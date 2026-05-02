import { useEffect, useState, useContext } from "react";
import axios from "axios";
import { AuthContext, API } from "@/App";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Loader2, Upload, FileScan, Activity, AlertTriangle,
  ShieldCheck, Clock, GitCompare, Stethoscope, Baby,
  FileDown, Flame, TrendingUp, Zap, Info,
} from "lucide-react";
import { toast } from "sonner";

const LANGS = [
  { id: "de", label: "🇩🇪 DE" },
  { id: "en", label: "🇬🇧 EN" },
  { id: "ar", label: "🇪🇬 AR" },
];

// Render citations [N] as styled <sup>
function Citations({ text }) {
  if (!text) return null;
  const parts = text.split(/(\[N?\d+\])/g);
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap leading-relaxed">
      {parts.map((p, i) =>
        /^\[N?\d+\]$/.test(p) ? (
          <sup key={i} className="font-bold text-amber-500 ml-0.5">{p}</sup>
        ) : (
          <span key={i}>{p}</span>
        )
      )}
    </div>
  );
}

export default function DicomPage() {
  const { token } = useContext(AuthContext) || {};
  const headers = { Authorization: `Bearer ${token}` };

  const [list, setList] = useState([]);
  const [file, setFile] = useState(null);
  const [patientLabel, setPatientLabel] = useState("");
  const [uploading, setUploading] = useState(false);
  const [current, setCurrent] = useState(null);       // uploaded/analyzed doc
  const [analyzing, setAnalyzing] = useState(false);
  const [patientContext, setPatientContext] = useState("");
  const [language, setLanguage] = useState("de");

  // Comparison
  const [cmpA, setCmpA] = useState("");
  const [cmpB, setCmpB] = useState("");
  const [comparing, setComparing] = useState(false);
  const [comparison, setComparison] = useState(null);

  // Manual body-part override for when DICOM metadata is insufficient
  const [bodyPartOverride, setBodyPartOverride] = useState("");

  const VALID_REGIONS = [
    { id: "chest", label: "🫁 Thorax" },
    { id: "brain", label: "🧠 Schädel/Gehirn" },
    { id: "abdomen", label: "🩻 Abdomen" },
    { id: "pelvis", label: "🦴 Becken" },
    { id: "spine", label: "🦴 Wirbelsäule" },
    { id: "limb", label: "🦾 Extremität" },
  ];

  const loadList = async () => {
    try {
      const r = await axios.get(`${API}/dicom/list/mine`, { headers });
      setList(r.data.items || []);
    } catch {}
  };

  useEffect(() => {
    if (token) loadList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const doUpload = async () => {
    if (!file) return toast.error("Bitte Datei wählen");
    setUploading(true);
    setCurrent(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      if (patientLabel) fd.append("patient_label", patientLabel);
      const r = await axios.post(`${API}/dicom/upload`, fd, {
        headers: { ...headers, "Content-Type": "multipart/form-data" },
        timeout: 180000,
      });
      setCurrent(r.data);
      toast.success(`${r.data.total_slices} Schichten geladen, ${r.data.selected_count} ausgewählt`);
      if (r.data.quality_warning) toast.warning(r.data.quality_warning);
      loadList();
    } catch (e) {
      const detail = e.response?.data?.detail;
      // Quality-gate rejection: detail is a dict with reason/action/code
      if (detail && typeof detail === "object" && detail.reason) {
        toast.error(`${detail.reason}${detail.action ? " — " + detail.action : ""}`, { duration: 8000 });
      } else {
        toast.error(typeof detail === "string" ? detail : "Upload fehlgeschlagen");
      }
    } finally {
      setUploading(false);
    }
  };

  const doAnalyze = async () => {
    if (!current?.analysis_id) return;
    setAnalyzing(true);
    try {
      const body = { patient_context: patientContext, language };
      if (bodyPartOverride) body.body_part_override = bodyPartOverride;
      // Kick off async job — returns immediately with status="analyzing"
      await axios.post(
        `${API}/dicom/analyze/${current.analysis_id}`,
        body,
        { headers, timeout: 15000 }
      );
      toast.info("Analyse gestartet — Ergebnis wird in Kürze erscheinen");

      // Poll every 2.5s until status = analyzed / error / context_missing (max 3 min)
      const id = current.analysis_id;
      const t0 = Date.now();
      const maxMs = 3 * 60 * 1000;
      while (Date.now() - t0 < maxMs) {
        await new Promise((r) => setTimeout(r, 2500));
        const r = await axios.get(`${API}/dicom/${id}`, { headers, timeout: 15000 });
        const s = r.data.status;
        if (s === "analyzed") {
          setCurrent({ ...current, analysis: r.data.analysis });
          toast.success("Analyse abgeschlossen");
          loadList();
          return;
        }
        if (s === "context_missing") {
          setCurrent({ ...current, analysis: r.data.analysis, context_missing: true });
          toast.error("Körperregion unbekannt — bitte manuell wählen und erneut senden");
          return;
        }
        if (s === "error") {
          toast.error(r.data.analyze_error || "Analyse fehlgeschlagen");
          return;
        }
        // keep polling while "analyzing" / "uploaded"
      }
      toast.error("Zeitüberschreitung — bitte erneut versuchen");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Analyse fehlgeschlagen");
    } finally {
      setAnalyzing(false);
    }
  };

  const doCompare = async () => {
    if (!cmpA || !cmpB) return toast.error("Beide Scans auswählen");
    setComparing(true);
    setComparison(null);
    try {
      const r = await axios.post(
        `${API}/dicom/compare/${cmpA}/${cmpB}`,
        { language },
        { headers, timeout: 180000 }
      );
      setComparison(r.data);
      toast.success("Vergleich erstellt");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Vergleich fehlgeschlagen");
    } finally {
      setComparing(false);
    }
  };

  const downloadPdf = async () => {
    if (!current?.analysis_id) return;
    try {
      const r = await axios.get(`${API}/dicom/report-pdf/${current.analysis_id}`, {
        headers, responseType: "blob", timeout: 60000,
      });
      const url = window.URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `dicom_report_${current.analysis_id.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast.error("PDF-Download fehlgeschlagen");
    }
  };

  const urgencyStyle = (u) => {
    const map = {
      HIGH:    { bg: "bg-red-500/15",    text: "text-red-600 dark:text-red-400",       label: "HIGH — Notfall", icon: Flame },
      MEDIUM:  { bg: "bg-amber-500/15",  text: "text-amber-600 dark:text-amber-400",   label: "MEDIUM — zeitkritisch", icon: AlertTriangle },
      LOW:     { bg: "bg-green-500/15",  text: "text-green-600 dark:text-green-400",   label: "LOW — kontrollbedürftig", icon: Info },
      UNKNOWN: { bg: "bg-muted",         text: "text-muted-foreground",                 label: "UNBEKANNT", icon: Info },
    };
    return map[u] || map.UNKNOWN;
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl" data-testid="dicom-page">
      <div className="flex items-center gap-3 mb-2">
        <FileScan className="w-8 h-8 text-amber-500" />
        <h1 className="text-3xl font-bold">DICOM Medical Imaging</h1>
        <Badge variant="secondary" className="text-xs">pydicom + OpenCV + RAG</Badge>
      </div>
      <p className="text-sm text-muted-foreground mb-6">
        Upload .dcm oder .zip (CT-Serie) → Smart Sampling → klinischer Bericht mit Leitlinien-Zitaten [N].
      </p>

      {/* UPLOAD */}
      <Card className="p-5 mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Upload className="w-5 h-5 text-amber-500" />
          <h2 className="font-bold">1. Datei hochladen</h2>
        </div>
        <input
          type="file"
          accept=".dcm,.zip,application/dicom,application/zip"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="block w-full text-sm mb-3 border rounded px-3 py-2 bg-background"
          data-testid="dicom-file-input"
        />
        <input
          value={patientLabel}
          onChange={(e) => setPatientLabel(e.target.value)}
          placeholder="Patientenlabel (optional) — z. B. 'Hamdy 45J'"
          className="block w-full text-sm mb-3 border rounded px-3 py-2 bg-background"
          data-testid="dicom-patient-label"
        />
        <Button onClick={doUpload} disabled={!file || uploading} data-testid="dicom-upload-btn">
          {uploading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Lade hoch & analysiere ...</> : <><Upload className="w-4 h-4 mr-2" /> Upload & Smart Sampling</>}
        </Button>
      </Card>

      {/* PREVIEWS */}
      {current && current.previews && (
        <Card className="p-5 mb-6" data-testid="dicom-preview-card">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-5 h-5 text-amber-500" />
            <h2 className="font-bold">Ausgewählte Schichten ({current.selected_count} / {current.total_slices})</h2>
          </div>
          <div className="text-xs text-muted-foreground mb-3">
            Modalität: <span className="font-semibold">{current.header?.modality}</span> ·
            Region: <span className="font-semibold">{current.header?.body_part || current.header?.study_description || "—"}</span> ·
            Patient: <span className="font-semibold">{current.header?.patient_age || "—"} / {current.header?.patient_sex || "—"}</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {current.previews.map((p) => (
              <div key={p.index} className="text-xs bg-muted/30 rounded p-2" data-testid={`dicom-preview-${p.index}`}>
                <img
                  src={`data:image/png;base64,${p.thumbnail}`}
                  alt={`Slice ${p.instance}`}
                  className="w-full rounded mb-2"
                />
                <div>#{p.instance}</div>
                <div className="text-muted-foreground">
                  sal={p.score?.saliency} · hell={p.score?.bright_regions} · dunkel={p.score?.dark_regions}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ANALYZE */}
      {current?.analysis_id && !current.analysis?.report && (
        <Card className="p-5 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Stethoscope className="w-5 h-5 text-amber-500" />
            <h2 className="font-bold">2. Klinische Analyse starten</h2>
          </div>

          {/* Context-missing warning */}
          {current.context_missing && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-700 dark:text-red-300 rounded-lg p-3 mb-4 text-sm" data-testid="dicom-context-missing">
              <div className="flex items-center gap-2 font-semibold mb-1">
                <AlertTriangle className="w-4 h-4" />
                Körperregion konnte nicht automatisch erkannt werden
              </div>
              <p className="opacity-90">
                Die DICOM-Metadaten enthalten keine <code>BodyPartExamined</code>, und die Beschreibung
                gibt keinen Hinweis. Bitte wähle die Region unten manuell und klicke erneut auf „Analyse starten".
              </p>
            </div>
          )}

          <Textarea
            value={patientContext}
            onChange={(e) => setPatientContext(e.target.value)}
            placeholder="Patientenkontext (z. B. 'Z.n. Verkehrsunfall, Dyspnoe, Hb 9.5 g/dl')"
            rows={3}
            className="mb-3"
            data-testid="dicom-patient-context"
          />

          {/* Manual body-part override */}
          <div className="mb-3">
            <label className="block text-sm font-semibold mb-1.5 flex items-center gap-2">
              <FileScan className="w-3.5 h-3.5 text-amber-500" />
              Körperregion (optional — überschreibt Auto-Erkennung)
            </label>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant={!bodyPartOverride ? "default" : "outline"}
                onClick={() => setBodyPartOverride("")}
                data-testid="dicom-region-auto"
              >
                Auto
              </Button>
              {VALID_REGIONS.map((r) => (
                <Button
                  key={r.id}
                  size="sm"
                  variant={bodyPartOverride === r.id ? "default" : "outline"}
                  onClick={() => setBodyPartOverride(r.id)}
                  data-testid={`dicom-region-${r.id}`}
                >
                  {r.label}
                </Button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2 mb-3">
            {LANGS.map((l) => (
              <Button key={l.id} size="sm" variant={language === l.id ? "default" : "outline"} onClick={() => setLanguage(l.id)}>
                {l.label}
              </Button>
            ))}
          </div>
          <Button onClick={doAnalyze} disabled={analyzing} data-testid="dicom-analyze-btn">
            {analyzing ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> RAG + DeepSeek läuft (30–60s) ...</> : <><Stethoscope className="w-4 h-4 mr-2" /> Analyse starten</>}
          </Button>
        </Card>
      )}

      {/* REPORT */}
      {current?.analysis?.report && (() => {
        const st = current.analysis.structured || {};
        const U = urgencyStyle(st.urgency || "UNKNOWN");
        const UIcon = U.icon;
        const det = current.analysis.detection || {};
        const val = current.analysis.validation || { valid: true, flags: [] };
        return (
        <Card className="p-5 mb-6" data-testid="dicom-report-card">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="w-5 h-5 text-amber-500" />
            <h2 className="font-bold">Klinischer Bericht</h2>
            <Button onClick={downloadPdf} variant="outline" size="sm" className="ml-auto gap-1.5" data-testid="dicom-pdf-btn">
              <FileDown className="w-4 h-4" /> PDF
            </Button>
          </div>

          {/* Context detection banner */}
          {current.analysis.body_part_label && (
            <div className="bg-muted/40 rounded-lg p-3 mb-3 flex items-center gap-3 text-sm flex-wrap" data-testid="dicom-detection-banner">
              <FileScan className="w-4 h-4 text-amber-500" />
              <span className="font-semibold">Erkannte Region:</span>
              <Badge className="bg-amber-500/20 text-amber-700 dark:text-amber-300" data-testid="dicom-body-part">
                {current.analysis.body_part_label}
              </Badge>
              <span className="text-xs text-muted-foreground">
                Methode: <code>{det.method || "?"}</code> · Konfidenz: {Math.round((det.confidence || 0) * 100)}%
              </span>
              {!val.valid && (
                <Badge className="ml-auto bg-red-500/15 text-red-700 dark:text-red-400" data-testid="dicom-validation-failed">
                  <AlertTriangle className="w-3 h-3 mr-1" /> {val.flags.length} Validierungs-Warnung(en)
                </Badge>
              )}
              {val.valid && (
                <Badge className="ml-auto bg-green-500/15 text-green-700 dark:text-green-400" data-testid="dicom-validation-ok">
                  <ShieldCheck className="w-3 h-3 mr-1" /> Region-konsistent
                </Badge>
              )}
            </div>
          )}

          {/* Urgency banner */}
          {st.urgency && st.urgency !== "UNKNOWN" && (
            <div className={`${U.bg} ${U.text} rounded-lg p-4 mb-4 flex items-center gap-3`} data-testid="dicom-urgency-banner">
              <UIcon className="w-6 h-6 flex-shrink-0" />
              <div className="flex-1">
                <div className="font-bold text-lg">{U.label}</div>
                {st.findings && <div className="text-sm opacity-90 mt-0.5">{st.findings}</div>}
              </div>
              {typeof st.confidence === "number" && (
                <div className="text-right">
                  <div className="text-xs opacity-70">Confidence</div>
                  <div className="font-bold text-xl">{Math.round(st.confidence * 100)}%</div>
                </div>
              )}
            </div>
          )}

          {/* ICD-10 tags */}
          {st.icd10?.length > 0 && (
            <div className="flex items-center gap-2 mb-3 text-sm">
              <span className="text-muted-foreground">ICD-10:</span>
              {st.icd10.map((c) => (
                <Badge key={c} variant="outline" className="font-mono" data-testid={`dicom-icd10-${c}`}>{c}</Badge>
              ))}
            </div>
          )}

          {/* Red flags */}
          {st.red_flags?.length > 0 && (
            <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-3 mb-4" data-testid="dicom-red-flags">
              <div className="flex items-center gap-2 mb-2 font-semibold text-red-700 dark:text-red-400 text-sm">
                <Flame className="w-4 h-4" /> Red Flags / Warnsymptome
              </div>
              <ul className="text-sm space-y-1">
                {st.red_flags.map((rf, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-red-500 font-bold">•</span>
                    <span>{rf}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Explainability */}
          {st.explainability?.length > 0 && (
            <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-3 mb-4" data-testid="dicom-explainability">
              <div className="flex items-center gap-2 mb-2 font-semibold text-amber-700 dark:text-amber-400 text-sm">
                <Zap className="w-4 h-4" /> Warum diese Dringlichkeit? (Explainability)
              </div>
              <ul className="text-sm space-y-1">
                {st.explainability.map((e, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-amber-500 font-bold">{i + 1}.</span>
                    <span>{e}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Cross-check */}
          {current.analysis.cross_check && (
            <div className={`p-3 rounded mb-4 text-sm flex items-center gap-2 ${
              current.analysis.cross_check.has_contradictions
                ? "bg-red-500/10 text-red-700 dark:text-red-300"
                : "bg-green-500/10 text-green-700 dark:text-green-300"
            }`} data-testid="dicom-cross-check">
              {current.analysis.cross_check.has_contradictions ? <AlertTriangle className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
              <span className="font-semibold">Cross-Verification:</span>
              <span>
                {current.analysis.cross_check.has_contradictions
                  ? `${current.analysis.cross_check.contradictions?.length || 0} Widerspruch/Widersprüche erkannt`
                  : "Konsistenter Bericht"}
              </span>
              <span className="ml-auto text-xs">Confidence: {current.analysis.cross_check.confidence}</span>
            </div>
          )}

          <Citations text={current.analysis.report} />

          {current.analysis.sources?.length > 0 && (
            <div className="mt-5 pt-4 border-t">
              <h3 className="text-sm font-bold mb-2 text-muted-foreground">Quellen:</h3>
              <div className="space-y-2">
                {current.analysis.sources.map((s) => (
                  <div key={s.index} className="text-xs bg-muted/30 rounded p-2" data-testid={`dicom-source-${s.index}`}>
                    <span className="font-bold text-amber-500">[{s.index}]</span>{" "}
                    <span className="font-semibold">{s.source}</span>
                    {s.code && <span className="text-muted-foreground ml-1">{s.code}</span>}
                    <p className="text-muted-foreground mt-1">{s.excerpt}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
        );
      })()}

      {/* HISTORY + COMPARISON */}
      {list.length > 0 && (
        <Card className="p-5 mb-6" data-testid="dicom-history-card">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-5 h-5 text-amber-500" />
            <h2 className="font-bold">Verlauf & Patienten-Tracking ({list.length})</h2>
          </div>
          <div className="space-y-1 max-h-72 overflow-y-auto mb-4">
            {list.map((it) => {
              const u = it.analysis?.structured?.urgency || it.urgency || "UNKNOWN";
              const uColor = u === "HIGH" ? "bg-red-500/15 text-red-600" : u === "MEDIUM" ? "bg-amber-500/15 text-amber-600" : u === "LOW" ? "bg-green-500/15 text-green-600" : "";
              return (
                <div key={it.id} className="flex items-center gap-2 text-xs bg-muted/30 rounded px-3 py-2">
                  <Baby className="w-3.5 h-3.5 text-amber-500" />
                  <span className="font-semibold">{it.patient_label || "Unbenannt"}</span>
                  <Badge variant="outline" className="text-[10px]">{it.header?.modality || "?"}</Badge>
                  <span className="text-muted-foreground">{it.header?.body_part}</span>
                  <span className="text-muted-foreground">{it.total_slices} Schichten</span>
                  {u !== "UNKNOWN" && (
                    <Badge className={`text-[10px] ${uColor}`} data-testid={`dicom-history-urgency-${it.id.slice(0,6)}`}>
                      <TrendingUp className="w-3 h-3 mr-0.5" /> {u}
                    </Badge>
                  )}
                  <span className="ml-auto text-muted-foreground">{(it.created_at || "").slice(0, 10)}</span>
                  <Badge variant={it.status === "analyzed" ? "default" : "secondary"} className="text-[10px]">
                    {it.status}
                  </Badge>
                  <code className="text-[10px] text-muted-foreground">{it.id.slice(0, 6)}</code>
                </div>
              );
            })}
          </div>

          <div className="flex items-center gap-2 mb-3">
            <GitCompare className="w-4 h-4 text-amber-500" />
            <h3 className="font-semibold text-sm">Zwei Scans vergleichen</h3>
          </div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <select value={cmpA} onChange={(e) => setCmpA(e.target.value)} className="text-sm border rounded px-2 py-1 bg-background" data-testid="dicom-cmp-a">
              <option value="">Scan 1 ...</option>
              {list.map((it) => {
                const label = `${(it.created_at || "").slice(0, 10)} — ${it.patient_label || it.id.slice(0, 6)}`;
                return <option key={it.id} value={it.id}>{label}</option>;
              })}
            </select>
            <select value={cmpB} onChange={(e) => setCmpB(e.target.value)} className="text-sm border rounded px-2 py-1 bg-background" data-testid="dicom-cmp-b">
              <option value="">Scan 2 ...</option>
              {list.map((it) => {
                const label = `${(it.created_at || "").slice(0, 10)} — ${it.patient_label || it.id.slice(0, 6)}`;
                return <option key={it.id} value={it.id}>{label}</option>;
              })}
            </select>
          </div>
          <Button size="sm" onClick={doCompare} disabled={!cmpA || !cmpB || comparing} data-testid="dicom-compare-btn">
            {comparing ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Vergleiche ...</> : <><GitCompare className="w-4 h-4 mr-2" /> Verlaufsbericht erstellen</>}
          </Button>

          {comparison && (
            <div className="mt-5 pt-4 border-t" data-testid="dicom-comparison-result">
              <h3 className="font-semibold text-sm mb-2">Quantitative Veränderung:</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4 text-xs">
                <div className="bg-muted/30 rounded p-2">
                  <div className="text-muted-foreground">Hyperdens</div>
                  <div className={`font-bold ${comparison.delta.bright_change_pct > 0 ? "text-red-500" : "text-green-500"}`}>
                    {comparison.delta.bright_change_pct > 0 ? "+" : ""}{comparison.delta.bright_change_pct}%
                  </div>
                </div>
                <div className="bg-muted/30 rounded p-2">
                  <div className="text-muted-foreground">Hypodens</div>
                  <div className={`font-bold ${comparison.delta.dark_change_pct > 0 ? "text-red-500" : "text-green-500"}`}>
                    {comparison.delta.dark_change_pct > 0 ? "+" : ""}{comparison.delta.dark_change_pct}%
                  </div>
                </div>
                <div className="bg-muted/30 rounded p-2">
                  <div className="text-muted-foreground">Schichten Δ</div>
                  <div className="font-bold">{comparison.delta.slice_count_change > 0 ? "+" : ""}{comparison.delta.slice_count_change}</div>
                </div>
                <div className="bg-muted/30 rounded p-2">
                  <div className="text-muted-foreground">Zeitraum</div>
                  <div className="font-bold">{comparison.delta.days_between} Tage</div>
                </div>
              </div>
              <Citations text={comparison.progression_report} />
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
