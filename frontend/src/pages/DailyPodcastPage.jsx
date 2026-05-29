import { useEffect, useState, useContext, useRef } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { AuthContext, API } from "@/App";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Loader2, Play, Pause, Calendar, Sparkles, Headphones, RotateCcw, Lock } from "lucide-react";

const LANGS = [
  { id: "de", label: "🇩🇪 Deutsch" },
  { id: "en", label: "🇬🇧 English" },
  { id: "ar", label: "🇪🇬 العربية" },
  { id: "ru", label: "🇷🇺 Русский" },
  { id: "uk", label: "🇺🇦 Українська" },
];

function parseScript(script) {
  const segments = [];
  const parts = script.split(/(\[Moderator\]|\[Experte\])/);
  let currentRole = null;
  parts.forEach(part => {
    if (part === '[Moderator]') currentRole = 'moderator';
    else if (part === '[Experte]') currentRole = 'experte';
    else if (part.trim() && currentRole) {
      segments.push({ role: currentRole, text: part.trim() });
    }
  });
  if (segments.length === 0 && script.trim()) segments.push({ role: "moderator", text: script.trim() });
  return segments;
}

export default function DailyPodcastPage() {
  const { token } = useContext(AuthContext) || {};
  const [language, setLanguage] = useState(() => localStorage.getItem("podcast_lang") || "de");
  const [current, setCurrent] = useState(null);
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [locked, setLocked] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [segments, setSegments] = useState([]);
  const [currentSegment, setCurrentSegment] = useState(-1);


  const [showScript, setShowScript] = useState(false);
  const [showCustomScript, setShowCustomScript] = useState(false);
  const [customPodcasts, setCustomPodcasts] = useState([]);
  const [customPlaying, setCustomPlaying] = useState(null);
  const [customScript, setCustomScript] = useState(null);

  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const stopSpeech = () => {
    window.speechSynthesis?.cancel();
    setPlaying(false);
    setCurrentSegment(-1);
  };

  const _voices = useRef([]);
  useEffect(() => {
    const grab = () => { _voices.current = window.speechSynthesis?.getVoices() || []; };
    grab();
    window.speechSynthesis?.addEventListener("voiceschanged", grab);
    return () => window.speechSynthesis?.removeEventListener("voiceschanged", grab);
  }, []);

  const _pickVoice = (role) => {
    const lang = language === "de" ? "de" : language === "en" ? "en" : language === "ar" ? "ar" : language === "ru" ? "ru" : "uk";
    const all = _voices.current.filter(v => v.lang.startsWith(lang));
    if (role === "moderator") {
      return all.find(v => /male|david|christoph|stefan|heiner|markus/i.test(v.name)) || all[0] || null;
    } else {
      return all.find(v => /female|zira|hedda|katja|elke|sabina|hanna/i.test(v.name)) || all[0] || null;
    }
  };

  const speakScript = (script) => {
    window.speechSynthesis?.cancel();
    const segs = parseScript(script);
    if (segs.length === 0) return;
    setSegments(segs);
    let index = 0;
    const speakNext = () => {
      if (index >= segs.length) { stopSpeech(); return; }
      const { role, text } = segs[index];
      const u = new SpeechSynthesisUtterance(text);
      u.lang = language === "de" ? "de-DE" : language === "en" ? "en-US" : language === "ar" ? "ar-SA" : language === "ru" ? "ru-RU" : "uk-UA";
      u.rate = 0.9;
      u.voice = _pickVoice(role);
      u.pitch = role === "moderator" ? 0.85 : 1.25;
      u.onstart = () => { setCurrentSegment(index); setPlaying(true); };
      u.onend = () => {
        setCurrentSegment(index);
        index++;
        if (index < segs.length) speakNext();
        else stopSpeech();
      };
      window.speechSynthesis.speak(u);
    };
    speakNext();
  };

  const togglePlay = () => {
    if (playing) {
      stopSpeech();
    } else {
      speakScript(current?.script || "");
    }
  };

  const segmentProgress = segments.length > 0 && currentSegment >= 0
    ? Math.round(((currentSegment + 1) / segments.length) * 100) : 0;

  useEffect(() => { localStorage.setItem("podcast_lang", language); }, [language]);

  useEffect(() => {
    return () => { window.speechSynthesis?.cancel(); };
  }, []);

  const loadDaily = async (id = null) => {
    setLoading(true);
    setCurrent(null);
    setLocked(false);
    stopSpeech();
    try {
      const url = id ? `${API}/podcast/${id}` : `${API}/podcast/daily?language=${language}`;
      const res = await axios.get(url, { headers });
      setCurrent(res.data);
      setSegments(parseScript(res.data.script || ""));
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

  const loadCustom = async () => {
    try {
      const res = await axios.get(`${API}/podcast/custom?limit=10`, { headers });
      setCustomPodcasts(res.data.items || []);
    } catch { setCustomPodcasts([]); }
  };

  useEffect(() => { loadDaily(); loadList(); loadCustom(); /* eslint-disable-next-line */ }, [language]);

  const playCustom = async (item) => {
    if (customPlaying === item.id) {
      stopSpeech();
      setCustomPlaying(null);
      setCustomScript(null);
      return;
    }
    stopSpeech();
    try {
      const res = await axios.get(`${API}/podcast/custom/${item.id}`, { headers });
      setCustomPlaying(item.id);
      setCustomScript(res.data.script || null);
      speakScript(res.data.script || "");
    } catch { setCustomPlaying(null); }
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

            {/* Web Speech API player */}
            <div className="space-y-4">
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-amber-500 transition-all" style={{ width: `${segmentProgress}%` }} />
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{playing && currentSegment >= 0 ? `${currentSegment + 1}/${segments.length}` : ""}</span>
                <span>{segments.length} Abschnitte</span>
              </div>

              <div className="flex items-center justify-center gap-3">
                <Button onClick={togglePlay} className="h-16 w-16 rounded-full bg-amber-500 hover:bg-amber-600 text-amber-950" data-testid="play-pause-btn">
                  {playing ? <Pause className="w-7 h-7" fill="currentColor" /> : <Play className="w-7 h-7 ml-1" fill="currentColor" />}
                </Button>
              </div>
            </div>

            {/* Script toggle */}
            <div className="mt-6 pt-4 border-t border-border/30">
              <button onClick={() => setShowScript(s => !s)} className="text-sm text-muted-foreground hover:text-foreground" data-testid="toggle-script-btn">
                {showScript ? "Skript ausblenden" : "Skript anzeigen"}
              </button>
            </div>

            {showScript && current.script && (
              <div className="mt-4 space-y-2">
                {segments.map((seg, i) => (
                  <div key={i} className={`p-3 rounded-lg text-sm leading-relaxed ${i === currentSegment && playing ? 'bg-amber-500/10 border border-amber-500/30' : 'bg-muted/30'} ${seg.role === "moderator" ? "border-l-4 border-l-blue-400" : "border-l-4 border-l-amber-400"}`}>
                    <span className="text-xs font-semibold uppercase text-muted-foreground">{seg.role}</span>
                    <p className="mt-1">{seg.text}</p>
                  </div>
                ))}
              </div>
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

          {/* Custom Podcasts */}
          <Card className="p-6 border-amber-500/30 bg-gradient-to-br from-amber-500/[0.03] to-transparent">
            <h3 className="font-semibold text-lg mb-1 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-500" /> Custom Podcasts
            </h3>
            <p className="text-xs text-muted-foreground mb-4">Von der Admin erstellte Folgen basierend auf individuellen Fällen</p>
            {customPodcasts.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">Noch keine Custom-Podcasts vorhanden.</p>
            ) : (
              <div className="space-y-2">
                {customPodcasts.map(item => (
                  <div key={item.id}>
                    <div className="flex items-center gap-3 p-3 rounded-lg border border-border/30 hover:border-amber-500/40 transition-all">
                      <button onClick={() => playCustom(item)}
                        className="h-9 w-9 rounded-full flex items-center justify-center bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 shrink-0 transition-all">
                        {customPlaying === item.id && playing ? <Pause className="w-4 h-4" fill="currentColor" /> : <Play className="w-4 h-4 ml-0.5" fill="currentColor" />}
                      </button>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate">{item.title}</div>
                        <div className="text-[11px] text-muted-foreground">
                          {new Date(item.created_at).toLocaleDateString('de-DE')} · {item.specialty} · {item.language?.toUpperCase()}
                        </div>
                      </div>
                      {customPlaying === item.id && customScript && (
                        <button onClick={() => setShowCustomScript(s => !s)} className="text-xs text-amber-500 hover:text-amber-400 shrink-0">
                          {showCustomScript ? "Ausblenden" : "Skript"}
                        </button>
                      )}
                    </div>
                    {customPlaying === item.id && showCustomScript && customScript && (
                      <pre className="mt-2 p-3 bg-muted/50 rounded-lg text-xs overflow-auto max-h-60 whitespace-pre-wrap font-sans leading-relaxed ml-2 mr-2">
                        {customScript}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      )}

      <div className="mt-8 text-center">
        <p className="text-xs text-muted-foreground">
          🎙️ Generiert mit Qwen3-235B (Alibaba) · Webbasierte Sprachausgabe (Web Speech API) · Aktualisiert alle 24 Stunden
        </p>
        <Link to="/" className="text-amber-500 hover:text-amber-400 text-sm font-medium" data-testid="back-home">← Zurück zur Startseite</Link>
      </div>
    </div>
  );
}
