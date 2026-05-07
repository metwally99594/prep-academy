import { useEffect, useState, useContext, useRef } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { AuthContext, API } from "@/App";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Loader2, Play, Pause, SkipBack, SkipForward, Calendar, Sparkles, Headphones, RotateCcw, Lock } from "lucide-react";

const LANGS = [
  { id: "de", label: "🇩🇪 Deutsch" },
  { id: "en", label: "🇬🇧 English" },
  { id: "ar", label: "🇪🇬 العربية" },
  { id: "ru", label: "🇷🇺 Русский" },
  { id: "uk", label: "🇺🇦 Українська" },
];

export default function DailyPodcastPage() {
  const { token } = useContext(AuthContext) || {};
  const [language, setLanguage] = useState(() => localStorage.getItem("podcast_lang") || "de");
  const [current, setCurrent] = useState(null);
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [locked, setLocked] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showScript, setShowScript] = useState(false);
  const audioRef = useRef(null);

  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  useEffect(() => { localStorage.setItem("podcast_lang", language); }, [language]);

  const loadDaily = async (id = null) => {
    setLoading(true);
    setCurrent(null);
    setLocked(false);
    try {
      const url = id ? `${API}/podcast/${id}` : `${API}/podcast/daily?language=${language}`;
      const res = await axios.get(url, { headers });
      setCurrent(res.data);
    } catch (err) {
      if (err?.response?.status === 403) setLocked(true);
      else setCurrent(null);
    } finally {
      setLoading(false);
    }
  };

  const loadList = async () => {
    try {
      const res = await axios.get(`${API}/podcast/list?language=${language}`, { headers });
      setList(res.data.items || []);
    } catch { setList([]); }
  };

  useEffect(() => { loadDaily(); loadList(); /* eslint-disable-next-line */ }, [language]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (playing) audioRef.current.pause(); else audioRef.current.play();
  };

  const seek = (delta) => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = Math.max(0, Math.min(audioRef.current.duration || 0, audioRef.current.currentTime + delta));
  };

  const fmt = (s) => {
    if (!s || isNaN(s)) return "0:00";
    const m = Math.floor(s / 60), sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-10" data-testid="daily-podcast-page">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-3">
          <Headphones className="w-3.5 h-3.5" /> Daily Medical Podcast
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold mb-2" style={{fontFamily: 'Playfair Display, serif'}}>
          5 Minuten <span className="text-amber-500">Medizin</span> pro Tag
        </h1>
        <p className="text-muted-foreground text-base mb-5">Jeden Tag ein neuer klinischer Fall — für freigeschaltete Benutzer</p>

        <div className="inline-flex flex-wrap gap-1.5 p-1 bg-muted/30 border border-border rounded-xl">
          {LANGS.map(l => (
            <button key={l.id} onClick={() => setLanguage(l.id)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${language === l.id ? 'bg-amber-500 text-amber-950' : 'text-muted-foreground hover:text-foreground'}`}
              data-testid={`lang-${l.id}-btn`}>
              {l.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20"><Loader2 className="w-10 h-10 animate-spin text-amber-500" /></div>
      ) : locked ? (
        <Card className="p-10 text-center" data-testid="podcast-locked">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 bg-amber-500/10">
            <Lock className="w-8 h-8 text-amber-500/70" />
          </div>
          <h2 className="text-xl font-semibold mb-2">Zugang nicht freigeschaltet</h2>
          <p className="text-muted-foreground text-sm">
            Der Daily Podcast ist nur für freigeschaltete Benutzer verfügbar.<br />
            Kontaktieren Sie den Administrator, um Zugang zu erhalten.
          </p>
        </Card>
      ) : !current ? (
        <Card className="p-10 text-center">
          <Sparkles className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
          <h2 className="text-xl font-semibold mb-2">Heute noch nicht verfügbar</h2>
          <p className="text-muted-foreground text-sm mb-4">
            Der heutige Podcast wird gerade vorbereitet. Schau in ein paar Minuten wieder vorbei.
          </p>
          <Button onClick={() => loadDaily()} variant="outline" data-testid="reload-btn"><RotateCcw className="w-4 h-4 mr-2" /> Erneut versuchen</Button>
        </Card>
      ) : (
        <>
          <Card className="p-6 md:p-8 mb-6 bg-gradient-to-br from-amber-500/5 to-transparent border-amber-500/20">
            <div className="flex items-center gap-2 text-xs text-amber-400 font-semibold uppercase tracking-wider mb-2 flex-wrap">
              <Calendar className="w-3.5 h-3.5" /> {new Date(current.created_at).toLocaleDateString('de-DE', { dateStyle: 'long' })}
              <span className="px-2 py-0.5 rounded bg-amber-500/10">{current.specialty}</span>
              {current.source_mode === "mcq" && current.source_year && (
                <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px]">
                  📝 Echte Prüfungsfrage · {current.source_city || ""} {current.source_year}
                </span>
              )}
            </div>
            <h2 className="text-2xl md:text-3xl font-bold mb-3" style={{fontFamily: 'Playfair Display, serif'}} data-testid="podcast-title">
              {current.title}
            </h2>
            {current.summary && <p className="text-muted-foreground text-sm md:text-base mb-6 leading-relaxed">{current.summary}</p>}

            <audio
              ref={audioRef}
              src={`data:audio/mp3;base64,${current.audio_base64}`}
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onTimeUpdate={(e) => setProgress(e.target.currentTime)}
              onLoadedMetadata={(e) => setDuration(e.target.duration)}
              onEnded={() => setPlaying(false)}
            />

            <div className="space-y-4">
              <div className="h-2 bg-muted rounded-full overflow-hidden cursor-pointer" onClick={(e) => {
                if (!audioRef.current?.duration) return;
                const rect = e.currentTarget.getBoundingClientRect();
                audioRef.current.currentTime = ((e.clientX - rect.left) / rect.width) * audioRef.current.duration;
              }}>
                <div className="h-full bg-amber-500 transition-all" style={{ width: duration ? `${(progress / duration) * 100}%` : '0%' }} />
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
                <span>{fmt(progress)}</span>
                <span>{fmt(duration)}</span>
              </div>

              <div className="flex items-center justify-center gap-3">
                <Button variant="outline" size="icon" onClick={() => seek(-10)} className="h-12 w-12 rounded-full" data-testid="seek-back-btn">
                  <SkipBack className="w-5 h-5" />
                </Button>
                <Button onClick={togglePlay} className="h-16 w-16 rounded-full bg-amber-500 hover:bg-amber-600 text-amber-950" data-testid="play-pause-btn">
                  {playing ? <Pause className="w-7 h-7" fill="currentColor" /> : <Play className="w-7 h-7 ml-1" fill="currentColor" />}
                </Button>
                <Button variant="outline" size="icon" onClick={() => seek(10)} className="h-12 w-12 rounded-full" data-testid="seek-forward-btn">
                  <SkipForward className="w-5 h-5" />
                </Button>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-border/30 flex items-center justify-between text-sm">
              <button onClick={() => setShowScript(s => !s)} className="text-muted-foreground hover:text-foreground" data-testid="toggle-script-btn">
                {showScript ? "Skript ausblenden" : "Skript anzeigen"}
              </button>
              <a href={`data:audio/mp3;base64,${current.audio_base64}`} download={`podcast-${current.date}-${current.language}.mp3`} className="text-amber-500 hover:text-amber-400 text-sm font-medium" data-testid="download-mp3-btn">
                MP3 herunterladen
              </a>
            </div>

            {showScript && current.script && (
              <pre className="mt-4 p-4 bg-muted/50 rounded-lg text-xs overflow-auto max-h-96 whitespace-pre-wrap font-sans leading-relaxed">
                {current.script}
              </pre>
            )}
          </Card>

          {list.length > 1 && (
            <Card className="p-6">
              <h3 className="font-semibold text-lg mb-4">Frühere Folgen</h3>
              <div className="space-y-2">
                {list.map(item => (
                  <button key={item.id} onClick={() => loadDaily(item.id)}
                    className={`w-full text-left p-3 rounded-lg border border-border/30 hover:border-amber-500/40 hover:bg-amber-500/5 transition-all ${current?.id === item.id ? 'bg-amber-500/10 border-amber-500/40' : ''}`}
                    data-testid={`history-${item.id}`}>
                    <div className="text-xs text-muted-foreground mb-1">{new Date(item.created_at).toLocaleDateString('de-DE')} · {item.specialty}</div>
                    <div className="font-medium text-sm">{item.title}</div>
                  </button>
                ))}
              </div>
            </Card>
          )}
        </>
      )}

      <div className="mt-8 text-center">
        <p className="text-xs text-muted-foreground">
          🎙️ Generiert mit Qwen3-235B (Alibaba) + Microsoft Edge TTS · Aktualisiert alle 24 Stunden
        </p>
        <Link to="/" className="text-amber-500 hover:text-amber-400 text-sm font-medium" data-testid="back-home">← Zurück zur Startseite</Link>
      </div>
    </div>
  );
}
