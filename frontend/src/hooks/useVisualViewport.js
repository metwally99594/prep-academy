import { useState, useEffect } from "react";

export function useVisualViewport() {
  const [height, setHeight] = useState(
    typeof window !== "undefined" ? window.innerHeight : 0,
  );

  useEffect(() => {
    if (typeof window === "undefined" || !("visualViewport" in window)) return;

    const handler = () => {
      setHeight(window.visualViewport.height);
    };

    window.visualViewport.addEventListener("resize", handler);
    window.visualViewport.addEventListener("scroll", handler);
    handler();

    return () => {
      window.visualViewport.removeEventListener("resize", handler);
      window.visualViewport.removeEventListener("scroll", handler);
    };
  }, []);

  return height;
}
