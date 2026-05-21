import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import {
  Sparkles, Loader2, Play, Pause, Headphones, Globe, Clock, FileText, Gauge,
} from "lucide-react";

const LANGS = [
  { id: "de", name: "Deutsch" },
  { id: "en", name: "English" },
  { id: "ar", name: "العربية" },
  { id: "ru", name: "Русский" },
];

export default function LerntoolsPage() {
  const { token } = useAuth();
  const [caseText, setCaseText] = useState("");
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("de");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playingId, setPlayingId] = useState(null);
  const [speed, setSpeed] = useState(1);
  const [audioCache, setAudioCache] = useState({});
  const audioRef = useRef(null);

  useEffect(() => {
    if (token) {
      axios.get(`${API}/podcast/custom?mine=true&limit=20`, {
        headers: { Authorization: `Bearer ${token}` },
      }).then(r => setHistory(r.data.items || [])).catch(() => {});
    }
    return () => { audioRef.current?.pause(); };
  }, [token]);

  const generate = async () => {
    if (!caseText.trim()) { toast.error("Bitte geben Sie einen medizinischen Fall ein"); return; }
    setGenerating(true);
    setResult(null);
    try {
      const res = await axios.post(`${API}/podcast/generate`, {
        case_text: caseText,
        title: title || undefined,
        language,
      }, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 600000,
      });
      const data = res.data;
      setResult(data);
      const { audio_base64, script, ...meta } = data;
      setHistory(prev => [meta, ...prev]);
      toast.success("Podcast erstellt!");
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || "Fehler bei der Generierung";
      toast.error(msg);
      if (e.code === "ECONNABORTED") toast.error("Zeitüberschreitung. Der Server braucht länger — bitte erneut versuchen.");
    } finally {
      setGenerating(false);
    }
  };

  const fetchAndPlay = async (item) => {
    let b64 = item.audio_base64 || audioCache[item.id];
    if (!b64) {
      const res = await axios.get(`${API}/podcast/custom/${item.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      b64 = res.data.audio_base64;
      setAudioCache(prev => ({ ...prev, [item.id]: b64 }));
    }
    audioRef.current.src = `data:audio/mp3;base64,${b64}`;
    await audioRef.current.play();
  };

  const togglePlay = (item) => {
    if (playingId === item.id && isPlaying) {
      audioRef.current?.pause();
      setIsPlaying(false);
      return;
    }
    if (audioRef.current) {
      fetchAndPlay(item).then(() => {
        setPlayingId(item.id);
        setIsPlaying(true);
      }).catch(() => {});
    }
  };

  const changeSpeed = (s) => {
    setSpeed(s);
    if (audioRef.current) audioRef.current.playbackRate = s;
  };

  const onEnded = () => { setIsPlaying(false); setPlayingId(null); };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="text-center mb-10">
        <h1 className="text-3xl sm:text-4xl font-bold mb-3" style={{ fontFamily: "'Playfair Display', serif", color: '#d4d4d8' }}>
          <span style={{ color: '#10b981' }}>Podcast</span> Generator
        </h1>
        <p style={{ color: '#8899aa' }}>Erstellen Sie eigene medizinische Podcasts aus Fallbeschreibungen</p>
      </div>

      <div className="rounded-2xl p-6 mb-8 space-y-4" style={{ background: '#0f1a3a', border: '1px solid rgba(16,185,129,0.12)' }}>
        <div>
          <label className="text-sm font-medium mb-1 block" style={{ color: '#d4d4d8' }}>
            <FileText className="w-4 h-4 inline mr-1" /> Medizinischer Fall
          </label>
          <Textarea
            value={caseText}
            onChange={e => setCaseText(e.target.value)}
            placeholder="Beschreiben Sie einen medizinischen Fall (Symptome, Befunde, Diagnose, Behandlung...)"
            rows={6}
            className="w-full rounded-lg bg-muted/50 border border-border px-3 py-2 text-sm resize-y"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium mb-1 block" style={{ color: '#d4d4d8' }}>Titel (optional)</label>
            <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="z.B. Polytrauma Fall" />
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block" style={{ color: '#d4d4d8' }}>
              <Globe className="w-4 h-4 inline mr-1" /> Sprache
            </label>
            <select value={language} onChange={e => setLanguage(e.target.value)}
              className="w-full h-10 rounded-lg bg-muted/50 border border-border px-3 text-sm">
              {LANGS.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>
        </div>

        <Button onClick={generate} disabled={generating || !caseText.trim()}
          className="gap-2 w-full sm:w-auto" style={{ background: 'linear-gradient(135deg, #10b981, #34d399)', color: '#06081a' }}>
          {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {generating ? "Wird generiert..." : "Podcast erstellen"}
        </Button>
      </div>

      {result && (
        <div className="rounded-2xl p-6 mb-8" style={{ background: '#0f1a3a', border: '1px solid rgba(16,185,129,0.2)' }}>
          <h3 className="font-semibold text-lg mb-3" style={{ color: '#d4d4d8' }}>{result.title}</h3>
          <div className="flex items-center gap-4 mb-4">
            <button onClick={() => togglePlay(result)}
              className="w-14 h-14 rounded-full flex items-center justify-center flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, #10b981, #34d399)' }}>
              {playingId === result.id && isPlaying ? <Pause className="w-6 h-6 text-[#06081a]" /> : <Play className="w-6 h-6 text-[#06081a] ml-1" />}
            </button>
            <div className="flex-1">
              <p className="text-sm" style={{ color: '#8899aa' }}>{result.language?.toUpperCase()} · {result.audio_size > 1000 ? `${(result.audio_size / 1024).toFixed(0)} KB` : `${result.audio_size} B`}</p>
            </div>
            <div className="flex items-center gap-1">
              <Gauge className="w-4 h-4" style={{ color: '#8899aa' }} />
              {[0.75, 1, 1.25, 1.5, 2].map(s => (
                <button key={s} onClick={() => changeSpeed(s)}
                  className="px-2 py-0.5 rounded text-xs font-medium transition-colors"
                  style={{
                    background: speed === s ? '#10b981' : 'transparent',
                    color: speed === s ? '#06081a' : '#8899aa',
                    border: '1px solid rgba(16,185,129,0.2)',
                  }}>
                  {s}x
                </button>
              ))}
            </div>
          </div>
          {result.script && (
            <details className="mt-4">
              <summary className="text-sm font-medium cursor-pointer" style={{ color: '#10b981' }}>Skript anzeigen</summary>
              <div className="mt-3 text-sm leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto rounded-lg p-4" style={{ background: '#06081a', color: '#d4d4d8', border: '1px solid rgba(16,185,129,0.1)' }}>
                {result.script}
              </div>
            </details>
          )}
        </div>
      )}

      {history.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-lg flex items-center gap-2" style={{ color: '#d4d4d8' }}>
              <Clock className="w-4 h-4" style={{ color: '#10b981' }} /> Meine Podcasts
            </h3>
            <div className="flex items-center gap-1">
              <Gauge className="w-4 h-4" style={{ color: '#8899aa' }} />
              {[0.75, 1, 1.25, 1.5, 2].map(s => (
                <button key={s} onClick={() => changeSpeed(s)}
                  className="px-2 py-0.5 rounded text-xs font-medium transition-colors"
                  style={{
                    background: speed === s ? '#10b981' : 'transparent',
                    color: speed === s ? '#06081a' : '#8899aa',
                    border: '1px solid rgba(16,185,129,0.2)',
                  }}>
                  {s}x
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            {history.map(item => (
              <div key={item.id} className="flex items-center gap-3 p-3 rounded-lg"
                style={{ background: '#0f1a3a', border: '1px solid rgba(16,185,129,0.08)' }}>
                <button onClick={() => togglePlay(item)}
                  className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{ background: 'linear-gradient(135deg, #10b981, #34d399)' }}>
                  {playingId === item.id && isPlaying ? <Pause className="w-4 h-4 text-[#06081a]" /> : <Play className="w-4 h-4 text-[#06081a] ml-0.5" />}
                </button>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: '#d4d4d8' }}>{item.title || "Custom Case"}</p>
                  <p className="text-xs" style={{ color: '#8899aa' }}>{item.language?.toUpperCase()} · {new Date(item.created_at).toLocaleDateString()}</p>
                </div>
                
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-col items-center justify-center py-12 gap-2" style={{ color: '#8899aa' }}>
        <Headphones className="w-8 h-8" />
        <p className="text-sm">Verwandeln Sie Ihre klinischen Fälle in Lernpodcasts</p>
      </div>
      <audio ref={audioRef} onEnded={onEnded} />
    </div>
  );
}
