import { useState, useRef, useCallback, useEffect } from "react";
import { Mic, Square, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function VoiceInputButton({ onTranscribed }) {
  const [state, setState] = useState("idle");
  const mediaRecorder = useRef(null);
  const chunks = useRef([]);

  useEffect(() => {
    return () => {
      if (mediaRecorder.current && mediaRecorder.current.state !== "inactive") {
        mediaRecorder.current.stop();
      }
    };
  }, []);

  const handleClick = useCallback(async () => {
    if (state === "recording") {
      mediaRecorder.current?.stop();
      setState("transcribing");
      return;
    }
    if (state === "transcribing") return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks.current = [];
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      mediaRecorder.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunks.current, { type: "audio/webm" });

        try {
          const { transcribeAudio } = await import("@/lib/api");
          const data = await transcribeAudio(blob);
          if (data?.transcript) {
            onTranscribed(data.transcript);
          } else {
            toast.error("Kein Transkript erhalten");
          }
        } catch (err) {
          const msg = err?.response?.data?.detail || err?.message || "Transkription fehlgeschlagen";
          toast.error(msg);
        }
        setState("idle");
      };

      recorder.onerror = () => {
        stream.getTracks().forEach(t => t.stop());
        setState("idle");
        toast.error("Aufnahmefehler");
      };

      recorder.start();
      setState("recording");
    } catch (err) {
      setState("idle");
      if (err?.name === "NotAllowedError" || err?.name === "PermissionDeniedError") {
        toast.error("Mikrofon-Zugriff verweigert — bitte erlauben in den Browser-Einstellungen");
      } else if (err?.name === "NotFoundError") {
        toast.error("Kein Mikrofon gefunden");
      } else if (err?.name === "NotReadableError") {
        toast.error("Mikrofon wird von einer anderen App verwendet");
      } else {
        toast.error(err?.message || "Mikrofon-Zugriff fehlgeschlagen");
      }
    }
  }, [state, onTranscribed]);

  return (
    <button
      onClick={handleClick}
      disabled={state === "transcribing"}
      className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all flex-shrink-0 ${
        state === "recording"
          ? "bg-red-500/20 text-red-400 animate-pulse shadow-lg shadow-red-500/20"
          : state === "transcribing"
            ? "bg-amber-500/20 text-amber-400"
            : "bg-muted hover:bg-muted/80 text-muted-foreground"
      }`}
      title={state === "idle" ? "Mikrofon" : state === "recording" ? "Aufnahme beenden" : "Transkribiere..."}
    >
      {state === "transcribing" ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <Mic className="w-4 h-4" />
      )}
    </button>
  );
}
