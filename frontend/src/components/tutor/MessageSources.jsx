import { useState } from "react";
import { BookOpen, ChevronDown } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from "@/components/ui/collapsible";

export default function MessageSources({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-4 pt-3 rounded-lg space-y-2" style={{ background: 'rgba(255,255,255,0.02)' }}>
      <p className="text-[11px] font-semibold text-white/30 uppercase tracking-wider ml-3">Wissensdatenbank</p>
      {sources.slice(0, 3).map((w, i) => (
        <SourceCard key={i} source={w} />
      ))}
    </div>
  );
}

function SourceCard({ source: w }) {
  const [open, setOpen] = useState(false);

  return (
    <Card className="border-0" style={{ background: 'rgba(59,130,246,0.06)' }}>
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="w-full">
          <CardContent className="p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <BookOpen className="w-3.5 h-3.5 shrink-0" style={{ color: '#3b82f6' }} />
                <span className="font-medium text-xs text-white/80 truncate">{w.title}</span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-[10px] px-1.5 py-0.5 rounded-full whitespace-nowrap"
                  style={{ background: 'rgba(59,130,246,0.1)', color: '#60a5fa' }}>
                  {w.category}
                </span>
                <ChevronDown className={`w-3.5 h-3.5 text-white/40 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
              </div>
            </div>
          </CardContent>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="px-3 pb-3 pt-0">
            <p className="text-xs text-white/50 leading-relaxed italic line-clamp-4">
              &ldquo;{w.excerpt}&rdquo;
            </p>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
