import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

export function LoadingSpinner({ size = "md", className, label }) {
  const sizeClass = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8",
  }[size] || "w-6 h-6";

  return (
    <div className={cn("flex items-center justify-center gap-2", className)}>
      <Loader2 className={cn(sizeClass, "animate-spin text-muted-foreground/60")} />
      {label && (
        <span className="text-xs text-muted-foreground">{label}</span>
      )}
    </div>
  );
}
