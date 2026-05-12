import { useState, useCallback, useMemo } from "react";
import axios from "axios";
import { API } from "@/App";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { CommentItem } from "./CommentItem";

function buildTree(comments) {
  const byId = {};
  const roots = [];

  for (const c of comments) {
    byId[c.id] = { ...c, replies: [] };
  }
  for (const c of Object.values(byId)) {
    if (c.parent_id && byId[c.parent_id]) {
      byId[c.parent_id].replies.push(c);
    } else {
      roots.push(c);
    }
  }

  roots.sort((a, b) => a.created_at.localeCompare(b.created_at));
  for (const c of Object.values(byId)) {
    c.replies.sort((a, b) => a.created_at.localeCompare(b.created_at));
  }

  return roots;
}

export function CommentSection({ postId, token, userId, userName, initialComments = [], commentCount = 0 }) {
  const [comments, setComments] = useState(initialComments);
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const headers = { Authorization: `Bearer ${token}` };

  const tree = useMemo(() => buildTree(comments), [comments]);

  const submitComment = useCallback(async (content, parentId = null) => {
    const optimisticId = `_opt_${Date.now()}`;
    const optimistic = {
      id: optimisticId,
      post_id: postId,
      parent_id: parentId || null,
      author_id: userId,
      author_name: userName || "Sie",
      content,
      status: "published",
      stats: {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      _optimistic: true,
    };
    setComments(prev => [...prev, optimistic]);

    try {
      const res = await axios.post(
        `${API}/community/comments`,
        { post_id: postId, content, ...(parentId ? { parent_id: parentId } : {}) },
        { headers, timeout: 12000 },
      );
      // Replace optimistic with real data (we have real ID + created_at now)
      setComments(prev =>
        prev.map(c =>
          c.id === optimisticId
            ? { ...optimistic, id: res.data.id, created_at: res.data.created_at, _optimistic: false }
            : c,
        ),
      );
    } catch (e) {
      setComments(prev => prev.filter(c => c.id !== optimisticId));
      toast.error(e.response?.data?.detail || "Kommentar konnte nicht gesendet werden. Bitte überprüfen Sie Ihre Verbindung.");
    }
  }, [postId, userId, userName, headers]);

  const handleSubmit = useCallback(async () => {
    if (!text.trim() || submitting) return;
    setSubmitting(true);
    try {
      await submitComment(text.trim());
      setText("");
    } finally {
      setSubmitting(false);
    }
  }, [text, submitting, submitComment]);

  const handleReply = useCallback(async (parentId, content) => {
    await submitComment(content, parentId);
  }, [submitComment]);

  const handleEditComment = useCallback(async (commentId, content) => {
    let original = null;
    setComments(prevComments => {
      const target = prevComments.find(c => c.id === commentId);
      original = target ? { ...target } : null;
      if (!target) return prevComments;
      return prevComments.map(c =>
        c.id === commentId ? { ...c, content, _optimistic: true } : c,
      );
    });
    if (!original) return;
    try {
      await axios.put(
        `${API}/community/comments/${commentId}`,
        { content },
        { headers, timeout: 12000 },
      );
      setComments(prevComments =>
        prevComments.map(c => c.id === commentId ? { ...c, _optimistic: false } : c),
      );
    } catch (e) {
      setComments(prevComments => {
        const stillExists = prevComments.some(c => c.id === commentId);
        if (!stillExists) return prevComments;
        return prevComments.map(c =>
          c.id === commentId ? { ...original, _optimistic: false } : c,
        );
      });
      toast.error(e.response?.data?.detail || "Kommentar konnte nicht bearbeitet werden.");
    }
  }, [headers]);

  const handleDeleteComment = useCallback(async (commentId) => {
    let removed = null;
    setComments(prevComments => {
      const target = prevComments.find(c => c.id === commentId);
      removed = target ? { ...target } : null;
      return prevComments.filter(c => c.id !== commentId);
    });
    if (!removed) return;
    try {
      await axios.delete(`${API}/community/comments/${commentId}`, { headers, timeout: 12000 });
    } catch (e) {
      setComments(prevComments => [...prevComments, { ...removed, _optimistic: false }]);
      toast.error(e.response?.data?.detail || "Kommentar konnte nicht gelöscht werden.");
    }
  }, [headers]);

  const realCount = comments.filter(c => !c._optimistic).length;
  const displayCount = realCount || commentCount;

  return (
    <div className="rounded-2xl border border-border/40 bg-card p-5">
      <h2 className="text-sm font-semibold mb-4">
        Kommentare {displayCount > 0 ? `(${displayCount})` : ""}
      </h2>

      {/* Comment tree */}
      <div className="space-y-4 mb-5 min-h-0">
        {tree.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            Noch keine Kommentare — schreiben Sie den ersten!
          </p>
        ) : (
          tree.map(comment => (
            <div key={comment.id} className="space-y-3">
              <CommentItem
                comment={comment}
                userId={userId}
                onSubmitReply={handleReply}
                onEditComment={handleEditComment}
                onDeleteComment={handleDeleteComment}
                depth={0}
              />
              {comment.replies.length > 0 && (
                <div className="space-y-3">
                  {comment.replies.map(reply => (
                    <CommentItem
                      key={reply.id}
                      comment={reply}
                      userId={userId}
                      onSubmitReply={handleReply}
                      onEditComment={handleEditComment}
                      onDeleteComment={handleDeleteComment}
                      depth={1}
                    />
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* New comment input */}
      <div
        className="flex gap-2 items-end border-t border-border/30 pt-4"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 0)" }}
      >
        <textarea
          className="flex-1 rounded-xl border bg-background/50 px-3 py-2.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary min-h-[44px] max-h-32"
          placeholder="Kommentar schreiben…"
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
            rows={1}
        />
        <Button
          size="icon"
          onClick={handleSubmit}
          disabled={submitting || !text.trim()}
          className="shrink-0 w-10 h-10"
          aria-label="Kommentar senden"
        >
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </Button>
      </div>
    </div>
  );
}
