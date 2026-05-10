import { useCallback } from "react";
import apiClient from "@/lib/api";

export function useReaction(_token) {
  const react = useCallback(async ({
    targetType,
    targetId,
    reaction,
    currentReaction,
    onOptimistic,
    onRollback,
    onCommit,
  }) => {
    const isSame = currentReaction === reaction;
    onOptimistic?.(isSame ? null : reaction);
    try {
      const res = await apiClient.post(
        "/community/reactions",
        { target_type: targetType, target_id: targetId, reaction },
        { timeout: 10000 },
      );
      onCommit?.(res.data.reaction ?? (isSame ? null : reaction), res.data.stats);
    } catch {
      onRollback?.(currentReaction);
    }
  }, []);

  return { react };
}
