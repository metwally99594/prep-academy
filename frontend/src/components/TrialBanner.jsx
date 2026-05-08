import { useState } from "react";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Clock, Crown, Gift, X, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function TrialBanner() {
  const { user, token } = useAuth();
  const [dismissed, setDismissed] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [requested, setRequested] = useState(false);

  if (!user || user.is_admin || dismissed) return null;

  const isPermanent = user.is_permanent;
  const trialEndsAt = user.trial_ends_at;
  const hasTrial = !!trialEndsAt;

  // Calculate days left
  let daysLeft = 0;
  if (trialEndsAt) {
    const delta = new Date(trialEndsAt) - Date.now();
    daysLeft = Math.max(0, Math.floor(delta / 86400000));
  }

  const isExpired = hasTrial && daysLeft === 0;
  const isUrgent  = hasTrial && daysLeft > 0 && daysLeft <= 7;
  const isActive  = hasTrial && daysLeft > 0;

  // Don't show banner for permanent users unless just made permanent
  if (isPermanent) {
    return null;
  }

  // Don't show if no trial info yet
  if (!hasTrial) return null;

  const requestExtension = async () => {
    setRequesting(true);
    try {
      await axios.post(`${API}/trial/request-extension`,
        { message: "" },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setRequested(true);
      toast.success("Verlängerungsanfrage gesendet");
    } catch (err) {
      const detail = err.response?.data?.detail || "";
      if (detail.includes("ausstehende")) {
        setRequested(true);
        toast.info("Anfrage bereits gestellt");
      } else {
        toast.error(detail || "Fehler beim Senden");
      }
    } finally {
      setRequesting(false);
    }
  };

  // Styles per state
  const styles = isExpired
    ? { bg: "bg-red-950/80 border-red-500/30", text: "text-red-200", icon: <Clock className="w-4 h-4 text-red-400 shrink-0" /> }
    : isUrgent
    ? { bg: "bg-amber-950/80 border-amber-500/30", text: "text-amber-200", icon: <Clock className="w-4 h-4 text-amber-400 shrink-0 animate-pulse" /> }
    : { bg: "bg-emerald-950/60 border-emerald-500/20", text: "text-emerald-200", icon: <Gift className="w-4 h-4 text-emerald-400 shrink-0" /> };

  const message = isExpired
    ? "Probezeit abgelaufen — Study bleibt verfügbar"
    : `Free Trial — ${daysLeft} Tag${daysLeft !== 1 ? "e" : ""} verbleibend`;

  return (
    <div className={`w-full border-b px-4 py-2 flex items-center justify-between gap-3 text-sm ${styles.bg}`}>
      <div className="flex items-center gap-2 min-w-0">
        {styles.icon}
        <span className={`${styles.text} font-medium truncate`}>{message}</span>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {(isUrgent || isExpired) && !requested && (
          <button
            onClick={requestExtension}
            disabled={requesting}
            className="text-xs px-2.5 py-1 rounded-lg border border-amber-500/40 text-amber-300 hover:bg-amber-500/10 transition-colors disabled:opacity-50 whitespace-nowrap flex items-center gap-1"
          >
            {requesting && <Loader2 className="w-3 h-3 animate-spin" />}
            Verlängerung anfragen
          </button>
        )}
        {requested && (
          <span className="text-xs text-emerald-400">✓ Anfrage gesendet</span>
        )}
        {isActive && !isUrgent && (
          <button onClick={() => setDismissed(true)} className="p-1 rounded hover:bg-white/5 transition-colors">
            <X className="w-3.5 h-3.5 text-emerald-400/60" />
          </button>
        )}
      </div>
    </div>
  );
}
