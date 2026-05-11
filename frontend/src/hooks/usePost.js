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

  const updatePost = useCallback(async (data) => {
    const prev = post;
    if (!prev) return;
    setPost(prevPost => prevPost ? { ...prevPost, ...data, _optimistic: true } : prevPost);
    try {
      await apiClient.put(`/community/posts/${postId}`, data, { timeout: 12000 });
      setPost(prevPost => prevPost ? { ...prevPost, _optimistic: false } : prevPost);
    } catch (e) {
      setPost(prevPost => {
        if (!prevPost) return prevPost;
        return { ...prev, _optimistic: false };
      });
      throw new Error(e.response?.data?.detail || "Fehler beim Bearbeiten");
    }
  }, [post, postId]);

  const deletePost = useCallback(async () => {
    if (!post) return;
    try {
      await apiClient.delete(`/community/posts/${postId}`, { timeout: 12000 });
    } catch (e) {
      throw new Error(e.response?.data?.detail || "Fehler beim Löschen");
    }
  }, [post, postId]);

  return { post, comments, userReaction, loading, error, load, addComment, applyReaction, updatePost, deletePost };
}
