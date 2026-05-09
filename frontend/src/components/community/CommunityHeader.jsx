import { Users, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

export function CommunityHeader({ onNewPost, user }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
          <Users className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-lg font-bold leading-tight">Community</h1>
          <p className="text-xs text-muted-foreground">Medizinische Diskussionen</p>
        </div>
      </div>
      {user && (
        <Button size="sm" className="gap-1.5 shrink-0" onClick={onNewPost}>
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">Beitrag erstellen</span>
          <span className="sm:hidden">Neu</span>
        </Button>
      )}
    </div>
  );
}
