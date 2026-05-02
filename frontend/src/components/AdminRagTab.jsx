import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/App";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Loader2, Upload, Database, Trash2, FileUp, RefreshCw } from "lucide-react";
import { toast } from "sonner";

// Specialties shown in the dropdown — matches BODY_PART_CONTEXT rag_categories in backend.
const CATEGORIES = [
  "Allgemein", "Notfallmedizin", "Kardiologie", "Pneumologie",
  "Neurologie", "Gastroenterologie", "Urologie", "Endokrinologie",
  "Chirurgie", "Psychiatrie", "Intensivmedizin", "Pharmakologie",
  "Orthopädie", "Pädiatrie", "Gynäkologie",
];

export default function AdminRagTab({ token }) {
  const headers = { Authorization: `Bearer ${token}` };
  const [status, setStatus] = useState(null);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [ingestText, setIngestText] = useState("");
  const [ingestName, setIngestName] = useState("");
  const [ingestCategory, setIngestCategory] = useState("Allgemein");
  const [ingesting, setIngesting] = useState(false);
  const [pdfFile, setPdfFile] = useState(null);
  const [pdfName, setPdfName] = useState("");
  const [pdfCategory, setPdfCategory] = useState("Allgemein");
  const [pdfUploading, setPdfUploading] = useState(false);

  const reload = async () => {
    setLoading(true);
    try {
      const [s, src] = await Promise.all([
        axios.get(`${API}/rag/status`),
        axios.get(`${API}/rag/sources`, { headers }),
      ]);
      setStatus(s.data);
      setSources(src.data.sources || []);
    } catch (e) {
      toast.error("Fehler beim Laden");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const doIngest = async () => {
    if (!ingestText.trim() || !ingestName.trim()) {
      return toast.error("Text und Quellen-Name sind Pflicht");
    }
    setIngesting(true);
    try {
      const r = await axios.post(
        `${API}/rag/ingest-text`,
        { content: ingestText, source: ingestName, category: ingestCategory, language: "de" },
        { headers, timeout: 60000 }
      );
      toast.success(`${r.data.added_chunks} Abschnitte hinzugefügt`);
      setIngestText("");
      setIngestName("");
      reload();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Import fehlgeschlagen");
    } finally {
      setIngesting(false);
    }
  };

  const doIngestPdf = async () => {
    if (!pdfFile || !pdfName.trim()) return toast.error("PDF und Name erforderlich");
    setPdfUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", pdfFile);
      fd.append("source", pdfName);
      fd.append("category", pdfCategory);
      fd.append("language", "de");
      const r = await axios.post(`${API}/rag/ingest-pdf`, fd, {
        headers: { ...headers, "Content-Type": "multipart/form-data" },
        timeout: 180000,
      });
      toast.success(`${r.data.added_chunks} Abschnitte aus PDF hinzugefügt`);
      setPdfFile(null);
      setPdfName("");
      reload();
    } catch (e) {
      toast.error(e.response?.data?.detail || "PDF-Import fehlgeschlagen");
    } finally {
      setPdfUploading(false);
    }
  };

  const deleteSource = async (name) => {
    if (!window.confirm(`Quelle "${name}" wirklich löschen?`)) return;
    try {
      await axios.delete(`${API}/rag/source/${encodeURIComponent(name)}`, { headers });
      toast.success("Quelle gelöscht");
      reload();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Fehler beim Löschen");
    }
  };

  return (
    <div className="space-y-6" data-testid="admin-rag-tab">
      {/* STATUS */}
      <Card className="p-5 bg-muted/30">
        <div className="flex items-center gap-4 flex-wrap text-sm">
          <Database className="w-5 h-5 text-amber-500" />
          <div>
            <span className="text-muted-foreground">KB: </span>
            <span className="font-bold" data-testid="admin-rag-kb-count">
              {status?.kb_document_count ?? "..."} Dokumente
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Modell: </span>
            <code className="text-xs bg-background px-2 py-0.5 rounded">{status?.model || "BGE-M3 (lazy)"}</code>
          </div>
          <div>
            <span className="text-muted-foreground">Status: </span>
            {status?.ready ? (
              <Badge className="bg-green-500/20 text-green-700">bereit</Badge>
            ) : (
              <Badge variant="secondary">initialisiert bei erster Abfrage</Badge>
            )}
          </div>
          <Button onClick={reload} size="sm" variant="outline" className="ml-auto gap-1.5" data-testid="admin-rag-refresh">
            <RefreshCw className="w-3.5 h-3.5" /> Aktualisieren
          </Button>
        </div>
      </Card>

      {/* INGEST TEXT */}
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <Upload className="w-5 h-5 text-amber-500" />
          <h3 className="font-bold">Text-Quelle importieren</h3>
        </div>
        <Textarea
          value={ingestText}
          onChange={(e) => setIngestText(e.target.value)}
          placeholder="Medizinischer Text / Leitlinie / Protokoll..."
          rows={5}
          className="mb-3"
          data-testid="admin-rag-ingest-text"
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <Input
            value={ingestName}
            onChange={(e) => setIngestName(e.target.value)}
            placeholder="Name der Quelle (z. B. 'S3-Leitlinie COPD 2024')"
            data-testid="admin-rag-ingest-name"
          />
          <select
            value={ingestCategory}
            onChange={(e) => setIngestCategory(e.target.value)}
            className="border rounded px-3 py-2 bg-background text-sm"
            data-testid="admin-rag-ingest-cat"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <Button onClick={doIngest} disabled={ingesting} data-testid="admin-rag-ingest-submit">
          {ingesting ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Importiere...</> : <><Upload className="w-4 h-4 mr-2" /> Text importieren</>}
        </Button>
      </Card>

      {/* INGEST PDF */}
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <FileUp className="w-5 h-5 text-amber-500" />
          <h3 className="font-bold">PDF importieren</h3>
        </div>
        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
          className="block w-full text-sm mb-3 border rounded px-3 py-2 bg-background"
          data-testid="admin-rag-pdf-file"
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <Input
            value={pdfName}
            onChange={(e) => setPdfName(e.target.value)}
            placeholder="Name (z. B. 'Herold Innere 2024')"
            data-testid="admin-rag-pdf-name"
          />
          <select
            value={pdfCategory}
            onChange={(e) => setPdfCategory(e.target.value)}
            className="border rounded px-3 py-2 bg-background text-sm"
            data-testid="admin-rag-pdf-cat"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <Button onClick={doIngestPdf} disabled={pdfUploading || !pdfFile} data-testid="admin-rag-pdf-submit">
          {pdfUploading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Verarbeite PDF...</> : <><FileUp className="w-4 h-4 mr-2" /> PDF importieren</>}
        </Button>
      </Card>

      {/* SOURCES LIST */}
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <Database className="w-5 h-5 text-amber-500" />
          <h3 className="font-bold">Aktuelle Quellen ({sources.length})</h3>
        </div>
        {loading && <Loader2 className="w-5 h-5 animate-spin" />}
        {!loading && sources.length === 0 && (
          <p className="text-sm text-muted-foreground">Noch keine Quellen. Import über die Felder oben.</p>
        )}
        <div className="space-y-1 max-h-96 overflow-y-auto">
          {sources.map((s, i) => (
            <div key={i} className="flex items-center gap-3 text-sm bg-muted/30 rounded px-3 py-2" data-testid={`admin-rag-source-${i}`}>
              <span className="font-semibold flex-1 min-w-0 truncate">{s.source}</span>
              <Badge variant="outline" className="text-[10px]">{s.category || "Allgemein"}</Badge>
              <span className="text-xs text-muted-foreground">{s.chunks} Chunks</span>
              <Button
                size="sm"
                variant="ghost"
                className="h-7 w-7 p-0"
                onClick={() => deleteSource(s.source)}
                data-testid={`admin-rag-delete-${i}`}
              >
                <Trash2 className="w-3.5 h-3.5 text-red-500" />
              </Button>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
