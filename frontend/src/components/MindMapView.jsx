import { useState } from "react";
import { ChevronRight } from "lucide-react";

export default function MindMapView({ data }) {
  if (!data) return null;

  return (
    <div>
      <h3 className="text-xl font-bold mb-4" style={{ color: '#c9a84c' }}>{data.title}</h3>
      <div className="space-y-2">
        {(data.children || []).map((branch, bi) => (
          <BranchItem key={bi} branch={branch} />
        ))}
      </div>
    </div>
  );
}

function BranchItem({ branch }) {
  const [open, setOpen] = useState(true);
  const color = branch.color || '#c9a84c';
  const kids = branch.children || [];

  return (
    <div className="ml-2 border-l-2 pl-4" style={{ borderColor: `${color}40` }}>
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 py-2 text-left w-full text-sm font-semibold hover:bg-white/5 rounded-lg">
        {kids.length > 0 && <ChevronRight className={`w-4 h-4 transition-transform ${open ? 'rotate-90' : ''}`} style={{ color }} />}
        {kids.length === 0 && <div className="w-2 h-2 rounded-full" style={{ background: color }} />}
        <span>{branch.title}</span>
      </button>
      {open && kids.length > 0 && (
        <div className="space-y-1">
          {kids.map((leaf, li) => (
            <LeafItem key={li} leaf={leaf} />
          ))}
        </div>
      )}
    </div>
  );
}

function LeafItem({ leaf }) {
  const [open, setOpen] = useState(false);
  const color = leaf.color || '#c9a84c';
  const kids = leaf.children || [];

  return (
    <div className="ml-6 pl-3 border-l border-white/5">
      <button onClick={() => kids.length > 0 && setOpen(!open)} className="flex items-center gap-2 py-1 text-left w-full text-sm hover:bg-white/5 rounded">
        <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
        <span className="text-muted-foreground">{leaf.title}</span>
      </button>
      {open && kids.length > 0 && (
        <div className="ml-4 space-y-0.5">
          {kids.map((sub, si) => (
            <div key={si} className="flex items-center gap-2 py-0.5 text-xs text-muted-foreground/70 pl-2">
              <div className="w-1 h-1 rounded-full bg-muted-foreground/30" />
              {sub.title}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
