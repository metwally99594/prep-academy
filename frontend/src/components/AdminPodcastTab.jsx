import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { API } from "@/App";
import { toast } from "sonner";
import { Loader2, RefreshCw, Calendar, Headphones, Play, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const LANGS = [
  { id: "de", label: "🇩🇪 Deutsch" },
  { id: "en", label: "🇬🇧 English" },
  { id: "ar", label: "🇪🇬 العربية" },
  { id: "ru", label: "🇷🇺 Русский" },
  { id: "uk", label: "🇺🇦 Українська" },
];

export default function AdminPodcastTab({ token }) {
  const [generating, setGenerating] = useState({});
  const [generatingAll, setGeneratingAll] = useState(false);
  const [todayStatus, setTodayStatus] = useState({});
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [previewAudio, setPreviewAudio] = useState(null);

  const [customCase, setCustomCase] = useState("");
  const [customLang, setCustomLang] = useState("de");
  const [customTitle, setCustomTitle] = useState("");
  const [customBusy, setCustomBusy] = useState(false);
  const [customResult, setCustomResult] = useState(null);
  const [customPodcasts, setCustomPodcasts] = useState([]);
  const audioRef = useRef(null);

  const headers = { Authorization: `Bearer ${token}` };

  const loadStatus = async () => {
    setLoading(true);
    const status = {};
    const allHistory = [];
    for (const l of LANGS) {
      try {
        const res = await axios.get(`${API}/podcast/list?language=${l.id}&limit=10`);
        const items = res.data.items || [];
        const today = new Date().toISOString().slice(0, 10);
        status[l.id] = items.find(i => i.date === today) || null;
        allHistory.push(...items.map(i => ({ ...i, lang: l.id })));
      } catch {
        status[l.id] = null;
      }
    }
    allHistory.sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
    setTodayStatus(status);
    setHistory(allHistory.slice(0, 30));
    setLoading(false);
  };

  useEffect(() => { loadStatus(); loadCustomPodcasts(); /* eslint-disable-next-line */ }, []);

  const loadCustomPodcasts = async () => {
    try {
      const res = await axios.get(`${API}/podcast/custom?limit=20`, { headers });
      setCustomPodcasts(res.data.items || []);
    } catch {}
  };

  const generateCustom = async () => {
    if (!customCase.trim()) { toast.error("Bitte Fallbeschreibung eingeben"); return; }
    setCustomBusy(true);
    setCustomResult(null);
    try {
      const res = await axios.post(`${API}/podcast/admin/custom`,
        { language: customLang, case_text: customCase, title: customTitle.trim() || undefined },
        { headers, timeout: 180000 }
      );
      toast.success(`✅ Podcast "${res.data.title}" generiert`);
      setCustomResult(res.data);
      await loadCustomPodcasts();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Generierung fehlgeschlagen");
    } finally {
      setCustomBusy(false);
    }
  };

  const generate = async (langId) => {
    setGenerating(prev => ({ ...prev, [langId]: true }));
    try {
      const res = await axios.post(`${API}/podcast/admin/generate`,
        { language: langId, force: true },
        { headers, timeout: 180000 }
      );
      toast.success(`✅ ${LANGS.find(l => l.id === langId).label}: "${res.data.title}" generiert`);
      await loadStatus();
    } catch (err) {
      toast.error(err.response?.data?.detail || `Fehler bei ${langId}`);
    } finally {
      setGenerating(prev => ({ ...prev, [langId]: false }));
    }
  };

  const generateAll = async () => {
    setGeneratingAll(true);
    for (const l of LANGS) {
      await generate(l.id);
    }
    setGeneratingAll(false);
    toast.success("Alle 5 Sprachen generiert!");
  };

  const playPreview = async (item) => {
    try {
      const res = await axios.get(`${API}/podcast/${item.id}`, { headers });
      const audio = new Audio(`data:audio/mp3;base64,${res.data.audio_base64}`);
      if (previewAudio) { previewAudio.pause(); }
      setPreviewAudio(audio);
      audio.play();
    } catch {
      toast.error("Wiedergabe fehlgeschlagen");
    }
  };

  return (
    <div className="space-y-6" data-testid="admin-podcast-tab">
      <Card className="p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold flex items-center gap-2">
              <Headphones className="w-5 h-5 text-amber-500" />
              Daily Podcast — Manuelle Steuerung
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Auto-Generierung läuft alle 6h. Hier kannst du sofort eine neue Folge erzwingen.
            </p>
          </div>
          <Button onClick={generateAll} disabled={generatingAll} className="bg-amber-500 hover:bg-amber-600 text-amber-950" data-testid="generate-all-btn">
            {generatingAll ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />}
            Alle 5 Sprachen neu generieren
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {LANGS.map(l => {
            const t = todayStatus[l.id];
            const busy = generating[l.id];
            return (
              <div key={l.id} className={`p-3 rounded-xl border ${t ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-amber-500/30 bg-amber-500/5'}`} data-testid={`podcast-status-${l.id}`}>
                <div className="text-sm font-bold mb-1">{l.label}</div>
                {loading ? (
                  <div className="text-xs text-muted-foreground flex items-center gap-1.5"><Loader2 className="w-3 h-3 animate-spin" /> Lädt...</div>
                ) : t ? (
                  <>
                    <div className="text-xs text-emerald-400 mb-1">✓ Heute generiert</div>
                    <div className="text-xs font-medium line-clamp-2 mb-2">{t.title}</div>
                    <div className="text-[10px] text-muted-foreground mb-2">{t.specialty}{t.source_year ? ` · ${t.source_year}` : ''}</div>
                  </>
                ) : (
                  <div className="text-xs text-amber-400 mb-2">⚠ Heute fehlt</div>
                )}
                <Button onClick={() => generate(l.id)} disabled={busy} size="sm" variant="outline" className="w-full h-7 text-xs" data-testid={`generate-${l.id}-btn`}>
                  {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3 mr-1" />}
                  {busy ? "..." : t ? "Neu" : "Generieren"}
                </Button>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Custom Case Podcast */}
      <Card className="p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-500" />
              Custom Case → Podcast
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Gib eine medizinische Fallbeschreibung ein und generiere daraus einen Podcast.
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Sprache</label>
            <select value={customLang} onChange={e => setCustomLang(e.target.value)}
              className="w-full mt-1 p-2 rounded-lg border border-border bg-background text-sm">
              {LANGS.map(l => <option key={l.id} value={l.id}>{l.label}</option>)}
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">Titel (optional)</label>
            <input value={customTitle} onChange={e => setCustomTitle(e.target.value)}
              placeholder="z.B. Fall: Akute Pankreatitis"
              className="w-full mt-1 p-2 rounded-lg border border-border bg-background text-sm" />
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">Fallbeschreibung</label>
            <textarea value={customCase} onChange={e => setCustomCase(e.target.value)}
              placeholder="Beschreibe den medizinischen Fall (Symptome, Diagnostik, Therapie, Differentialdiagnosen...)"
              rows={5}
              className="w-full mt-1 p-3 rounded-lg border border-border bg-background text-sm resize-y" />
          </div>

          <Button onClick={generateCustom} disabled={customBusy || !customCase.trim()}
            className="bg-amber-500 hover:bg-amber-600 text-amber-950 w-full gap-2">
            {customBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {customBusy ? "Generiere..." : "Podcast generieren"}
          </Button>

          {customResult && customResult.audio_base64 && (
            <div className="p-3 rounded-xl border border-emerald-500/30 bg-emerald-500/5">
              <div className="text-xs text-emerald-400 mb-1">✅ Generiert: {customResult.title}</div>
              <div className="text-[11px] text-muted-foreground mb-2">{customResult.language?.toUpperCase()} · {customResult.specialty}</div>
              <audio controls className="w-full h-8"
                src={`data:audio/mp3;base64,${customResult.audio_base64}`} />
            </div>
          )}
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Calendar className="w-5 h-5 text-amber-500" />
          Verlauf (letzte 30 Folgen)
        </h3>
        {history.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">Noch keine Folgen generiert.</p>
        ) : (
          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {history.map(item => (
              <div key={item.id} className="flex items-center gap-3 p-3 rounded-lg border border-border/30 hover:border-amber-500/30 transition-colors">
                <div className="text-xs px-2 py-1 rounded font-bold bg-muted">{LANGS.find(l => l.id === item.lang)?.label.split(' ')[0]}</div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{item.title}</div>
                  <div className="text-[11px] text-muted-foreground">
                    {new Date(item.created_at).toLocaleDateString('de-DE')} · {item.specialty}
                    {item.source_mode === "mcq" && (
                      <span className="ml-2 px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px]">📝 {item.source_city || ''} {item.source_year || ''}</span>
                    )}
                  </div>
                </div>
                <Button size="sm" variant="ghost" onClick={() => playPreview(item)} className="h-8 w-8 p-0" data-testid={`play-${item.id}`}>
                  <Play className="w-3.5 h-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="text-center text-xs text-muted-foreground">
        🤖 Automatische Generierung: alle 6 Stunden für alle 5 Sprachen · Quelle: 3000+ MCQ-Datenbank · Kosten: $0
      </div>
    </div>
  );
}
