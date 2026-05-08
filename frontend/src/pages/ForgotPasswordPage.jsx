import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Mail, Loader2, CheckCircle } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    try {
      await axios.post(`${API}/auth/forgot-password`, { email });
    } catch {
      // always show success — don't leak if email exists
    } finally {
      setLoading(false);
      setSent(true);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12"
      style={{ background: "linear-gradient(135deg,#080818 0%,#0c1229 50%,#080818 100%)" }}>
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-block mb-4">
            <img src="/logo-elite.png" alt="PrepAcademy" className="w-20 h-20 object-contain mx-auto"
              style={{ filter: "drop-shadow(0 0 16px rgba(201,168,76,0.2))" }} />
          </Link>
          <h1 className="text-2xl font-bold text-white mb-1">Passwort vergessen</h1>
          <p className="text-white/40 text-sm">Wir senden Ihnen einen Reset-Link</p>
        </div>

        <div className="rounded-2xl border border-white/10 p-8"
          style={{ background: "rgba(12,18,41,0.8)", backdropFilter: "blur(20px)" }}>
          {sent ? (
            <div className="text-center">
              <CheckCircle className="w-14 h-14 text-emerald-400 mx-auto mb-4" />
              <h2 className="text-lg font-semibold text-white mb-2">Link gesendet</h2>
              <p className="text-white/50 text-sm mb-6">
                Falls ein Konto mit dieser E-Mail existiert, haben wir Ihnen einen Reset-Link gesendet.
                Bitte prüfen Sie auch Ihren Spam-Ordner.
              </p>
              <Link to="/login">
                <Button variant="ghost" className="text-amber-500 hover:text-amber-400">
                  Zurück zur Anmeldung
                </Button>
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-white/80">E-Mail-Adresse</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="beispiel@email.com"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    className="pl-10 h-12 bg-white/5 border-white/10 text-white placeholder:text-white/25 focus:border-amber-500/40"
                    autoFocus
                  />
                </div>
              </div>

              <Button type="submit" disabled={loading || !email.trim()} className="w-full h-12 text-base font-semibold border-0"
                style={{ background: "linear-gradient(135deg,#c9a84c,#dbb85c)", color: "#06081a" }}>
                {loading ? <><Loader2 className="w-5 h-5 animate-spin mr-2" />Wird gesendet…</> : "Reset-Link anfordern"}
              </Button>

              <div className="text-center">
                <Link to="/login" className="text-sm text-white/30 hover:text-white/60 transition-colors">
                  Zurück zur Anmeldung
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
