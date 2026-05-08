import { useState, useEffect } from "react";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  Download, FileDown, Loader2, Lock, BookOpen, MapPin, ChevronRight,
} from "lucide-react";

const UNI_LABELS = {
  vienna: "Wien", wien: "Wien", innsbruck: "Innsbruck",
  graz: "Graz", andere: "Andere", linz: "Linz",
};

function uniLabel(id) {
  return UNI_LABELS[id] || (id ? id.charAt(0).toUpperCase() + id.slice(1) : "Andere");
}

export default function ExportPage() {
  const { user, token } = useAuth();
  const [categories, setCategories] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(null); // "subject-uni" key

  const canExport = user?.can_export_pdf || user?.is_permanent || user?.is_admin;

  useEffect(() => {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    axios.get(`${API}/export/categories`, { headers })
      .then(r => setCategories(r.data))
      .catch(() => toast.error("Fehler beim Laden"))
      .finally(() => setLoading(false));
  }, [token]);

  const downloadPDF = async (subject, university) => {
    if (!canExport) {
      toast.error("Kein Zugang zum PDF-Export");
      return;
    }
    const key = `${subject}-${university}`;
    setDownloading(key);
    try {
      const url = `${API}/export/questions/pdf?subject=${encodeURIComponent(subject)}&university=${encodeURIComponent(university)}`;
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Export fehlgeschlagen");
      }
      const blob = await response.blob();
      const disp = response.headers.get("content-disposition") || "";
      const nameMatch = disp.match(/filename="([^"]+)"/);
      const filename = nameMatch ? nameMatch[1] : `PrepAcademy_Export.pdf`;
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      toast.error(err.message || "Download fehlgeschlagen");
    } finally {
      setDownloading(null);
    }
  };

  const DownloadBtn = ({ subject, university, label, variant = "outline" }) => {
    const key = `${subject}-${university}`;
    const busy = downloading === key;
    return (
      <button
        onClick={() => downloadPDF(subject, university)}
        disabled={!!downloading || !canExport}
        className={`flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg border transition-all disabled:opacity-50 disabled:cursor-not-allowed
          ${variant === "primary"
            ? "bg-amber-500/15 border-amber-500/30 text-amber-300 hover:bg-amber-500/25"
            : "border-border text-muted-foreground hover:border-primary/40 hover:text-foreground"
          }`}
      >
        {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
        {label}
      </button>
    );
  };

  if (loading) return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
    </div>
  );

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2.5 rounded-xl bg-amber-500/10">
          <FileDown className="w-5 h-5 text-amber-500" />
        </div>
        <div>
          <h1 className="text-xl font-bold">Fragen exportieren</h1>
          <p className="text-sm text-muted-foreground">
            PDF zum Drucken oder Teilen herunterladen
          </p>
        </div>
      </div>

      {/* Access locked */}
      {!canExport && (
        <div className="glass-card rounded-2xl p-6 flex items-center gap-4 border-amber-500/20 bg-amber-500/5">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center shrink-0">
            <Lock className="w-6 h-6 text-amber-500/70" />
          </div>
          <div>
            <h3 className="font-semibold mb-1">Export nicht freigeschaltet</h3>
            <p className="text-sm text-muted-foreground">
              Der PDF-Export ist nur für freigeschaltete Nutzer verfügbar. Kontaktieren Sie den Administrator.
            </p>
          </div>
        </div>
      )}

      {categories && (
        <>
          {/* All questions card */}
          <div className="glass-card rounded-2xl p-6 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-primary/10">
                <BookOpen className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h2 className="font-semibold">Alle Fragen</h2>
                <p className="text-sm text-muted-foreground">{categories.total.toLocaleString()} Fragen gesamt</p>
              </div>
            </div>
            <DownloadBtn subject="all" university="all" label="Download PDF" variant="primary" />
          </div>

          {/* Per-subject grid */}
          <div>
            <h2 className="font-semibold mb-3 flex items-center gap-2 text-sm text-muted-foreground uppercase tracking-wide">
              <MapPin className="w-3.5 h-3.5" /> Nach Fachgebiet
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {categories.subjects.map(s => (
                <div key={s.id} className="glass-card rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="font-medium text-sm">{s.name}</h3>
                      <span className="text-xs text-muted-foreground">{s.count} Fragen</span>
                    </div>
                    <ChevronRight className="w-4 h-4 text-muted-foreground/40" />
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <DownloadBtn subject={s.id} university="all" label="Alle" />
                    {categories.universities.slice(0, 3).map(u => (
                      <DownloadBtn key={u.id} subject={s.id} university={u.id} label={uniLabel(u.id)} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Per-university section */}
          {categories.universities.length > 0 && (
            <div>
              <h2 className="font-semibold mb-3 flex items-center gap-2 text-sm text-muted-foreground uppercase tracking-wide">
                <MapPin className="w-3.5 h-3.5" /> Nach Standort
              </h2>
              <div className="flex flex-wrap gap-3">
                {categories.universities.map(u => (
                  <div key={u.id} className="glass-card rounded-xl p-4 flex items-center gap-4">
                    <div>
                      <h3 className="font-medium text-sm">{uniLabel(u.id)}</h3>
                      <span className="text-xs text-muted-foreground">{u.count} Fragen</span>
                    </div>
                    <DownloadBtn subject="all" university={u.id} label="Download" variant="primary" />
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
