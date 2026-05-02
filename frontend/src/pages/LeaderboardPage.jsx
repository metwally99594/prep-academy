import { useState, useEffect } from "react";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Trophy, Medal, Crown, TrendingUp, Target, Flame, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

const LEVEL_COLORS = {
  1: "from-gray-400 to-gray-500",
  2: "from-emerald-400 to-emerald-600",
  3: "from-blue-400 to-blue-600",
  4: "from-indigo-400 to-indigo-600",
  5: "from-purple-400 to-purple-600",
  6: "from-pink-400 to-pink-600",
  7: "from-rose-400 to-rose-600",
  8: "from-orange-400 to-orange-600",
  9: "from-amber-400 to-amber-600",
  10: "from-yellow-400 to-yellow-600",
};

export default function LeaderboardPage() {
  const { token, user } = useAuth();
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const res = await axios.get(`${API}/gamification/leaderboard`, { headers });
        setLeaderboard(res.data);
      } catch (error) {
        console.error("Failed to fetch leaderboard:", error);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchLeaderboard();
  }, [token]);

  const getRankIcon = (rank) => {
    if (rank === 1) return <Crown className="w-6 h-6 text-yellow-500" />;
    if (rank === 2) return <Medal className="w-6 h-6 text-gray-400" />;
    if (rank === 3) return <Medal className="w-6 h-6 text-amber-700" />;
    return <span className="text-lg font-bold text-muted-foreground w-6 text-center">#{rank}</span>;
  };

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="space-y-4">
          {[...Array(8)].map((_, i) => <div key={i} className="skeleton h-16 rounded-xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Link to="/dashboard" className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground mb-6 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Zurück zum Dashboard
      </Link>

      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-3 mb-4">
          <Trophy className="w-8 h-8 text-amber-500" />
          <h1 className="text-3xl font-bold" data-testid="leaderboard-title">Rangliste</h1>
        </div>
        <p className="text-muted-foreground">Top-Lernende nach XP-Punkten</p>
      </div>

      {/* Top 3 Podium */}
      {leaderboard.length >= 3 && (
        <div className="flex items-end justify-center gap-4 mb-8" data-testid="podium">
          {/* 2nd Place */}
          <div className="flex flex-col items-center w-28">
            <Medal className="w-8 h-8 text-gray-400 mb-2" />
            <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${LEVEL_COLORS[leaderboard[1]?.level?.level || 1]} flex items-center justify-center shadow-lg mb-2`}>
              <span className="text-xl font-bold text-white">{leaderboard[1]?.level?.level}</span>
            </div>
            <span className="text-sm font-semibold truncate w-full text-center">{leaderboard[1]?.name}</span>
            <span className="text-xs text-muted-foreground">{leaderboard[1]?.xp?.toLocaleString()} XP</span>
            <div className="w-full h-20 bg-gray-400/20 rounded-t-xl mt-2" />
          </div>
          
          {/* 1st Place */}
          <div className="flex flex-col items-center w-28">
            <Crown className="w-10 h-10 text-yellow-500 mb-2" />
            <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${LEVEL_COLORS[leaderboard[0]?.level?.level || 1]} flex items-center justify-center shadow-lg mb-2 ring-2 ring-yellow-400`}>
              <span className="text-2xl font-bold text-white">{leaderboard[0]?.level?.level}</span>
            </div>
            <span className="text-sm font-bold truncate w-full text-center">{leaderboard[0]?.name}</span>
            <span className="text-xs text-primary font-medium">{leaderboard[0]?.xp?.toLocaleString()} XP</span>
            <div className="w-full h-28 bg-yellow-400/20 rounded-t-xl mt-2" />
          </div>

          {/* 3rd Place */}
          <div className="flex flex-col items-center w-28">
            <Medal className="w-8 h-8 text-amber-700 mb-2" />
            <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${LEVEL_COLORS[leaderboard[2]?.level?.level || 1]} flex items-center justify-center shadow-lg mb-2`}>
              <span className="text-xl font-bold text-white">{leaderboard[2]?.level?.level}</span>
            </div>
            <span className="text-sm font-semibold truncate w-full text-center">{leaderboard[2]?.name}</span>
            <span className="text-xs text-muted-foreground">{leaderboard[2]?.xp?.toLocaleString()} XP</span>
            <div className="w-full h-14 bg-amber-600/20 rounded-t-xl mt-2" />
          </div>
        </div>
      )}

      {/* Full List */}
      <div className="space-y-2" data-testid="leaderboard-list">
        {leaderboard.map((entry) => {
          const isMe = entry.id === user?.id;
          return (
            <div
              key={entry.id}
              className={`flex items-center gap-4 p-4 rounded-xl transition-colors ${
                isMe ? 'bg-primary/10 border border-primary/30 ring-1 ring-primary/20' : 'glass-card hover:bg-muted/50'
              }`}
              data-testid={`leaderboard-entry-${entry.rank}`}
            >
              <div className="w-8 flex justify-center">{getRankIcon(entry.rank)}</div>
              
              <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${LEVEL_COLORS[entry.level?.level || 1]} flex items-center justify-center shadow`}>
                <span className="text-sm font-bold text-white">{entry.level?.level}</span>
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`font-semibold truncate ${isMe ? 'text-primary' : ''}`}>
                    {entry.name} {isMe && '(Du)'}
                  </span>
                  <span className="text-xs px-2 py-0.5 bg-muted rounded-full text-muted-foreground">
                    {entry.level?.name_de}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-0.5">
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Target className="w-3 h-3" /> {entry.accuracy}%
                  </span>
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" /> {entry.total_questions} Fragen
                  </span>
                </div>
              </div>

              <div className="text-right">
                <div className="font-bold text-primary">{entry.xp?.toLocaleString()}</div>
                <div className="text-xs text-muted-foreground">XP</div>
              </div>
            </div>
          );
        })}
      </div>

      {leaderboard.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <Trophy className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>Noch keine Einträge. Beantworte Fragen, um in der Rangliste zu erscheinen!</p>
        </div>
      )}
    </div>
  );
}
