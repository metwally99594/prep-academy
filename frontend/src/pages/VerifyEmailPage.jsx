import { useState, useEffect } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/App";
import { Button } from "@/components/ui/button";
import { CheckCircle, XCircle, Loader2, Mail } from "lucide-react";

export default function VerifyEmailPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token");
  const [status, setStatus] = useState("loading"); // loading | success | error
  const [errorMsg, setErrorMsg] = useState("");
  const [resending, setResending] = useState(false);
  const [resendEmail, setResendEmail] = useState("");
  const [resendDone, setResendDone] = useState(false);

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setErrorMsg("Kein Verifizierungstoken gefunden.");
      return;
    }
    axios.get(`${API}/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then(() => {
        setStatus("success");
        setTimeout(() => navigate("/login?verified=1"), 3500);
      })
      .catch(err => {
        setStatus("error");
        setErrorMsg(err.response?.data?.detail || "Verifizierung fehlgeschlagen.");
      });
  }, [token]); // eslint-disable-line

  const handleResend = async () => {
    if (!resendEmail.trim()) return;
    setResending(true);
    try {
      await axios.post(`${API}/auth/resend-verification`, { email: resendEmail });
      setResendDone(true);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || "Fehler beim Senden.");
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4"
      style={{ background: "linear-gradient(135deg,#080818 0%,#0c1229 50%,#080818 100%)" }}>
      <div className="w-full max-w-md text-center">
        <Link to="/" className="inline-block mb-8">
          <img src="/logo-elite.png" alt="PrepAcademy" className="w-20 h-20 object-contain mx-auto"
            style={{ filter: "drop-shadow(0 0 16px rgba(59,130,246,0.2))" }} />
        </Link>

        {status === "loading" && (
          <div className="rounded-2xl border border-white/10 p-10" style={{ background: "rgba(12,18,41,0.8)" }}>
            <Loader2 className="w-12 h-12 animate-spin text-amber-500 mx-auto mb-4" />
            <p className="text-white/60">E-Mail wird verifiziert…</p>
          </div>
        )}

        {status === "success" && (
          <div className="rounded-2xl border border-emerald-500/20 p-10" style={{ background: "rgba(12,18,41,0.8)" }}>
            <CheckCircle className="w-14 h-14 text-emerald-400 mx-auto mb-4" />
            <h1 className="text-xl font-bold text-white mb-2">E-Mail bestätigt!</h1>
            <p className="text-white/50 mb-6">Ihr Konto ist jetzt aktiv. Sie werden weitergeleitet…</p>
            <Link to="/login">
              <Button className="w-full h-11" style={{ background: "linear-gradient(135deg,#3b82f6,#60a5fa)", color: "#06081a" }}>
                Jetzt anmelden
              </Button>
            </Link>
          </div>
        )}

        {status === "error" && (
          <div className="rounded-2xl border border-red-500/20 p-10" style={{ background: "rgba(12,18,41,0.8)" }}>
            <XCircle className="w-14 h-14 text-red-400 mx-auto mb-4" />
            <h1 className="text-xl font-bold text-white mb-2">Verifizierung fehlgeschlagen</h1>
            <p className="text-white/50 mb-6">{errorMsg}</p>

            {!resendDone ? (
              <div className="space-y-3">
                <p className="text-sm text-white/40">Neuen Link anfordern:</p>
                <input
                  type="email"
                  placeholder="Ihre E-Mail-Adresse"
                  value={resendEmail}
                  onChange={e => setResendEmail(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-white/10 bg-white/5 text-white placeholder:text-white/25 text-sm focus:outline-none focus:border-amber-500/40"
                />
                <Button onClick={handleResend} disabled={resending || !resendEmail.trim()} className="w-full h-11"
                  style={{ background: "linear-gradient(135deg,#3b82f6,#60a5fa)", color: "#06081a" }}>
                  {resending ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Wird gesendet…</> : <><Mail className="w-4 h-4 mr-2" />Link erneut senden</>}
                </Button>
              </div>
            ) : (
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                <p className="text-emerald-400 text-sm">Link wurde gesendet. Bitte prüfen Sie Ihr Postfach.</p>
              </div>
            )}

            <Link to="/login" className="block mt-4 text-sm text-white/30 hover:text-white/60 transition-colors">
              Zurück zur Anmeldung
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
