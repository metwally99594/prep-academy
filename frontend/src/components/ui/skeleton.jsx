import { cn } from "@/lib/utils"

function Skeleton({
  className,
  ...props
}) {
  return (
    <div
      className={cn("animate-skeleton-pulse rounded-md bg-primary/8", className)}
      {...props} />
  );
}

export { Skeleton }
