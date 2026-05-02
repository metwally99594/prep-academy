import { useEffect, useState, useContext } from "react";
import axios from "axios";
import { AuthContext, API } from "@/App";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Loader2, Search, BookOpenCheck, Database, ShieldCheck, Upload, Trash2 } from "lucide-react";
import { toast } from "sonner";

const LANGS = [
  { id: "de", label: "🇩🇪 DE" },
  { id: "en", label: "🇬🇧 EN" },
  { id: "ar", label: "🇪🇬 AR" },
  { id: "ru", label: "🇷🇺 RU" },
  { id: "uk", label: "🇺🇦 UK" },
];

const MODELS = [
  { id: "deepseek/deepseek-chat-v3.1", label: "DeepSeek V3.1 (empfohlen)" },
  { id: "deepseek/deepseek-chat-v3-0324", label: "DeepSeek V3 0324 (günstiger)" },
  { id: "qwen/qwen3-235b-a22b-2507", label: "Qwen3 235B" },
];

function RagAnswer({ answer }) {
  if (!answer) return null;
  // Highlight [1], [2] citations
  const parts = answer.split(/(\[\d+\])/g);
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap leading-relaxed">
      {parts.map((p, i) =>
        /^\[\d+\]$/.test(p) ? (
          <sup key={i} className="ml-0.5 font-bold text-amber-600 dark:text-amber-400">
            {p}
          </sup>
        ) : (
          <span key={i}>{p}</span>
        )
      )}
    </div>
  );
}

