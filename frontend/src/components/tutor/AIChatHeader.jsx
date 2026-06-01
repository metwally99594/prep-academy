import { Button } from "@/components/ui/button";
import { MODELS, LANGUAGES, FLAG_EMOJI } from "@/hooks/useAIChat";
import {
  Sparkles, ChevronDown, Globe, Database, BookOpen,
  PanelLeft, PlusCircle, X, Bot,
} from "lucide-react";

export default function AIChatHeader({
  isTutor, currentModel, currentLang,
  selectedModel, selectedLang, selectedSpecialty, selectedChapter,
  chapters, specialties,
  showModelPicker, showLangPicker, showSpecialtyPicker, showChapterPicker,
  sidebarOpen, conversationId,
  onModelSelect, onLangSelect, onSpecialtySelect, onChapterSelect,
  onToggleSidebar, onNewConversation, onClose,
  onModelPickerToggle, onLangPickerToggle, onSpecialtyPickerToggle, onChapterPickerToggle,
}) {
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'rgba(59,130,246,0.1)', background: 'rgba(59, 130, 246, 0.03)' }}>
      <div className="flex items-center gap-3">
        {isTutor && !sidebarOpen && (
          <Button variant="ghost" size="icon" className="w-7 h-7" onClick={onToggleSidebar} title="Sidebar einblenden">
            <PanelLeft className="w-4 h-4 text-white/40" />
          </Button>
        )}
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: isTutor ? 'rgba(245,158,11,0.12)' : 'rgba(59,130,246,0.1)' }}>
          {isTutor ? <BookOpen className="w-5 h-5" style={{ color: '#f59e0b' }} /> : <Sparkles className="w-5 h-5" style={{ color: '#3b82f6' }} />}
        </div>
        <div>
          <h3 className="font-semibold text-white text-sm">{isTutor ? "Medizinischer KI-Tutor" : "Medizinischer KI-Assistent"}</h3>
          <div className="flex items-center gap-2">
            {/* Model Picker */}
            <div className="relative">
              <button onClick={onModelPickerToggle}
                className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md transition-colors hover:bg-white/5"
                style={{ color: currentModel.color }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: currentModel.color }} />
                {currentModel.name}
                <ChevronDown className="w-3 h-3" />
              </button>
              {showModelPicker && (
                <div className="absolute top-full left-0 mt-1 rounded-xl border p-1 z-50 min-w-[180px]"
                  style={{ background: '#0f1a3a', borderColor: 'rgba(59,130,246,0.15)' }}>
                  {MODELS.map(m => (
                    <button key={m.id} onClick={() => onModelSelect(m.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-sm transition-colors ${selectedModel === m.id ? 'bg-white/10' : 'hover:bg-white/5'}`}>
                      <span className="w-2 h-2 rounded-full" style={{ background: m.color }} />
                      <div>
                        <span className="text-white font-medium">{m.name}</span>
                        <span className="text-white/30 text-xs ml-2">{m.provider}</span>
                      </div>
                      {selectedModel === m.id && <span className="ml-auto text-xs" style={{ color: '#3b82f6' }}>&#10003;</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {isTutor && (
              <>
                <span className="text-white/10">|</span>
                {/* Specialty Picker */}
                <div className="relative">
                  <button onClick={onSpecialtyPickerToggle}
                    className="flex items-center gap-1 text-[11px] text-white/50 px-2 py-0.5 rounded-md transition-colors hover:bg-white/5">
                    <Database className="w-3 h-3" />
                    {selectedSpecialty ? specialties.find(s => s.id === selectedSpecialty)?.name || selectedSpecialty : "Alle Fächer"}
                    <ChevronDown className="w-3 h-3" />
                  </button>
                  {showSpecialtyPicker && (
                    <div className="absolute top-full left-0 mt-1 rounded-xl border p-1 z-50 min-w-[180px] max-h-[300px] overflow-y-auto"
                      style={{ background: '#0f1a3a', borderColor: 'rgba(59,130,246,0.15)' }}>
                      <button onClick={() => onSpecialtySelect("")}
                        className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors ${!selectedSpecialty ? 'bg-white/10' : 'hover:bg-white/5'}`}>
                        <Database className="w-3.5 h-3.5 text-white/40" />
                        <span className="text-white">Alle Fächer</span>
                      </button>
                      {specialties.map(s => (
                        <button key={s.id} onClick={() => onSpecialtySelect(s.id)}
                          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors ${selectedSpecialty === s.id ? 'bg-white/10' : 'hover:bg-white/5'}`}>
                          <span>{s.icon || "📄"}</span>
                          <span className="text-white">{s.name}</span>
                          <span className="ml-auto text-[10px] text-white/30">{s.question_count || ""}</span>
                          {selectedSpecialty === s.id && <span className="text-xs" style={{ color: '#3b82f6' }}>&#10003;</span>}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Chapter Picker */}
                {chapters.length > 0 && (
                  <>
                    <span className="text-white/10">|</span>
                    <div className="relative">
                      <button onClick={onChapterPickerToggle}
                        className="flex items-center gap-1 text-[11px] text-white/50 px-2 py-0.5 rounded-md transition-colors hover:bg-white/5">
                        <BookOpen className="w-3 h-3" />
                        {selectedChapter !== null ? (chapters.find(c => c.index === selectedChapter)?.title || `Kapitel ${selectedChapter + 1}`) : "Ganzes Dokument"}
                        <ChevronDown className="w-3 h-3" />
                      </button>
                      {showChapterPicker && (
                        <div className="absolute top-full left-0 mt-1 rounded-xl border p-1 z-50 min-w-[220px] max-h-[300px] overflow-y-auto"
                          style={{ background: '#0f1a3a', borderColor: 'rgba(59,130,246,0.15)' }}>
                          <button onClick={() => onChapterSelect(null)}
                            className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors ${selectedChapter === null ? 'bg-white/10' : 'hover:bg-white/5'}`}>
                            <BookOpen className="w-3.5 h-3.5 text-white/40" />
                            <span className="text-white">Ganzes Dokument</span>
                          </button>
                          {chapters.map(ch => (
                            <button key={ch.index} onClick={() => onChapterSelect(ch.index)}
                              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors ${selectedChapter === ch.index ? 'bg-white/10' : 'hover:bg-white/5'}`}>
                              <span className="text-white/40 text-xs w-5">{ch.index + 1}.</span>
                              <span className="text-white truncate">{ch.title}</span>
                              <span className="ml-auto text-[10px] text-white/30">S. {ch.page_start}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </>
            )}

            <span className="text-white/10">|</span>
            {/* Language Picker */}
            <div className="relative">
              <button onClick={onLangPickerToggle}
                className="flex items-center gap-1 text-[11px] text-white/50 px-2 py-0.5 rounded-md transition-colors hover:bg-white/5">
                <Globe className="w-3 h-3" />
                {currentLang.name}
                <ChevronDown className="w-3 h-3" />
              </button>
              {showLangPicker && (
                <div className="absolute top-full left-0 mt-1 rounded-xl border p-1 z-50 min-w-[160px]"
                  style={{ background: '#0f1a3a', borderColor: 'rgba(59,130,246,0.15)' }}>
                  {LANGUAGES.map(l => (
                    <button key={l.id} onClick={() => onLangSelect(l.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-sm transition-colors ${selectedLang === l.id ? 'bg-white/10' : 'hover:bg-white/5'}`}>
                      <span>{FLAG_EMOJI[l.flag]}</span>
                      <span className="text-white">{l.name}</span>
                      {selectedLang === l.id && <span className="ml-auto text-xs" style={{ color: '#3b82f6' }}>&#10003;</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-1">
        {isTutor && (
          <Button variant="ghost" size="icon" onClick={onNewConversation} className="text-white/30 hover:text-blue-400" title="Neue Konversation starten" aria-label="Neue Konversation starten">
            <PlusCircle className="w-4 h-4" />
          </Button>
        )}
        <Button variant="ghost" size="icon" onClick={onClose} className="text-white/40 hover:text-white">
          <X className="w-5 h-5" />
        </Button>
      </div>
    </div>
  );
}
