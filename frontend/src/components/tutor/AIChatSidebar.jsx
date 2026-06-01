import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Plus, PanelLeftClose, Pin, PinOff, Pencil, Trash2, MessageSquare, Check } from "lucide-react";

export default function AIChatSidebar({
  conversations, conversationId, conversationsLoading,
  renamingId, renameValue,
  onSelect, onDelete, onRename, onPin, onNew, onToggle,
  onStartRename, onRenameValueChange, onRenameCancel,
}) {
  const pinned = conversations.filter(c => c.pinned);
  const history = conversations.filter(c => !c.pinned);

  return (
    <div className="w-64 flex-shrink-0 border-r flex flex-col" style={{ borderColor: 'rgba(59,130,246,0.1)', background: 'rgba(0,0,0,0.15)' }}>
      <div className="flex items-center justify-between px-3 py-3 border-b" style={{ borderColor: 'rgba(59,130,246,0.1)' }}>
        <span className="text-xs font-semibold text-white/50 uppercase tracking-wider">Konversationen</span>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="w-7 h-7" onClick={onNew} title="Neue Konversation">
            <Plus className="w-4 h-4 text-white/60" />
          </Button>
          <Button variant="ghost" size="icon" className="w-7 h-7" onClick={onToggle} title="Sidebar ausblenden">
            <PanelLeftClose className="w-4 h-4 text-white/40" />
          </Button>
        </div>
      </div>
      <ScrollArea className="flex-1 p-2">
        {conversationsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-white/30" />
          </div>
        ) : conversations.length === 0 ? (
          <p className="text-xs text-white/30 text-center py-8">Noch keine Konversationen</p>
        ) : (
          <div className="space-y-3">
            {pinned.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 px-2 py-1">
                  <Pin className="w-3 h-3 text-yellow-400" />
                  <span className="text-[10px] font-semibold text-yellow-400/70 uppercase tracking-wider">Angeheftet</span>
                </div>
                <div className="space-y-0.5">
                  {pinned.map(c => (
                    <div key={c.id}
                      className={`group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer text-sm transition-colors ${
                        conversationId === c.id ? 'bg-white/10' : 'hover:bg-white/5'
                      }`}
                      onClick={() => onSelect(c.id)}
                      style={conversationId === c.id ? { border: '1px solid rgba(59,130,246,0.2)' } : {}}
                    >
                      <Pin className="w-3 h-3 flex-shrink-0 text-yellow-400/60" />
                      {renamingId === c.id ? (
                        <div className="flex-1 flex items-center gap-1">
                          <input value={renameValue} onChange={e => onRenameValueChange(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter') onRename(c.id); if (e.key === 'Escape') onRenameCancel(); }}
                            className="flex-1 text-xs bg-white/10 border border-white/20 rounded px-1 py-0.5 text-white outline-none" autoFocus
                            onClick={e => e.stopPropagation()} />
                          <button onClick={e => { e.stopPropagation(); onRename(c.id); }} className="text-green-400 hover:text-green-300">
                            <Check className="w-3 h-3" />
                          </button>
                        </div>
                      ) : (
                        <>
                          <span className="flex-1 truncate text-white/70 group-hover:text-white/90">{c.title}</span>
                          <div className="hidden group-hover:flex items-center gap-0.5">
                            <button onClick={e => onPin(c.id, e)} className="p-0.5 text-yellow-400/50 hover:text-yellow-400" title="Loslösen">
                              <PinOff className="w-3 h-3" />
                            </button>
                            <button onClick={e => { e.stopPropagation(); onStartRename(c.id, c.title); }} className="p-0.5 text-white/30 hover:text-white/60">
                              <Pencil className="w-3 h-3" />
                            </button>
                            <button onClick={e => onDelete(c.id, e)} className="p-0.5 text-red-400/50 hover:text-red-400">
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {history.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 px-2 py-1">
                  <MessageSquare className="w-3 h-3 text-white/30" />
                  <span className="text-[10px] font-semibold text-white/30 uppercase tracking-wider">Verlauf</span>
                </div>
                <div className="space-y-0.5">
                  {history.map(c => (
                    <div key={c.id}
                      className={`group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer text-sm transition-colors ${
                        conversationId === c.id ? 'bg-white/10' : 'hover:bg-white/5'
                      }`}
                      onClick={() => onSelect(c.id)}
                      style={conversationId === c.id ? { border: '1px solid rgba(59,130,246,0.2)' } : {}}
                    >
                      <MessageSquare className="w-3.5 h-3.5 flex-shrink-0 text-white/30" />
                      {renamingId === c.id ? (
                        <div className="flex-1 flex items-center gap-1">
                          <input value={renameValue} onChange={e => onRenameValueChange(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter') onRename(c.id); if (e.key === 'Escape') onRenameCancel(); }}
                            className="flex-1 text-xs bg-white/10 border border-white/20 rounded px-1 py-0.5 text-white outline-none" autoFocus
                            onClick={e => e.stopPropagation()} />
                          <button onClick={e => { e.stopPropagation(); onRename(c.id); }} className="text-green-400 hover:text-green-300">
                            <Check className="w-3 h-3" />
                          </button>
                        </div>
                      ) : (
                        <>
                          <span className="flex-1 truncate text-white/70 group-hover:text-white/90">{c.title}</span>
                          <div className="hidden group-hover:flex items-center gap-0.5">
                            <button onClick={e => onPin(c.id, e)} className="p-0.5 text-white/30 hover:text-yellow-400" title="Anheften">
                              <Pin className="w-3 h-3" />
                            </button>
                            <button onClick={e => { e.stopPropagation(); onStartRename(c.id, c.title); }} className="p-0.5 text-white/30 hover:text-white/60">
                              <Pencil className="w-3 h-3" />
                            </button>
                            <button onClick={e => onDelete(c.id, e)} className="p-0.5 text-red-400/50 hover:text-red-400">
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