export default function RagPage() {
  const { token, user } = useContext(AuthContext) || {};
  const [status, setStatus] = useState(null);
  const [sources, setSources] = useState([]);
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState(() => localStorage.getItem("rag_lang") || "de");
  const [model, setModel] = useState(MODELS[0].id);
  const [topK, setTopK] = useState(4);
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState("");
  const [answerSources, setAnswerSources] = useState([]);

  // Admin ingest
  const [ingestText, setIngestText] = useState("");
  const [ingestSource, setIngestSource] = useState("");
  const [ingestCategory, setIngestCategory] = useState("Allgemein");
  const [ingesting, setIngesting] = useState(false);

  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    localStorage.setItem("rag_lang", language);
  }, [language]);

  const loadStatus = async () => {
    try {
      const r = await axios.get(`${API}/rag/status`);
      setStatus(r.data);
    } catch {}
  };

  const loadSources = async () => {
    try {
      const r = await axios.get(`${API}/rag/sources`, { headers });
      setSources(r.data.sources || []);
      setStatus((s) => (s ? { ...s, kb_document_count: r.data.total_docs } : s));
    } catch {}
  };

  useEffect(() => {
    loadStatus();
    if (token) loadSources();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const runQuery = async () => {
    if (!query.trim()) {
      toast.error("Bitte eine Frage eingeben");
      return;
    }
    setLoading(true);
    setAnswer("");
    setAnswerSources([]);
    try {
      const r = await axios.post(
        `${API}/rag/query`,
        { query, language, top_k: topK, model },
        { headers, timeout: 120000 }
      );
      setAnswer(r.data.answer || "");
      setAnswerSources(r.data.sources || []);
      if (!status?.ready) loadStatus();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Anfrage fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  };

  const runIngest = async () => {
    if (!ingestText.trim() || !ingestSource.trim()) {
      toast.error("Text und Quelle sind Pflicht");
      return;
    }
    setIngesting(true);
    try {
      const r = await axios.post(
        `${API}/rag/ingest-text`,
        { content: ingestText, source: ingestSource, category: ingestCategory, language },
        { headers, timeout: 60000 }
      );
      toast.success(`${r.data.added_chunks} Abschnitte hinzugefügt`);
      setIngestText("");
      setIngestSource("");
      loadSources();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Import fehlgeschlagen");
    } finally {
      setIngesting(false);
    }
  };

  const deleteSource = async (name) => {
    if (!window.confirm(`Quelle "${name}" wirklich löschen?`)) return;
    try {
      await axios.delete(`${API}/rag/source/${encodeURIComponent(name)}`, { headers });
      toast.success("Quelle gelöscht");
      loadSources();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Löschen fehlgeschlagen");
    }
  };

  const isAdmin = user?.is_admin;

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl" data-testid="rag-page">
      <div className="flex items-center gap-3 mb-2">
        <ShieldCheck className="w-8 h-8 text-amber-500" />
        <h1 className="text-3xl font-bold">Medical RAG</h1>
        <Badge variant="secondary" className="text-xs">BGE-M3 + DeepSeek V3</Badge>
      </div>
      <p className="text-sm text-muted-foreground mb-6">
        Medizinische Fragen beantwortet aus verifizierten Quellen (ICD-10, WHO, RKI, S3-Leitlinien) — mit Zitaten.
      </p>

      {/* STATUS BAR */}
      <Card className="p-4 mb-6 bg-muted/40">
        <div className="flex items-center gap-6 flex-wrap text-sm">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-amber-500" />
            <span className="text-muted-foreground">KB:</span>
            <span className="font-bold" data-testid="rag-kb-count">
              {status?.kb_document_count ?? "..."} Dokumente
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Modell:</span>
            <code className="text-xs bg-background px-2 py-0.5 rounded">
              {status?.model || "BGE-M3 (lädt beim ersten Abruf)"}
            </code>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Status:</span>
            {status?.ready ? (
              <Badge className="bg-green-500/20 text-green-700 dark:text-green-300">bereit</Badge>
            ) : (
              <Badge variant="secondary">init on first query</Badge>
            )}
          </div>
        </div>
      </Card>

      {/* QUERY */}
      <Card className="p-5 mb-6">
        <label className="block text-sm font-semibold mb-2">Deine Frage</label>
        <Textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="z. B. Was ist die sofortige Therapie bei Hämatopneumothorax?"
          rows={3}
          className="mb-3"
          data-testid="rag-query-input"
        />

        <div className="flex flex-wrap gap-3 items-center mb-4">
          <div className="flex items-center gap-1">
            {LANGS.map((l) => (
              <Button
                key={l.id}
                size="sm"
                variant={language === l.id ? "default" : "outline"}
                onClick={() => setLanguage(l.id)}
                data-testid={`rag-lang-${l.id}`}
              >
                {l.label}
              </Button>
            ))}
          </div>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="text-sm border rounded px-2 py-1 bg-background"
            data-testid="rag-model-select"
          >
            {MODELS.map((m) => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
          <div className="flex items-center gap-2 text-sm">
            <label className="text-muted-foreground">top-K:</label>
            <input
              type="number"
              min="1"
              max="10"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value) || 4)}
              className="w-16 border rounded px-2 py-1 bg-background"
              data-testid="rag-topk-input"
            />
          </div>
        </div>

        <Button onClick={runQuery} disabled={loading} className="w-full" data-testid="rag-query-submit">
          {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Suche & Analyse...</> : <><Search className="w-4 h-4 mr-2" /> Anfrage senden</>}
        </Button>
      </Card>

      {/* ANSWER */}
      {(answer || answerSources.length > 0) && (
        <Card className="p-5 mb-6" data-testid="rag-answer-card">
          <div className="flex items-center gap-2 mb-3">
            <BookOpenCheck className="w-5 h-5 text-amber-500" />
            <h2 className="font-bold">Antwort</h2>
          </div>
          <RagAnswer answer={answer} />
          {answerSources.length > 0 && (
            <div className="mt-5 pt-4 border-t">
              <h3 className="text-sm font-bold mb-2 text-muted-foreground">Quellen:</h3>
              <div className="space-y-2">
                {answerSources.map((s) => (
                  <div
                    key={s.index}
                    className="text-xs bg-muted/50 rounded p-3"
                    data-testid={`rag-source-${s.index}`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline" className="text-amber-600 dark:text-amber-400">
                        [{s.index}]
                      </Badge>
                      <span className="font-semibold">{s.source}</span>
                      {s.code && <span className="text-muted-foreground">{s.code}</span>}
                      {s.score != null && (
                        <span className="ml-auto text-muted-foreground">
                          match: {(s.score * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>
                    <p className="text-muted-foreground">{s.excerpt}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* ADMIN PANEL */}
      {isAdmin && (
        <Card className="p-5 mb-6 border-amber-500/30" data-testid="rag-admin-panel">
          <div className="flex items-center gap-2 mb-4">
            <Upload className="w-5 h-5 text-amber-500" />
            <h2 className="font-bold">Admin: Wissensbasis verwalten</h2>
          </div>

          <label className="block text-sm font-semibold mb-1">Text-Inhalt</label>
          <Textarea
            value={ingestText}
            onChange={(e) => setIngestText(e.target.value)}
            placeholder="Medizinischer Text / Leitlinie / Protokoll..."
            rows={4}
            className="mb-3"
            data-testid="rag-ingest-text"
          />

          <div className="grid grid-cols-2 gap-3 mb-3">
            <input
              value={ingestSource}
              onChange={(e) => setIngestSource(e.target.value)}
              placeholder="Quellen-Name (z. B. S3-Leitlinie XY)"
              className="text-sm border rounded px-3 py-2 bg-background"
              data-testid="rag-ingest-source"
            />
            <input
              value={ingestCategory}
              onChange={(e) => setIngestCategory(e.target.value)}
              placeholder="Kategorie (z. B. Kardiologie)"
              className="text-sm border rounded px-3 py-2 bg-background"
              data-testid="rag-ingest-category"
            />
          </div>

          <Button onClick={runIngest} disabled={ingesting} size="sm" data-testid="rag-ingest-submit">
            {ingesting ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Importiere...</> : <><Upload className="w-4 h-4 mr-2" /> Text importieren</>}
          </Button>

          {sources.length > 0 && (
            <div className="mt-5 pt-4 border-t">
              <h3 className="text-sm font-bold mb-2">Aktuelle Quellen ({sources.length}):</h3>
              <div className="space-y-1 max-h-80 overflow-y-auto">
                {sources.map((s, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-xs bg-muted/30 rounded px-3 py-2"
                  >
                    <span className="font-semibold">{s.source}</span>
                    <Badge variant="outline" className="text-[10px]">{s.category}</Badge>
                    <span className="text-muted-foreground">{s.chunks} chunks</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="ml-auto h-7 w-7 p-0"
                      onClick={() => deleteSource(s.source)}
                      data-testid={`rag-delete-source-${i}`}
                    >
                      <Trash2 className="w-3.5 h-3.5 text-red-500" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
