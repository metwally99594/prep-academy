import { useEffect, useState, useContext } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { AuthContext, API } from "@/App";
import { Loader2, CheckCircle2, XCircle, Crown } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function BillingSuccessPage() {
  const { token } = useContext(AuthContext);
  const navigate = useNavigate();
  const [status, setStatus] = useState("checking"); // checking | paid | failed | expired
  const [details, setDetails] = useState(null);

  useEffect(() => {
    if (!token) { navigate("/login"); return; }
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get("session_id");
    if (!sessionId) { setStatus("failed"); return; }

    let attempts = 0;
    const maxAttempts = 8;
    const poll = async () => {
      try {
        const res = await axios.get(`${API}/billing/status/${sessionId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setDetails(res.data);
        if (res.data.payment_status === "paid") { setStatus("paid"); return; }
        if (res.data.status === "expired") { setStatus("expired"); return; }
        attempts++;
        if (attempts >= maxAttempts) { setStatus("failed"); return; }
        setTimeout(poll, 2500);
      } catch {
        attempts++;
        if (attempts >= maxAttempts) { setStatus("failed"); return; }
        setTimeout(poll, 2500);
      }
    };
    poll();
  }, [token, navigate]);

  return (
    <div className="max-w-md mx-auto px-4 py-20 text-center" data-testid="billing-success-page">
      {status === "checking" && (
        <>
          <Loader2 className="w-16 h-16 animate-spin text-amber-500 mx-auto mb-6" />
          <h1 className="text-2xl font-bold mb-2">Zahlung wird überprüft...</h1>
          <p className="text-muted-foreground">Bitte warten Sie einen Moment.</p>
        </>
      )}
      {status === "paid" && (
        <>
          <div className="inline-flex p-4 rounded-full bg-emerald-500/10 border-2 border-emerald-500 mb-6">
            <CheckCircle2 className="w-16 h-16 text-emerald-500" />
          </div>
          <h1 className="text-3xl font-bold mb-3" style={{fontFamily: 'Playfair Display, serif'}}>
            <Crown className="w-8 h-8 inline-block text-amber-500 mr-2" />
            Premium aktiviert!
          </h1>
          <p className="text-muted-foreground mb-2">
            {details && `€${details.amount} ${details.currency?.toUpperCase()} erfolgreich gezahlt.`}
          </p>
          <p className="text-sm text-muted-foreground mb-8">
            Sie haben jetzt unbegrenzten Zugriff auf alle Premium-Features.
          </p>
          <div className="flex gap-3 justify-center">
            <Button asChild className="bg-amber-500 hover:bg-amber-600 text-amber-950" data-testid="goto-analyzer">
              <Link to="/analyzer">Medical Analyzer öffnen</Link>
            </Button>
            <Button asChild variant="outline" data-testid="goto-dashboard">
              <Link to="/dashboard">Zum Dashboard</Link>
            </Button>
          </div>
        </>
      )}
      {(status === "failed" || status === "expired") && (
        <>
          <div className="inline-flex p-4 rounded-full bg-red-500/10 border-2 border-red-500 mb-6">
            <XCircle className="w-16 h-16 text-red-500" />
          </div>
          <h1 className="text-2xl font-bold mb-3">Zahlung nicht abgeschlossen</h1>
          <p className="text-muted-foreground mb-8">
            {status === "expired" ? "Die Sitzung ist abgelaufen." : "Wir konnten den Zahlungsstatus nicht bestätigen."}
          </p>
          <Button asChild data-testid="retry-billing">
            <Link to="/billing">Erneut versuchen</Link>
          </Button>
        </>
      )}
    </div>
  );
}
