import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import axios from "axios";
import { useAuth, API } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Eye, EyeOff, Mail, Lock, Loader2, CheckCircle } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [unverified, setUnverified] = useState(false);
  const [resending, setResending] = useState(false);
  const [resendDone, setResendDone] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const justVerified = params.get("verified") === "1";

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Bitte geben Sie E-Mail und Passwort ein");
      return;
    }
    setUnverified(false);
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Erfolgreich angemeldet");
      navigate("/");
    } catch (error) {
      console.error("LOGIN_FAILED", {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
        code: error.code,
      });
      const detail = error.response?.data?.detail || "";
      if (detail === "email_not_verified") {
        setUnverified(true);
      } else {
        toast.error(detail || "Anmeldung fehlgeschlagen");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    try {
      await axios.post(`${API}/auth/resend-verification`, { email });
      setResendDone(true);
    } catch {
      setResendDone(true); // always show success
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12" style={{ background: "linear-gradient(135deg, #080818 0%, #0c1229 50%, #080818 100%)", paddingBottom: "max(3rem, env(safe-area-inset-bottom))" }}>
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-3 mb-6">
            <img src="/logo-elite.png" alt="Prep Academy" className="w-28 h-28 object-contain" style={{ filter: "drop-shadow(0 0 20px rgba(201,168,76,0.2))" }} />
          </Link>
          <h1 className="text-2xl font-bold mb-2 text-white" data-testid="login-title">Anmelden</h1>
          <p className="text-white/50">Melden Sie sich an, um auf Ihr Konto zuzugreifen</p>
        </div>

        {justVerified && (
          <div className="mb-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            <p className="text-sm text-emerald-300">E-Mail bestätigt! Sie können sich jetzt anmelden.</p>
          </div>
        )}

        {unverified && (
          <div className="mb-4 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 space-y-2">
            <p className="text-sm text-amber-300">Bitte bestätigen Sie zuerst Ihre E-Mail-Adresse.</p>
            {!resendDone ? (
              <button onClick={handleResend} disabled={resending}
                className="text-xs text-amber-400 hover:text-amber-300 underline disabled:opacity-50">
                {resending ? "Wird gesendet…" : "Bestätigungslink erneut senden"}
              </button>
            ) : (
              <p className="text-xs text-emerald-400">Link gesendet — bitte prüfen Sie Ihr Postfach.</p>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit} className="rounded-2xl p-8 space-y-5 border border-[#c9a84c]/10" style={{ background: 'rgba(12, 18, 41, 0.8)', backdropFilter: 'blur(20px)' }}>
          <div className="space-y-2">
            <Label htmlFor="email" className="text-white/80">E-Mail</Label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30" />
              <Input id="email" type="email" placeholder="beispiel@email.com" value={email}
                onChange={e => setEmail(e.target.value)}
                className="pl-10 h-12 bg-white/5 border-white/10 text-white placeholder:text-white/25 focus:border-[#c9a84c]/40"
                data-testid="login-email-input" />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="text-white/80">Passwort</Label>
              <Link to="/forgot-password" className="text-xs text-white/35 hover:text-amber-400 transition-colors">
                Passwort vergessen?
              </Link>
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30" />
              <Input id="password" type={showPassword ? "text" : "password"} placeholder="••••••••" value={password}
                onChange={e => setPassword(e.target.value)}
                className="pl-10 pr-10 h-12 bg-white/5 border-white/10 text-white placeholder:text-white/25 focus:border-[#c9a84c]/40"
                data-testid="login-password-input" />
              <button type="button" onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors"
                data-testid="toggle-password-visibility">
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          <Button type="submit"
            className="w-full h-12 text-base font-semibold text-[#0a0a1a] border-0 bg-gradient-to-r from-[#c9a84c] to-[#dbb85c] hover:shadow-[0_4px_20px_rgba(201,168,76,0.3)] transition-all"
            disabled={loading} data-testid="login-submit-btn">
            {loading ? <><Loader2 className="w-5 h-5 animate-spin mr-2" />Anmeldung läuft…</> : "Anmelden"}
          </Button>

          <div className="text-center text-sm">
            <span className="text-white/40">Noch kein Konto? </span>
            <Link to="/register" className="text-[#c9a84c] hover:underline" data-testid="register-link">Registrieren</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
