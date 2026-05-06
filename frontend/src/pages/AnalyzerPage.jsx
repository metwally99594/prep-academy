import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import {
  Upload, Camera, Loader2, Trash2, Clock, FileImage, Activity, Lock,
  ChevronDown, ChevronUp, Heart, Brain, Scan, Droplets, Bone, Radio,
  FileText, ArrowRight, Download, Plus, Images, Shield, AlertTriangle,
  Stethoscope, Eye, BarChart3,
} from "lucide-react";

const REPORT_TYPES = [
  { id: "ECG", label: "EKG", desc: "12-Kanal-Analyse", icon: Activity, color: "text-blue-500", bg: "bg-blue-50", emoji: "📈" },
  { id: "CT", label: "CT-Scan", desc: "3D-Segmentierung", icon: Scan, color: "text-orange-500", bg: "bg-orange-50", emoji: "🔬" },
  { id: "MRI", label: "MRT", desc: "Weichteilanalyse", icon: Brain, color: "text-purple-500", bg: "bg-purple-50", emoji: "🧲" },
  { id: "BloodTest", label: "Blutbild", desc: "Laborwerte", icon: Droplets, color: "text-red-500", bg: "bg-red-50", emoji: "🩸" },
  { id: "XRay", label: "Röntgen", desc: "Befundanalyse", icon: Bone, color: "text-sky-500", bg: "bg-sky-50", emoji: "🫁" },
  { id: "Ultrasound", label: "Ultraschall", desc: "Sonographie", icon: Radio, color: "text-teal-500", bg: "bg-teal-50", emoji: "📡" },
  { id: "Echo", label: "Echokardiographie", desc: "Herzultraschall", icon: Heart, color: "text-pink-500", bg: "bg-pink-50", emoji: "❤️" },
  { id: "Other", label: "Sonstiges", desc: "Andere Befunde", icon: FileText, color: "text-gray-500", bg: "bg-gray-50", emoji: "📋" },
];

