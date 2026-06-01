import useAIChat from "@/hooks/useAIChat";
import AIChatSidebar from "@/components/tutor/AIChatSidebar";
import AIChatHeader from "@/components/tutor/AIChatHeader";
import AIChatMessages from "@/components/tutor/AIChatMessages";
import AIChatInput from "@/components/tutor/AIChatInput";
import PageViewerModal from "@/components/tutor/PageViewerModal";
import ImageLightbox from "@/components/tutor/ImageLightbox";

export default function AIChat({ question, isOpen, onClose }) {
  const { isTutor, sidebarOpen, sidebarProps, headerProps, messagesProps, inputProps, modalProps } = useAIChat({ question, isOpen, onClose });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="w-full max-w-6xl h-[85vh] min-h-[500px] max-h-[90vh] rounded-2xl border shadow-2xl flex overflow-hidden animate-fadeIn"
        style={{ background: '#0c1229', borderColor: 'rgba(59,130,246,0.15)' }}>
        {isTutor && sidebarOpen && <AIChatSidebar {...sidebarProps} />}
        <div className="flex-1 flex flex-col min-w-0">
          <AIChatHeader {...headerProps} />
          <AIChatMessages {...messagesProps} />
          <AIChatInput {...inputProps} />
        </div>
      </div>
      <PageViewerModal {...modalProps.pageViewer} />
      <ImageLightbox {...modalProps.lightbox} />
    </div>
  );
}
