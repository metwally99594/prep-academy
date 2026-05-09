import { useCallback } from "react";
import axios from "axios";
import { API } from "@/App";

export function useReaction(token) {
  const headers = { Authorization: `Bearer ${token}` };

  const react = useCallback(async ({
    targetType,
    targetId,
    reaction,
    currentReaction,
    onOptimistic,
    onRollback,
    onCommit,
  }) => {
    // If clicking the same reaction again → toggle off (send same reaction = toggle on backend)
    const isSame = currentReaction === reaction;

    // Optimistic stats patch
    onOptimistic?.(isSame ? null : reaction);

    try {
      const res = await axios.post(
        `${API}/community/reactions`,
        { target_type: targetType, target_id: targetId, reaction },
        { headers, timeout: 10000 },
      );
      onCommit?.(res.data.reaction ?? (isSame ? null : reaction), res.data.stats);
    } catch {
      onRollback?.(currentReaction);
    }
  }, [token]);

  return { react };
}