export default function AnalyzerPage() {
  const { token } = useAuth();
  const [hasAccess, setHasAccess] = useState(null);
  const [images, setImages] = useState([]);
  const [reportType, setReportType] = useState("ECG");
  const [clinicalContext, setClinicalContext] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [expandedHistory, setExpandedHistory] = useState(null);
  const [showAllHistory, setShowAllHistory] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef(null);
  const videoRef = useRef(null);
  const [showCamera, setShowCamera] = useState(false);

  useEffect(() => {
    if (!token) return;
    const headers = { Authorization: `Bearer ${token}` };
    axios.get(`${API}/analyzer/access`, { headers }).then(() => setHasAccess(true)).catch(() => setHasAccess(false));
    fetchHistory();
  }, [token]); // eslint-disable-line

  const fetchHistory = () => {
    if (!token) return;
    axios.get(`${API}/analyzer/history`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => setHistory(r.data || []))
      .catch(() => {});
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files || []);
    processFiles(files);
    if (fileRef.current) fileRef.current.value = "";
  };

  const processFiles = (files) => {
    files.forEach(file => {
      if (file.size > 20 * 1024 * 1024) { toast.error(`${file.name}: Zu groß (max 20MB)`); return; }
      if (file.type.startsWith("video/")) {
        const video = document.createElement("video");
        video.preload = "metadata";
        video.onloadeddata = () => { video.currentTime = 1; };
        video.onseeked = () => {
          const canvas = document.createElement("canvas");
          canvas.width = video.videoWidth; canvas.height = video.videoHeight;
          canvas.getContext("2d").drawImage(video, 0, 0);
          canvas.toBlob((blob) => {
            if (!blob) return;
            const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
            setImages(prev => [...prev, { dataUrl, blob, name: file.name.replace(/\.[^.]+$/, '') + '.jpg' }].slice(0, 10));
          }, "image/jpeg", 0.7);
          URL.revokeObjectURL(video.src);
        };
        video.src = URL.createObjectURL(file);
        return;
      }
      // Compress & convert to Blob (for multipart upload — much more efficient than base64 JSON)
      const reader = new FileReader();
      reader.onload = (ev) => {
        const img = new window.Image();
        img.onload = () => {
          const canvas = document.createElement("canvas");
          const tryCompress = (maxDim, quality) => {
            let w = img.width, h = img.height;
            if (w > maxDim || h > maxDim) {
              if (w > h) { h = Math.round(h * maxDim / w); w = maxDim; }
              else { w = Math.round(w * maxDim / h); h = maxDim; }
            }
            canvas.width = w; canvas.height = h;
            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "#000"; ctx.fillRect(0, 0, w, h);
            ctx.drawImage(img, 0, 0, w, h);
            return canvas.toDataURL("image/jpeg", quality);
          };

          let dataUrl = tryCompress(1600, 0.85);
          if (dataUrl.length > 800 * 1024) dataUrl = tryCompress(1300, 0.8);
          if (dataUrl.length > 800 * 1024) dataUrl = tryCompress(1024, 0.75);

          // Convert dataUrl to Blob for efficient multipart upload
          canvas.toBlob((blob) => {
            if (!blob) return;
            console.log(`[Analyzer] Image ready: ${(blob.size/1024).toFixed(0)} KB blob (original ${(file.size/1024).toFixed(0)} KB)`);
            setImages(prev => [...prev, { dataUrl, blob, name: file.name.replace(/\.[^.]+$/, '') + '.jpg' }].slice(0, 10));
          }, "image/jpeg", 0.82);
        };
        img.onerror = () => {
          // Non-image file (PDF, DICOM) - use original file
          setImages(prev => [...prev, { dataUrl: ev.target.result, blob: file, name: file.name }].slice(0, 10));
        };
        img.src = ev.target.result;
      };
      reader.readAsDataURL(file);
    });
  };

  const onDrop = useCallback((e) => {
    e.preventDefault(); setDragging(false);
    const files = Array.from(e.dataTransfer.files || []);
    processFiles(files);
  }, []); // eslint-disable-line

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      videoRef.current.srcObject = stream; setShowCamera(true);
    } catch { toast.error("Kamera nicht verfügbar"); }
  };
  const stopCamera = () => {
    if (videoRef.current?.srcObject) videoRef.current.srcObject.getTracks().forEach(t => t.stop());
    setShowCamera(false);
  };
  const capturePhoto = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth; canvas.height = videoRef.current.videoHeight;
    canvas.getContext("2d").drawImage(videoRef.current, 0, 0);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.8);
    canvas.toBlob((blob) => {
      if (!blob) return;
      setImages(prev => [...prev, { dataUrl, blob, name: `photo_${Date.now()}.jpg` }].slice(0, 10));
    }, "image/jpeg", 0.8);
    stopCamera();
  };

  const analyzeReport = async () => {
    if (images.length === 0) return;
    setAnalyzing(true); setResult(null);
    try {
      // Upload via multipart/form-data (bypasses JSON size limits & inefficient base64 encoding)
      const formData = new FormData();
      images.forEach((img, i) => {
        const blob = img.blob || img;
        const name = img.name || `image_${i}.jpg`;
        formData.append("files", blob, name);
      });
      formData.append("report_type", reportType);
      formData.append("clinical_context", clinicalContext || "");

      const totalMB = images.reduce((s, img) => s + (img.blob?.size || 0), 0) / (1024 * 1024);
      console.log(`[Analyzer] Uploading ${images.length} files, total ${totalMB.toFixed(2)} MB via multipart`);

      const start = await axios.post(`${API}/analyzer/analyze-upload`, formData, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 90000,
      });
      const jobId = start.data.job_id;
      if (!jobId) throw new Error("Kein Job-ID erhalten");

      // Poll the job status every 3s
      const maxAttempts = 80;
      let attempt = 0;
      while (attempt < maxAttempts) {
        await new Promise(r => setTimeout(r, 3000));
        attempt++;
        try {
          const poll = await axios.get(`${API}/analyzer/job/${jobId}`, {
            headers: { Authorization: `Bearer ${token}` }, timeout: 15000,
          });
          const { status, result: jobResult, message } = poll.data;
          if (status === "done" && jobResult) {
            setResult(jobResult);
            fetchHistory();
            toast.success(`Analyse abgeschlossen! ${jobResult.ai_count || 1} KI-Modell${(jobResult.ai_count || 1) > 1 ? 'e' : ''} verwendet.`);
            return;
          }
          if (status === "error") {
            throw new Error(message || "Analyse fehlgeschlagen");
          }
        } catch (pollErr) {
          if (pollErr.message?.includes("Analyse fehlgeschlagen")) throw pollErr;
          console.warn("[Analyzer] Poll retry:", pollErr.message);
        }
      }
      throw new Error("Timeout: Analyse dauert zu lange");
    } catch (err) {
      console.error("[Analyzer] Error:", err);
      const msg = err.response?.data?.detail || err.message || "Analyse fehlgeschlagen";
      toast.error(msg === "Network Error" ? "Netzwerkfehler beim Hochladen. Bitte Verbindung prüfen." : msg);
    } finally {
      setAnalyzing(false);
    }
  };

  const deleteAnalysis = async (id) => {
    try {
      await axios.delete(`${API}/analyzer/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      setHistory(prev => prev.filter(h => h.id !== id));
      toast.success("Gelöscht");
    } catch { /* */ }
  };

  const getConfidence = (result) => {
    if (result?.confidence_score) return result.confidence_score;
    const m = (result?.analysis || "").match(/(\d{1,3})\s*%/);
    return m ? Math.min(parseInt(m[1]), 100) : 55;
  };
  const getModelsLabel = (result) => {
    if (result?.models_used?.length) {
      return result.models_used.map(m => m.model).join(' + ');
    }
    return result?.ai_count > 1 ? `${result.ai_count} KI-Modelle` : '1 KI-Modell';
  };
  const getFindings = (text) => ((text || "").match(/^[-•]\s/gm) || []).length;

  // Build a professional printable HTML report (opens print dialog → save as PDF)
  const printReport = (item) => {
    const typeObj = REPORT_TYPES.find(t => t.id === item.report_type) || { label: item.report_type, emoji: '📋' };
    const conf = getConfidence(item);
    const confColor = conf >= 80 ? '#10b981' : conf >= 60 ? '#f59e0b' : '#ef4444';
    const dateStr = new Date(item.created_at || Date.now()).toLocaleString('de-DE', { dateStyle: 'long', timeStyle: 'short' });
    const logoUrl = `${window.location.origin}/logo-elite.png`;

    // Convert markdown-ish text to HTML for print
    const toPrintHtml = (md) => {
      if (!md) return '';
      let html = md
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/^## (.*)$/gm, '<h2>$1</h2>')
        .replace(/^### (.*)$/gm, '<h3>$1</h3>')
        .replace(/^---$/gm, '<hr/>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`)
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br/>');
      return `<p>${html}</p>`;
    };

    const win = window.open('', '_blank', 'width=900,height=1200');
    if (!win) { toast.error('Pop-up blockiert. Bitte Pop-ups erlauben.'); return; }

    win.document.write(`<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"/>
<title>Prep Academy — Analysebericht ${typeObj.label}</title>
<style>
  @page { size: A4; margin: 16mm 14mm 22mm 14mm; }
  * { box-sizing: border-box; }
  body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #1a1a2e; margin: 0; padding: 0; line-height: 1.55; font-size: 11pt; }
  .header { border-bottom: 3px solid #c9a84c; padding-bottom: 14px; margin-bottom: 22px; display: flex; align-items: center; justify-content: space-between; }
  .header .brand { display: flex; align-items: center; gap: 14px; }
  .header .brand img { width: 54px; height: 54px; border-radius: 10px; }
  .header .brand .t1 { font-family: 'Playfair Display', Georgia, serif; font-size: 22pt; font-weight: 700; color: #0c1229; letter-spacing: -0.5px; }
  .header .brand .t1 span { color: #c9a84c; }
  .header .brand .t2 { font-size: 9pt; color: #6b7280; text-transform: uppercase; letter-spacing: 1.5px; }
  .header .meta { text-align: right; font-size: 9pt; color: #6b7280; }
  .header .meta .badge { display: inline-block; padding: 4px 10px; background: #c9a84c; color: #0c1229; font-weight: 700; border-radius: 6px; font-size: 9pt; margin-bottom: 4px; }

  .title-section { background: linear-gradient(135deg, #0c1229, #1a1f3a); color: #fff; padding: 18px 22px; border-radius: 12px; margin-bottom: 18px; }
  .title-section h1 { margin: 0 0 6px 0; font-family: 'Playfair Display', Georgia, serif; font-size: 20pt; color: #c9a84c; }
  .title-section p { margin: 0; font-size: 10pt; opacity: 0.9; }

  .kpis { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 22px; }
  .kpi { border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 14px; }
  .kpi .lbl { font-size: 8pt; text-transform: uppercase; letter-spacing: 1px; color: #6b7280; margin-bottom: 4px; font-weight: 700; }
  .kpi .val { font-size: 16pt; font-weight: 700; color: #0c1229; }
  .kpi .sub { font-size: 8.5pt; color: #6b7280; margin-top: 2px; }
  .bar { height: 6px; background: #e5e7eb; border-radius: 3px; margin-top: 6px; overflow: hidden; }
  .bar > div { height: 100%; border-radius: 3px; }

  .ctx { background: #fdf6e6; border-right: 3px solid #c9a84c; padding: 10px 14px; border-radius: 6px; margin-bottom: 18px; font-size: 10pt; }
  .ctx .t { font-weight: 700; color: #8b6914; margin-bottom: 3px; font-size: 9pt; text-transform: uppercase; letter-spacing: 1px; }

  .content { font-size: 10.5pt; }
  .content h2 { color: #c9a84c; border-bottom: 2px solid #c9a84c; padding-bottom: 4px; margin: 20px 0 10px 0; font-size: 13pt; }
  .content h3 { color: #0c1229; margin: 14px 0 6px 0; font-size: 11pt; }
  .content hr { border: 0; border-top: 1px dashed #c9a84c; margin: 22px 0; }
  .content ul { margin: 6px 0 10px 0; padding-left: 20px; }
  .content li { margin-bottom: 4px; }
  .content strong { color: #0c1229; }
  .content p { margin: 6px 0; }

  .disclaimer { margin-top: 26px; padding: 12px 14px; background: #fff8e1; border: 1px solid #fbbf24; border-radius: 8px; font-size: 8.5pt; color: #78350f; }
  .disclaimer strong { color: #92400e; }

  .footer { margin-top: 30px; padding-top: 18px; border-top: 2px solid #c9a84c; display: flex; align-items: center; justify-content: space-between; }
  .footer img { width: 48px; height: 48px; border-radius: 8px; }
  .footer .info { text-align: center; flex: 1; }
  .footer .info .name { font-family: 'Playfair Display', Georgia, serif; font-size: 14pt; font-weight: 700; color: #0c1229; }
  .footer .info .name span { color: #c9a84c; }
  .footer .info .tag { font-size: 8pt; color: #6b7280; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 2px; }
  .footer .page { font-size: 8pt; color: #6b7280; }

  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .no-print { display: none !important; }
  }
  .actions { position: fixed; top: 10px; right: 10px; display: flex; gap: 8px; z-index: 99; }
  .actions button { padding: 8px 16px; border: 0; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 10pt; }
  .actions .p { background: #c9a84c; color: #0c1229; }
  .actions .c { background: #e5e7eb; color: #374151; }
</style>
</head><body>
  <div class="actions no-print">
    <button class="p" onclick="window.print()">🖨️ Drucken / Als PDF speichern</button>
    <button class="c" onclick="window.close()">Schließen</button>
  </div>

  <div class="header">
    <div class="brand">
      <img src="${logoUrl}" alt="PrepAcademy" onerror="this.style.display='none'"/>
      <div>
        <div class="t1">Prep<span>Academy</span></div>
        <div class="t2">Medical Analyzer — Befundbericht</div>
      </div>
    </div>
    <div class="meta">
      <div class="badge">${typeObj.label}</div>
      <div>${dateStr}</div>
      <div>ID: ${(item.id || '').slice(0, 8)}</div>
    </div>
  </div>

  <div class="title-section">
    <h1>${typeObj.emoji} ${typeObj.label} — KI-Analysebericht</h1>
    <p>Multi-KI-Befundanalyse mit unabhängiger Zweit- und Drittmeinung</p>
  </div>

  <div class="kpis">
    <div class="kpi">
      <div class="lbl">Vertrauen</div>
      <div class="val" style="color:${confColor}">${conf}%</div>
      <div class="bar"><div style="width:${conf}%;background:${confColor}"></div></div>
    </div>
    <div class="kpi">
      <div class="lbl">KI-Modelle</div>
      <div class="val">${item.ai_count || 1}×</div>
      <div class="sub">${(item.models_used || []).map(m => m.model.split(' ')[0]).join(' + ') || 'Gemma 4 31B'}</div>
    </div>
    <div class="kpi">
      <div class="lbl">Befunde</div>
      <div class="val">${getFindings(item.analysis || '')}</div>
      <div class="sub">erkannte Punkte</div>
    </div>
  </div>

  ${clinicalContext && !item.id ? `<div class="ctx"><div class="t">Klinischer Kontext</div>${clinicalContext}</div>` : ''}

  <div class="content">${toPrintHtml(item.analysis || '')}</div>

  <div class="disclaimer">
    <strong>Wichtiger Hinweis:</strong> Dieser Bericht wurde durch KI-Modelle generiert und dient ausschließlich als unterstützendes Lernwerkzeug für medizinisches Fachpersonal und Studierende. Er ersetzt keine ärztliche Diagnose oder klinische Beurteilung. Alle Empfehlungen sind durch einen qualifizierten Arzt zu überprüfen.
  </div>

  <div class="footer">
    <img src="${logoUrl}" alt="PrepAcademy Elite" onerror="this.style.display='none'"/>
    <div class="info">
      <div class="name">Prep<span>Academy</span> Elite</div>
      <div class="tag">Redefining Medical Education</div>
    </div>
    <div class="page">${window.location.host}</div>
  </div>

  <script>
    window.addEventListener('load', function(){ setTimeout(function(){ window.print(); }, 600); });
  </script>
</body></html>`);
    win.document.close();
  };

  if (hasAccess === null) return <div className="flex justify-center py-20"><Loader2 className="animate-spin" style={{ color: '#c9a84c' }} /></div>;
  if (hasAccess === false) return (
    <div className="max-w-md mx-auto px-4 py-20 text-center">
      <Lock className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
      <h2 className="text-xl font-bold mb-2">Premium-Funktion</h2>
      <p className="text-sm text-muted-foreground">Der Medical Analyzer ist für registrierte Benutzer verfügbar.</p>
    </div>
  );

  const selectedType = REPORT_TYPES.find(t => t.id === reportType);
  const confidence = result ? getConfidence(result) : 0;
  const confColor = confidence >= 80 ? '#10b981' : confidence >= 60 ? '#f59e0b' : '#ef4444';

  return (
    <div className="max-w-[1200px] mx-auto px-4 py-6" data-testid="analyzer-page">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)' }}>
          <Stethoscope className="w-5 h-5 text-[#06081a]" />
        </div>
        <div>
          <h1 className="text-xl font-bold" style={{ fontFamily: "'Playfair Display', serif" }}>Medical <span style={{ color: '#c9a84c' }}>Analyzer</span></h1>
          <p className="text-xs text-muted-foreground">Multi-AI Befundanalyse mit Zweitmeinung</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr_280px] gap-4">
        {/* ── Sidebar: Modalities ── */}
        <div className="glass-card rounded-2xl p-3 space-y-1 lg:self-start" data-testid="modality-sidebar">
          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground px-2 pb-2 border-b border-border/30">Untersuchungstypen</p>
          {REPORT_TYPES.map(rt => (
            <button key={rt.id} onClick={() => setReportType(rt.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all ${reportType === rt.id ? 'bg-[#c9a84c]/10 border-r-[3px] border-[#c9a84c]' : 'hover:bg-muted/30'}`}
              data-testid={`mod-${rt.id}`}>
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm flex-shrink-0 ${reportType === rt.id ? 'bg-[#c9a84c] text-[#06081a]' : 'bg-muted/50'}`}>
                {rt.emoji}
              </div>
              <div className="min-w-0">
                <div className={`text-xs font-semibold ${reportType === rt.id ? 'text-[#c9a84c]' : ''}`}>{rt.label}</div>
                <div className="text-[10px] text-muted-foreground truncate">{rt.desc}</div>
              </div>
            </button>
          ))}
        </div>

        {/* ── Main Content ── */}
        <div className="space-y-4">
          {/* Privacy Note */}
          <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs" style={{ background: 'rgba(201,168,76,0.08)', border: '1px solid rgba(201,168,76,0.2)', color: '#c9a84c' }}>
            <Shield className="w-4 h-4 flex-shrink-0" />
            3 KI-Modelle: Gemma 4 31B (Google) + Nemotron 12B VL (NVIDIA) + Qianfan OCR (Baidu) — mit Fallback-Chain
          </div>

          {/* Disclaimer */}
          <div className="flex gap-2 px-4 py-3 rounded-xl text-xs" style={{ background: 'rgba(245,158,11,0.08)', borderRight: '3px solid #f59e0b' }}>
            <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
            <div className="text-muted-foreground">
              <strong className="text-amber-500">Hinweis:</strong> Dieses System dient als KI-gestütztes Lernwerkzeug. Keine klinische Diagnose ohne ärztliche Beurteilung. Ergebnisse können Fehler enthalten.
            </div>
          </div>

          {/* Upload Zone */}
          {showCamera ? (
            <div className="space-y-3 glass-card rounded-2xl p-4">
              <video ref={videoRef} autoPlay playsInline className="w-full rounded-xl border" />
              <div className="flex gap-3">
                <Button onClick={capturePhoto} className="flex-1 gap-2"><Camera className="w-4 h-4" /> Aufnehmen</Button>
                <Button variant="outline" onClick={stopCamera}>Abbrechen</Button>
              </div>
            </div>
          ) : images.length > 0 ? (
            <div className="glass-card rounded-2xl p-4 space-y-3">
              <div className={`grid gap-2 ${images.length === 1 ? 'grid-cols-1' : images.length <= 4 ? 'grid-cols-2' : 'grid-cols-3'}`}>
                {images.map((img, idx) => (
                  <div key={idx} className="relative group">
                    <img src={img.dataUrl || img} alt={`Bild ${idx + 1}`} className="w-full h-40 object-cover rounded-xl border border-border/30" />
                    <button onClick={() => setImages(prev => prev.filter((_, i) => i !== idx))}
                      className="absolute top-1 right-1 w-6 h-6 rounded-full bg-red-500 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                      <Trash2 className="w-3 h-3" />
                    </button>
                    <span className="absolute bottom-1 left-1 bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded font-mono">{idx + 1}</span>
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Images className="w-3 h-3" /> {images.length} Bild{images.length > 1 ? 'er' : ''} <span className="text-muted-foreground/50">(max 10)</span>
                </span>
                <div className="flex gap-2">
                  {images.length < 10 && (
                    <Button variant="outline" size="sm" className="gap-1 h-7 text-xs" onClick={() => fileRef.current?.click()}>
                      <Plus className="w-3 h-3" /> Weitere
                    </Button>
                  )}
                  <Button variant="outline" size="sm" className="gap-1 h-7 text-xs" onClick={startCamera}>
                    <Camera className="w-3 h-3" /> Kamera
                  </Button>
                  <Button variant="outline" size="sm" className="gap-1 h-7 text-xs text-red-400 hover:text-red-500" onClick={() => setImages([])}>
                    <Trash2 className="w-3 h-3" /> Alle
                  </Button>
                </div>
              </div>
              <input ref={fileRef} type="file" accept="image/*,video/*,.pdf,.dcm,.dicom" multiple className="hidden" onChange={handleFileSelect} />
            </div>
          ) : (
            <div className={`glass-card rounded-2xl p-8 text-center cursor-pointer transition-all border-2 border-dashed ${dragging ? 'border-[#c9a84c] bg-[#c9a84c]/5' : 'border-border/30 hover:border-[#c9a84c]/40'}`}
              onDragOver={e => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              onClick={() => fileRef.current?.click()}
              data-testid="upload-dropzone">
              <div className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center" style={{ background: 'rgba(201,168,76,0.1)' }}>
                <Upload className="w-7 h-7" style={{ color: '#c9a84c' }} />
              </div>
              <p className="font-semibold text-sm mb-1">Bilder hochladen oder hierher ziehen</p>
              <p className="text-xs text-muted-foreground mb-3">Mehrere Bilder möglich — DICOM · PNG · JPG · PDF bis 10MB</p>
              <div className="flex flex-wrap gap-1.5 justify-center">
                {['DICOM', 'PNG', 'JPG', 'PDF', 'MP4'].map(f => (
                  <span key={f} className="px-2 py-0.5 rounded text-[10px] bg-muted/50 border border-border/30 font-mono">{f}</span>
                ))}
              </div>
              <div className="flex gap-2 justify-center mt-4">
                <Button variant="outline" size="sm" className="gap-1 text-xs" onClick={e => { e.stopPropagation(); startCamera(); }}>
                  <Camera className="w-3 h-3" /> Kamera
                </Button>
              </div>
              <input ref={fileRef} type="file" accept="image/*,video/*,.pdf,.dcm,.dicom" multiple className="hidden" onChange={handleFileSelect} data-testid="file-input" />
            </div>
          )}

          {/* Clinical Context */}
          <div>
            <label className="text-xs font-semibold flex items-center gap-1 mb-1.5">
              <Eye className="w-3 h-3" /> Klinischer Kontext <span className="text-muted-foreground font-normal">(Optional)</span>
            </label>
            <Textarea value={clinicalContext} onChange={e => setClinicalContext(e.target.value)}
              placeholder="z.B. 55J männlich, Brustschmerzen, RR 160/95, Beginn vor 2h. DD: ACS."
              className="min-h-[80px] text-sm" data-testid="clinical-context-input" />
          </div>

          {/* Analyze Button */}
          <Button onClick={analyzeReport} disabled={analyzing || images.length === 0}
            className="w-full gap-2 h-12 text-base font-semibold"
            style={images.length > 0 && !analyzing ? { background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' } : {}}
            data-testid="analyze-btn">
            {analyzing ? <><Loader2 className="w-5 h-5 animate-spin" /> Multi-AI Analyse läuft (Gemma 4 31B + Nemotron 12B + Qianfan)...</>
              : <>{selectedType && <span className="text-lg">{selectedType.emoji}</span>} {images.length > 1 ? `${images.length} Bilder` : selectedType?.label || 'Bericht'} analysieren (3 KI)</>}
          </Button>

          {/* ── Result Card ── */}
          {result && (
            <div className="glass-card rounded-2xl overflow-hidden" data-testid="analysis-result">
              {/* Header */}
              <div className="flex items-center gap-3 px-5 py-3 border-b border-border/30" style={{ background: 'rgba(201,168,76,0.05)' }}>
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <div className="flex-1">
                  <h3 className="font-bold text-sm">KI-Analysebericht — {result.report_type}</h3>
                  <p className="text-[10px] text-muted-foreground">
                    {result.ai_count || 1} KI-Modell{(result.ai_count || 1) > 1 ? 'e' : ''}: {getModelsLabel(result)} · {new Date().toLocaleTimeString('de-DE')}
                  </p>
                </div>
                <Button variant="outline" size="sm" className="gap-1 h-7" onClick={() => printReport(result)} data-testid="print-report-btn">
                  <Download className="w-3 h-3" /> Drucken / PDF
                </Button>
              </div>

              {/* Findings Grid */}
              <div className="grid grid-cols-2 gap-3 p-4 border-b border-border/30">
                <div className="p-3 rounded-xl bg-muted/20">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">Vertrauen</p>
                  <p className="text-lg font-bold" style={{ color: confColor }}>{confidence}%</p>
                  <div className="h-1.5 rounded-full bg-muted/30 mt-1 overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width: `${confidence}%`, background: confColor }} />
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-muted/20">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">Typ</p>
                  <p className="text-lg font-bold flex items-center gap-2">{selectedType?.emoji} {selectedType?.label}</p>
                  <p className="text-[10px] text-muted-foreground">{getFindings(result.analysis)} Befunde erkannt</p>
                </div>
              </div>

              {/* Report Body */}
              <div className="p-5 prose prose-sm max-w-none dark:prose-invert [&_h2]:text-[#c9a84c] [&_h2]:text-sm [&_h2]:mt-4 [&_h2]:mb-2 [&_strong]:text-foreground [&_li]:text-sm leading-relaxed"
                dangerouslySetInnerHTML={{ __html: formatMarkdown(result.analysis) }}
                data-testid="analysis-content" />
            </div>
          )}
        </div>

        {/* ── Right: History ── */}
        <div className="space-y-3 lg:self-start">
          <div className="glass-card rounded-2xl p-3" data-testid="history-section">
            <div className="flex items-center justify-between mb-2 px-1">
              <h2 className="font-semibold text-xs flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" style={{ color: '#c9a84c' }} /> Letzte Analysen
              </h2>
              {history.length > 3 && (
                <button onClick={() => setShowAllHistory(!showAllHistory)} className="text-[10px] text-[#c9a84c] hover:underline">
                  {showAllHistory ? "Weniger" : `Alle (${history.length})`}
                </button>
              )}
            </div>
            {history.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-6">Noch keine Analysen</p>
            ) : (
              <div className="space-y-1.5 max-h-[500px] overflow-y-auto">
                {(showAllHistory ? history : history.slice(0, 5)).map(item => {
                  const typeInfo = REPORT_TYPES.find(rt => rt.id === item.report_type);
                  return (
                    <div key={item.id} className="rounded-xl border border-border/30 overflow-hidden" data-testid={`history-item-${item.id}`}>
                      <button onClick={() => setExpandedHistory(expandedHistory === item.id ? null : item.id)}
                        className="w-full p-2.5 hover:bg-muted/20 transition-colors text-left">
                        <div className="flex items-center gap-2">
                          <span className="text-sm">{typeInfo?.emoji || '📋'}</span>
                          <span className="text-xs font-medium flex-1">{item.report_type}</span>
                          <span className="text-[10px] text-muted-foreground">
                            {new Date(item.created_at).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })}
                          </span>
                          {expandedHistory === item.id ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </div>
                      </button>
                      {expandedHistory === item.id && (
                        <div className="border-t border-border/20 p-2.5">
                          <div className="prose prose-xs max-w-none dark:prose-invert [&_h2]:text-[10px] [&_h2]:text-[#c9a84c] [&_li]:text-[10px] [&_p]:text-[10px] max-h-48 overflow-y-auto"
                            dangerouslySetInnerHTML={{ __html: formatMarkdown(item.analysis) }} />
                          <div className="flex gap-1 mt-2">
                            <Button variant="ghost" size="sm" className="h-6 text-[10px] text-red-400 gap-1 px-2" onClick={() => deleteAnalysis(item.id)}>
                              <Trash2 className="w-2.5 h-2.5" /> Löschen
                            </Button>
                            <Button variant="ghost" size="sm" className="h-6 text-[10px] gap-1 px-2" onClick={() => printReport(item)} data-testid={`print-history-${item.id}`}>
                              <Download className="w-2.5 h-2.5" /> PDF
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer Disclaimer */}
          <div className="px-3 py-2 rounded-xl bg-muted/20 border border-border/20">
            <p className="text-[10px] text-muted-foreground text-center leading-relaxed">
              <Stethoscope className="w-3 h-3 inline mr-1" style={{ color: '#c9a84c' }} />
              <span style={{ color: '#c9a84c' }}>Prep Academy</span> — Multi-AI Befundanalyse.
              Nur zur Unterstützung. Ärztliche Beurteilung hat Vorrang.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function formatMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/## (.*)/g, "<h2>$1</h2>")
    .replace(/### (.*)/g, "<h3 style='font-size:13px;font-weight:700;margin-top:12px;color:#c9a84c'>$1</h3>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/^[-•] (.*)/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>")
    .replace(/<\/ul>\s*<ul>/g, "")
    .replace(/---/g, "<hr style='border-color:rgba(201,168,76,0.2);margin:16px 0'/>")
    .replace(/\n\n/g, "<br/><br/>")
    .replace(/\n/g, "<br/>");
}
