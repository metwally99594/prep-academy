import { useEffect, useState, useContext } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { AuthContext, API } from "@/App";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Loader2, Check, Crown, Sparkles, Zap } from "lucide-react";

const ICONS = { premium_1m: Sparkles, premium_6m: Zap, premium_1y: Crown };
const HIGHLIGHT = "premium_6m";

export default function BillingPage() {
  const { token, user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [packages, setPackages] = useState([]);
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(null);

  useEffect(() => {
    if (!token) { navigate("/login"); return; }
    Promise.all([
      axios.get(`${API}/billing/packages`),
      axios.get(`${API}/billing/me`, { headers: { Authorization: `Bearer ${token}` } }),
    ]).then(([p, m]) => {
      setPackages(p.data.packages || []);
      setMe(m.data || null);
    }).catch(() => toast.error("Fehler beim Laden")).finally(() => setLoading(false));
  }, [token, navigate]);

  const checkout = async (pkgId) => {
    setRedirecting(pkgId);
    try {
      const res = await axios.post(`${API}/billing/checkout`,
        { package_id: pkgId, origin_url: window.location.origin },
        { headers: { Authorization: `Bearer ${token}` } });
      if (res.data.url) {
        window.location.href = res.data.url;
      } else {
        throw new Error("Keine Checkout-URL erhalten");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Checkout fehlgeschlagen");
      setRedirecting(null);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center min-h-[60vh]"><Loader2 className="w-8 h-8 animate-spin text-amber-500" /></div>;
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-12" data-testid="billing-page">
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-4">
          <Crown className="w-3.5 h-3.5" /> Premium Pläne
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold mb-3" style={{fontFamily: 'Playfair Display, serif'}}>
          Wählen Sie Ihren <span className="text-amber-500">Plan</span>
        </h1>
        <p className="text-muted-foreground max-w-2xl mx-auto text-base">
          Schalten Sie unbegrenzten Zugriff auf den Medical Analyzer, AI-Notizen und Audio-Podcasts frei.
        </p>
        {me?.is_active && (
          <div className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm">
            <Check className="w-4 h-4" /> Premium aktiv bis {new Date(me.premium_until).toLocaleDateString('de-DE')}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {packages.map((pkg) => {
          const Icon = ICONS[pkg.id] || Sparkles;
          const isHighlight = pkg.id === HIGHLIGHT;
          const monthlyEq = (pkg.amount / (pkg.duration_days / 30)).toFixed(2);
          return (
            <Card key={pkg.id} className={`relative p-6 flex flex-col gap-5 ${isHighlight ? 'border-amber-500 border-2 shadow-[0_0_40px_rgba(245,158,11,0.15)]' : 'border-border/40'}`} data-testid={`package-${pkg.id}`}>
              {isHighlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-amber-500 text-amber-950 text-xs font-bold uppercase tracking-wider">
                  Beliebt
                </div>
              )}
              <div className="flex items-center gap-3">
                <div className={`p-3 rounded-xl ${isHighlight ? 'bg-amber-500/20 text-amber-400' : 'bg-muted text-muted-foreground'}`}>
                  <Icon className="w-6 h-6" />
                </div>
                <div>
                  <div className="font-bold text-lg leading-tight">{pkg.label}</div>
                  <div className="text-xs text-muted-foreground">{pkg.duration_days} Tage Zugriff</div>
                </div>
              </div>

              <div>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-4xl font-black tracking-tight">€{pkg.amount}</span>
                  <span className="text-sm text-muted-foreground">einmalig</span>
                </div>
                <div className="text-xs text-muted-foreground mt-1">≈ €{monthlyEq} / Monat</div>
              </div>

              <ul className="flex flex-col gap-2.5 flex-1">
                {pkg.features.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <Check className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isHighlight ? 'text-amber-500' : 'text-emerald-500'}`} />
                    <span className="text-foreground/90">{f}</span>
                  </li>
                ))}
              </ul>

              <Button
                onClick={() => checkout(pkg.id)}
                disabled={redirecting === pkg.id}
                className={`w-full h-11 ${isHighlight ? 'bg-amber-500 hover:bg-amber-600 text-amber-950' : ''}`}
                variant={isHighlight ? 'default' : 'outline'}
                data-testid={`checkout-${pkg.id}-btn`}
              >
                {redirecting === pkg.id ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Jetzt aktivieren'}
              </Button>
            </Card>
          );
        })}
      </div>

      <div className="mt-12 text-center text-xs text-muted-foreground space-y-2">
        <p>🔒 Sichere Zahlung über Stripe · Karten, Apple Pay, Google Pay</p>
        <p>Keine automatische Verlängerung — einmalige Zahlung, klare Laufzeit.</p>
      </div>
    </div>
  );
}
