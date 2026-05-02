import { useState, useEffect } from "react";
import axios from "axios";
import { API } from "@/App";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Tag, Plus, Trash2, Loader2, Palette } from "lucide-react";

const TAG_COLORS = [
  "#6366f1", "#8b5cf6", "#ec4899", "#ef4444", "#f97316",
  "#eab308", "#22c55e", "#14b8a6", "#06b6d4", "#3b82f6",
];

export default function AdminTagsTab({ token }) {
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState("#6366f1");
  const [creating, setCreating] = useState(false);

  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchTags();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchTags = async () => {
    try {
      const res = await axios.get(`${API}/tags`, { headers });
      setTags(res.data);
    } catch (e) {
      console.error("Failed to fetch tags:", e);
    } finally {
      setLoading(false);
    }
  };

  const createTag = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const res = await axios.post(`${API}/admin/tags`, { name: newName.trim(), color: newColor }, { headers });
      setTags(prev => [...prev, { ...res.data, created_at: new Date().toISOString() }]);
      setNewName("");
      toast.success("Tag erstellt");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Fehler");
    } finally {
      setCreating(false);
    }
  };

  const deleteTag = async (tagId) => {
    try {
      await axios.delete(`${API}/admin/tags/${tagId}`, { headers });
      setTags(prev => prev.filter(t => t.id !== tagId));
      toast.success("Tag gelöscht");
    } catch (e) {
      toast.error("Fehler beim Löschen");
    }
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>;

  return (
    <div className="glass-card rounded-2xl p-6" data-testid="admin-tags-tab">
      <h2 className="text-xl font-semibold flex items-center gap-2 mb-2">
        <Tag className="w-5 h-5" style={{ color: "#c4f441" }} />
        Tags verwalten ({tags.length})
      </h2>
      <p className="text-sm text-muted-foreground mb-6">
        Tags helfen beim Kategorisieren von Fragen. Erstellen Sie Tags hier, dann weisen Sie sie einzelnen Fragen zu 
        (Fragen → Bearbeiten → Tags auswählen). Studenten können dann im <strong>Eigene Auswahl</strong> nach Tags filtern.
      </p>

      {/* Create new tag */}
      <div className="flex items-center gap-3 mb-6 flex-wrap" data-testid="tag-create-form">
        <input
          type="text" value={newName} onChange={e => setNewName(e.target.value)}
          placeholder="Neuer Tag Name..."
          className="px-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary w-48"
          data-testid="tag-name-input"
          onKeyDown={e => e.key === "Enter" && createTag()}
        />
        <div className="flex items-center gap-1.5">
          <Palette className="w-4 h-4 text-muted-foreground" />
          {TAG_COLORS.map(c => (
            <button key={c} onClick={() => setNewColor(c)} data-testid={`tag-color-${c}`}
              className={`w-6 h-6 rounded-full border-2 transition-transform ${newColor === c ? "border-foreground scale-110" : "border-transparent"}`}
              style={{ background: c }} />
          ))}
        </div>
        <Button onClick={createTag} disabled={creating || !newName.trim()} className="gap-1" data-testid="tag-create-btn">
          {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          Erstellen
        </Button>
      </div>

      {/* Tags list */}
      {tags.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Tag className="w-10 h-10 mx-auto opacity-20 mb-3" />
          <p>Noch keine Tags erstellt</p>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2" data-testid="tags-list">
          {tags.map(tag => (
            <div key={tag.id} className="flex items-center gap-2 px-3 py-2 rounded-xl border bg-card group" data-testid={`tag-${tag.id}`}>
              <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: tag.color }} />
              <span className="text-sm font-medium">{tag.name}</span>
              <button onClick={() => deleteTag(tag.id)} className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500" data-testid={`delete-tag-${tag.id}`}>
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
