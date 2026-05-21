import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import {
  Sparkles, Loader2, Play, Pause, Headphones, Globe, Clock, FileText,
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
  const audioRef = useRef(null);

  useEffect(() => {
    if (token) {
      axios.get(`${API}/podcast/custom?limit=20`, {
        headers: { Authorization: `Bearer ${token}` },
      }).then(r => setHistory(r.data.items || [])).catch(() => {});
    }
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
        timeout: 120000,
      });
      setResult(res.data);
      setHistory(prev => [res.data, ...prev]);
      toast.success("Podcast erstellt!");
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message || "Fehler bei der Generierung");
    } finally {
      setGenerating(false);
    }
  };

  const togglePlay = (item) => {
    if (playingId === item.id && isPlaying) {
      audioRef.current?.pause();
      setIsPlaying(false);
      return;
    }
    if (audioRef.current) {
      audioRef.current.src = `data:audio/mp3;base64,${item.audio_base64}`;
      audioRef.current.play().then(() => {
        setPlayingId(item.id);
        setIsPlaying(true);
      }).catch(() => {});
    }
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
          <div className="flex items-center gap-4">
            <button onClick={() => togglePlay(result)}
              className="w-14 h-14 rounded-full flex items-center justify-center flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, #10b981, #34d399)' }}>
              {playingId === result.id && isPlaying ? <Pause className="w-6 h-6 text-[#06081a]" /> : <Play className="w-6 h-6 text-[#06081a] ml-1" />}
            </button>
            <div className="flex-1">
              <p className="text-sm" style={{ color: '#8899aa' }}>{result.language?.toUpperCase()} · {result.audio_size > 1000 ? `${(result.audio_size / 1024).toFixed(0)} KB` : `${result.audio_size} B`}</p>
            </div>
          </div>
        </div>
      )}

      {history.length > 0 && (
        <div>
          <h3 className="font-semibold text-lg mb-4 flex items-center gap-2" style={{ color: '#d4d4d8' }}>
            <Clock className="w-4 h-4" style={{ color: '#10b981' }} /> Meine Podcasts
          </h3>
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
