import { Inbox } from "lucide-react";

export function EmptyState({ icon: Icon = Inbox, title, description, action }) {
  return (
    <div className="text-center py-16">
      <div className="flex justify-center mb-4">
        <div className="w-12 h-12 rounded-xl bg-muted/50 flex items-center justify-center">
          <Icon className="w-6 h-6 text-muted-foreground/40" />
        </div>
      </div>
      <p className="text-sm font-medium text-foreground/80 mb-1">{title}</p>
      {description && (
        <p className="text-xs text-muted-foreground/60 mb-4 max-w-xs mx-auto">{description}</p>
      )}
      {action && action}
    </div>
  );
}
