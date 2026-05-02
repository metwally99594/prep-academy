import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { 
  BarChart3, 
  ArrowLeft,
  Target,
  Trophy,
  TrendingUp,
  CheckCircle2,
  XCircle,
  Loader2
} from "lucide-react";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from "recharts";

const SPECIALTY_NAMES = {
  surgery: "Chirurgie",
  internal: "Innere Medizin",
  pediatrics: "Pädiatrie",
  emergency: "Notfallmedizin",
  ophthalmology: "Ophthalmologie",
  dermatology: "Dermatologie",
  ent: "HNO",
  obgyn: "Gynäkologie",
  neurology: "Neurologie",
  special: "Special",
};

export default function StatsPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const { token } = useAuth();

  useEffect(() => {
    fetchStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const fetchStats = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.get(`${API}/stats`, { headers });
      setStats(response.data);
    } catch (error) {
      console.error("Failed to fetch stats:", error);
      toast.error("Fehler beim Laden der Statistik");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const pieData = [
    { name: "Richtig", value: stats?.correct_answers || 0 },
    { name: "Falsch", value: stats?.wrong_answers || 0 },
  ];

  const specialtyData = Object.entries(stats?.by_specialty || {}).map(([key, value]) => ({
    name: SPECIALTY_NAMES[key] || key,
    total: value.total || 0,
    correct: value.correct || 0,
    accuracy: value.total > 0 ? Math.round((value.correct / value.total) * 100) : 0
  }));

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-primary/10">
            <BarChart3 className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="stats-title">Statistik</h1>
            <p className="text-muted-foreground">Verfolgen Sie Ihren Lernfortschritt</p>
          </div>
        </div>
        <Link to="/">
          <Button variant="ghost" className="gap-2">
            <ArrowLeft className="w-4 h-4" />
            Zurück
          </Button>
        </Link>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="glass-card rounded-xl p-6" data-testid="stat-total">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Target className="w-5 h-5 text-primary" />
            </div>
          </div>
          <div className="text-3xl font-bold mb-1">{stats?.total_questions || 0}</div>
          <div className="text-sm text-muted-foreground">Fragen gesamt</div>
        </div>

        <div className="glass-card rounded-xl p-6" data-testid="stat-correct">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-lg bg-emerald-500/10">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
            </div>
          </div>
          <div className="text-3xl font-bold mb-1 text-emerald-500">{stats?.correct_answers || 0}</div>
          <div className="text-sm text-muted-foreground">Richtig</div>
        </div>

        <div className="glass-card rounded-xl p-6" data-testid="stat-wrong">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-lg bg-red-500/10">
              <XCircle className="w-5 h-5 text-red-500" />
            </div>
          </div>
          <div className="text-3xl font-bold mb-1 text-red-500">{stats?.wrong_answers || 0}</div>
          <div className="text-sm text-muted-foreground">Falsch</div>
        </div>

        <div className="glass-card rounded-xl p-6" data-testid="stat-accuracy">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-lg bg-amber-500/10">
              <Trophy className="w-5 h-5 text-amber-500" />
            </div>
          </div>
          <div className="text-3xl font-bold mb-1 text-amber-500">{stats?.accuracy_percentage || 0}%</div>
          <div className="text-sm text-muted-foreground">Erfolgsquote</div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-6 mb-8">
        {/* Pie Chart */}
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary" />
            Antwortverteilung
          </h3>
          {stats?.total_questions > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    <Cell fill="hsl(160, 84%, 39%)" />
                    <Cell fill="hsl(350, 89%, 60%)" />
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      background: "hsl(222, 47%, 8%)",
                      border: "1px solid hsl(217, 33%, 25%)",
                      borderRadius: "8px"
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-muted-foreground">
              Noch keine Daten vorhanden
            </div>
          )}
        </div>

        {/* Bar Chart - By Specialty */}
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            Leistung nach Fachgebiet
          </h3>
          {specialtyData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={specialtyData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(217, 33%, 25%)" />
                  <XAxis type="number" stroke="hsl(215, 20%, 65%)" />
                  <YAxis dataKey="name" type="category" width={100} stroke="hsl(215, 20%, 65%)" fontSize={12} />
                  <Tooltip 
                    contentStyle={{ 
                      background: "hsl(222, 47%, 8%)",
                      border: "1px solid hsl(217, 33%, 25%)",
                      borderRadius: "8px"
                    }}
                    formatter={(value, name) => [value, name === "correct" ? "Richtig" : "Gesamt"]}
                  />
                  <Bar dataKey="total" fill="hsl(217, 33%, 25%)" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="correct" fill="hsl(160, 84%, 39%)" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-muted-foreground">
              Noch keine Daten vorhanden
            </div>
          )}
        </div>
      </div>

      {/* Specialty Progress */}
      {specialtyData.length > 0 && (
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold mb-6">Detaillierter Fortschritt</h3>
          <div className="space-y-6">
            {specialtyData.map((spec, index) => (
              <div key={spec.name} data-testid={`specialty-progress-${index}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{spec.name}</span>
                  <span className="text-sm text-muted-foreground">
                    {spec.correct}/{spec.total} ({spec.accuracy}%)
                  </span>
                </div>
                <Progress value={spec.accuracy} className="h-2" />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
