import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { 
  FileText, Trash2, ArrowLeft, Search, Loader2, BookOpen,
} from "lucide-react";

export default function MyNotesPage() {
  const { token } = useAuth();
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    const fetchNotes = async () => {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const res = await axios.get(`${API}/notes/all`, { headers });
        setNotes(res.data);
      } catch (e) {
        console.error("Failed to fetch notes:", e);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchNotes();
  }, [token]);

  const deleteNote = async (questionId) => {
    setDeleting(questionId);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.delete(`${API}/notes/${questionId}`, { headers });
      setNotes(prev => prev.filter(n => n.question_id !== questionId));
      toast.success("Notiz gelöscht");
    } catch {
      toast.error("Fehler beim Löschen");
    } finally {
      setDeleting(null);
    }
  };

  const filtered = notes.filter(n => {
    if (!search) return true;
    const s = search.toLowerCase();
    return n.text.toLowerCase().includes(s) || n.question_text.toLowerCase().includes(s);
  });

  const formatDate = (iso) => {
    if (!iso) return "";
    return new Date(iso).toLocaleDateString("de-AT", { day: "2-digit", month: "short", year: "numeric" });
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <Link to="/dashboard">
          <Button variant="ghost" size="icon" className="rounded-full" data-testid="notes-back-btn">
            <ArrowLeft className="w-5 h-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold flex items-center gap-2" data-testid="notes-page-title">
            <FileText className="w-6 h-6" style={{ color: "#c4f441" }} />
            Meine Notizen
          </h1>
          <p className="text-muted-foreground text-sm mt-1">{notes.length} Notizen gespeichert</p>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Notizen durchsuchen..."
          className="w-full pl-10 pr-4 py-3 rounded-xl border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          data-testid="notes-search"
        />
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20">
          <BookOpen className="w-12 h-12 mx-auto text-muted-foreground/30 mb-4" />
          <p className="text-muted-foreground">
            {search ? "Keine Notizen gefunden." : "Noch keine Notizen. Fügen Sie Notizen beim Üben hinzu!"}
          </p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="notes-list">
          {filtered.map(note => (
            <div key={note.question_id} className="glass-card rounded-xl p-5 group" data-testid={`note-item-${note.question_id}`}>
              {/* Question preview */}
              <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                {note.question_text}
              </p>

              {/* Note text */}
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{note.text}</p>

              {/* Footer */}
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-border/50">
                <span className="text-xs text-muted-foreground">
                  {formatDate(note.updated_at)}
                  {note.specialty_id && (
                    <span className="ml-2 px-2 py-0.5 rounded-full bg-muted text-xs">{note.specialty_id}</span>
                  )}
                </span>
                <button
                  onClick={() => deleteNote(note.question_id)}
                  disabled={deleting === note.question_id}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500"
                  data-testid={`delete-note-${note.question_id}`}
                >
                  {deleting === note.question_id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
