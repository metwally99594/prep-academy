import { useState, useCallback, useEffect } from "react";
import apiClient from "@/lib/api";

export function usePost(token, postId) {
  const [post, setPost] = useState(null);
  const [comments, setComments] = useState([]);
  const [userReaction, setUserReaction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!token || !postId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(
        `/community/posts/${postId}`,
        { timeout: 12000 },
      );
      setPost(res.data.post);
      setComments(res.data.comments || []);
      setUserReaction(res.data.user_reaction || null);
    } catch (e) {
      setError(e.response?.data?.detail || "Fehler beim Laden");
    } finally {
      setLoading(false);
    }
  }, [token, postId]);

  useEffect(() => {
    setPost(null);
    setComments([]);
    setUserReaction(null);
    load();
  }, [load]);

  const addComment = useCallback(async (content, parentId = null) => {
    const res = await apiClient.post(
      "/community/comments",
      { post_id: postId, content, parent_id: parentId || undefined },
      { timeout: 12000 },
    );
    await load();
    return res.data;
  }, [token, postId, load]);

  const applyReaction = useCallback((reaction, stats) => {
    setUserReaction(reaction);
    if (stats) setPost(prev => prev ? { ...prev, stats } : prev);
  }, []);

  return { post, comments, userReaction, loading, error, load, addComment, applyReaction };
}
