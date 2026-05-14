import { useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Lock, Eye, EyeOff, Loader2 } from "lucide-react";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token");

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password.length < 6) { toast.error("Mindestens 6 Zeichen"); return; }
    if (password !== confirm) { toast.error("Passwörter stimmen nicht überein"); return; }
    if (!token) { toast.error("Kein Reset-Token gefunden"); return; }

    setLoading(true);
    try {
      await axios.post(`${API}/auth/reset-password`, { token, new_password: password });
      toast.success("Passwort erfolgreich geändert");
      setTimeout(() => navigate("/login"), 1200);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Zurücksetzen");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center"
        style={{ background: "linear-gradient(135deg,#080818,#0c1229)" }}>
        <div className="text-center text-white/50">
          <p className="mb-4">Kein gültiger Reset-Link.</p>
          <Link to="/forgot-password" className="text-amber-500 hover:underline">Neuen Link anfordern</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12"
      style={{ background: "linear-gradient(135deg,#080818 0%,#0c1229 50%,#080818 100%)" }}>
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-block mb-4">
            <img src="/logo-elite.png" alt="PrepAcademy" className="w-20 h-20 object-contain mx-auto"
              style={{ filter: "drop-shadow(0 0 16px rgba(59,130,246,0.2))" }} />
          </Link>
          <h1 className="text-2xl font-bold text-white mb-1">Neues Passwort</h1>
          <p className="text-white/40 text-sm">Geben Sie Ihr neues Passwort ein</p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-2xl border border-white/10 p-8 space-y-5"
          style={{ background: "rgba(12,18,41,0.8)", backdropFilter: "blur(20px)" }}>
          <div className="space-y-2">
            <Label htmlFor="password" className="text-white/80">Neues Passwort</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30" />
              <Input
                id="password"
                type={showPw ? "text" : "password"}
                placeholder="Neues Passwort"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="pl-10 pr-10 h-12 bg-white/5 border-white/10 text-white placeholder:text-white/25 focus:border-amber-500/40"
                autoFocus
              />
              <button type="button" onClick={() => setShowPw(p => !p)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors">
                {showPw ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm" className="text-white/80">Passwort bestätigen</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30" />
              <Input
                id="confirm"
                type={showPw ? "text" : "password"}
                placeholder="Passwort wiederholen"
                value={confirm}
                onChange={e => setConfirm(e.target.value)}
                className="pl-10 h-12 bg-white/5 border-white/10 text-white placeholder:text-white/25 focus:border-amber-500/40"
              />
            </div>
          </div>

          <Button type="submit" disabled={loading || !password || !confirm} className="w-full h-12 text-base font-semibold border-0"
            style={{ background: "linear-gradient(135deg,#3b82f6,#60a5fa)", color: "#06081a" }}>
            {loading ? <><Loader2 className="w-5 h-5 animate-spin mr-2" />Wird gespeichert…</> : "Passwort ändern"}
          </Button>

          <div className="text-center">
            <Link to="/login" className="text-sm text-white/30 hover:text-white/60 transition-colors">
              Zurück zur Anmeldung
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
