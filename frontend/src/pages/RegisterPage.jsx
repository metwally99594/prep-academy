import { useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Eye, EyeOff, Mail, Lock, User, Loader2, MailCheck, Shield, ShieldAlert, ShieldCheck } from "lucide-react";

function PasswordStrength({ password }) {
  const strength = useMemo(() => {
    let score = 0;
    if (password.length >= 6) score++;
    if (password.length >= 10) score++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
    if (/\d/.test(password)) score++;
    if (/[^a-zA-Z0-9]/.test(password)) score++;
    return score;
  }, [password]);
  if (!password) return null;
  const bars = [
    { fill: strength >= 1 ? "bg-red-500" : "bg-muted", label: "Schwach" },
    { fill: strength >= 2 ? "bg-orange-400" : "bg-muted", label: "Mittel" },
    { fill: strength >= 3 ? "bg-yellow-400" : "bg-muted", label: "Gut" },
    { fill: strength >= 4 ? "bg-emerald-400" : "bg-muted", label: "Stark" },
    { fill: strength >= 5 ? "bg-emerald-500" : "bg-muted", label: "Sehr stark" },
  ];
  return (
    <div className="mt-2 space-y-1">
      <div className="flex gap-1">
        {bars.map((b, i) => (
          <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${b.fill}`} />
        ))}
      </div>
      <p className={`text-[10px] ${
        strength <= 1 ? "text-red-400" : strength <= 2 ? "text-orange-400" : strength <= 3 ? "text-yellow-400" : "text-emerald-400"
      }`}>
        {strength <= 1 ? <ShieldAlert className="w-3 h-3 inline mr-1" /> : strength >= 4 ? <ShieldCheck className="w-3 h-3 inline mr-1" /> : <Shield className="w-3 h-3 inline mr-1" />}
        {bars[Math.min(strength, bars.length - 1)]?.label || ""}
      </p>
    </div>
  );
}

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [doneEmail, setDoneEmail] = useState("");
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || !email || !password) { toast.error("Bitte füllen Sie alle Felder aus"); return; }
    if (password !== confirmPassword) { toast.error("Passwörter stimmen nicht überein"); return; }
    if (password.length < 6) { toast.error("Passwort muss mindestens 6 Zeichen haben"); return; }

    setLoading(true);
    try {
      const data = await register(email, password, name);
      if (data && data.token) {
        toast.success("Konto erstellt");
        navigate("/");
      } else {
        setDoneEmail(data?.email || email);
        setDone(true);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Registrierung fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  };

  if (done) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4"
        style={{ background: "linear-gradient(135deg,#080818 0%,#0c1229 50%,#080818 100%)" }}>
        <div className="w-full max-w-md text-center">
          <div className="rounded-2xl border border-amber-500/20 p-10" style={{ background: "rgba(12,18,41,0.8)" }}>
            <MailCheck className="w-14 h-14 text-amber-400 mx-auto mb-4" />
            <h1 className="text-xl font-bold text-white mb-2">E-Mail bestätigen</h1>
            <p className="text-white/50 text-sm mb-2">
              Wir haben einen Bestätigungslink an
            </p>
            <p className="text-amber-400 font-medium mb-4">{doneEmail}</p>
            <p className="text-white/40 text-sm mb-6">
              Bitte prüfen Sie Ihr Postfach und klicken Sie auf den Link, um Ihr Konto zu aktivieren.
            </p>
            <Link to="/login">
              <Button variant="ghost" className="text-amber-400 hover:text-amber-300">Zur Anmeldung</Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12"
      style={{ background: "linear-gradient(135deg,#080818 0%,#0c1229 50%,#080818 100%)", paddingBottom: "max(3rem, env(safe-area-inset-bottom))" }}>
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-block mb-4">
            <img src="/logo-elite.png" alt="PrepAcademy" className="w-20 h-20 object-contain mx-auto"
              style={{ filter: "drop-shadow(0 0 16px rgba(201,168,76,0.2))" }} />
          </Link>
          <h1 className="text-2xl font-bold mb-2 text-white" data-testid="register-title">Konto erstellen</h1>
          <p className="text-white/50">Registrieren Sie sich und beginnen Sie zu lernen</p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-2xl border border-[#c9a84c]/10 p-8 space-y-5"
          style={{ background: "rgba(12,18,41,0.8)", backdropFilter: "blur(20px)" }}>
          <div className="space-y-2">
            <Label htmlFor="name">Vollständiger Name</Label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <Input
                id="name"
                type="text"
                placeholder="Max Mustermann"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="pl-10 h-12"
                data-testid="register-name-input"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">E-Mail</Label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <Input
                id="email"
                type="email"
                placeholder="beispiel@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="pl-10 h-12"
                data-testid="register-email-input"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Passwort</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="pl-10 pr-10 h-12"
                data-testid="register-password-input"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            <PasswordStrength password={password} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Passwort bestätigen</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <Input
                id="confirmPassword"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={`pl-10 h-12 ${confirmPassword && password !== confirmPassword ? "border-destructive" : ""}`}
                data-testid="register-confirm-password-input"
              />
            </div>
            {confirmPassword && password !== confirmPassword && (
              <p className="text-[10px] text-destructive mt-1">Passwörter stimmen nicht überein</p>
            )}
          </div>

          <Button type="submit" disabled={loading} data-testid="register-submit-btn"
            className="w-full h-12 text-base font-semibold border-0"
            style={{ background: "linear-gradient(135deg,#c9a84c,#dbb85c)", color: "#06081a" }}>
            {loading ? <><Loader2 className="w-5 h-5 animate-spin mr-2" />Konto wird erstellt…</> : "Registrieren"}
          </Button>

          <div className="text-center text-sm">
            <span className="text-white/40">Bereits ein Konto? </span>
            <Link to="/login" className="text-amber-400 hover:underline" data-testid="login-link">
              Anmelden
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
