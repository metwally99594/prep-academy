import { useState, useEffect, useRef } from "react";
import { X, Mail, User, Phone, MessageSquare, Send, CheckCircle } from "lucide-react";
import axios from "axios";
import { API } from "@/App";
import { toast } from "sonner";

export default function RequestAccessModal({ open, onClose }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const firstFieldRef = useRef(null);

  useEffect(() => {
    if (open) {
      setSuccess(false);
      setTimeout(() => firstFieldRef.current?.focus(), 100);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const reset = () => {
    setName("");
    setEmail("");
    setPhone("");
    setMessage("");
    setSuccess(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) {
      toast.error("Bitte Name und E-Mail eingeben");
      return;
    }
    setSubmitting(true);
    try {
      const res = await axios.post(`${API}/contact-requests`, {
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim() || null,
        message: message.trim() || null,
        feature_pack: "advanced_features",
      });
      setSuccess(true);
      toast.success(res.data?.message || "Anfrage gesendet!");
    } catch (err) {
      const detail = err.response?.data?.detail || "Fehler beim Senden. Bitte erneut versuchen.";
      if (detail.includes("ausstehende Anfrage")) {
        toast.success("Anfrage bereits gesendet — wir melden uns in Kürze!");
        setSuccess(true);
      } else {
        toast.error(detail);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center p-4"
      style={{ background: "rgba(8, 13, 26, 0.85)", backdropFilter: "blur(8px)" }}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="request-access-title"
    >
      <div
        className="relative w-full max-w-md rounded-2xl shadow-2xl overflow-hidden"
        style={{ background: "#0f1a3a", border: "1px solid rgba(59,130,246,0.25)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top accent */}
        <div
          className="absolute top-0 left-0 right-0 h-1"
          style={{ background: "linear-gradient(90deg, #3b82f6, #06b6d4, #3b82f6)" }}
        />

        {/* Close button */}
        <button
          type="button"
          onClick={onClose}
          aria-label="Schließen"
          className="absolute top-4 right-4 p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-all z-10"
        >
          <X className="w-5 h-5" />
        </button>

        {success ? (
          /* Success state */
          <div className="p-8 text-center" data-testid="contact-request-success">
            <div
              className="w-16 h-16 mx-auto mb-5 rounded-full flex items-center justify-center"
              style={{ background: "rgba(34,197,94,0.15)", border: "1px solid rgba(34,197,94,0.4)" }}
            >
              <CheckCircle className="w-8 h-8" style={{ color: "#22c55e" }} />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Vielen Dank!</h3>
            <p className="text-white/60 text-sm mb-6 leading-relaxed">
              Ihre Anfrage wurde erfolgreich gesendet. Unser Team wird sich in Kürze persönlich
              bei Ihnen melden.
            </p>
            <button
              type="button"
              onClick={() => { reset(); onClose(); }}
              className="w-full py-2.5 rounded-xl text-sm font-semibold btn-medical"
            >
              Schließen
            </button>
          </div>
        ) : (
          /* Form state */
          <form onSubmit={handleSubmit} className="p-7 pt-9" data-testid="contact-request-form">
            <h3 id="request-access-title" className="text-xl font-bold text-white mb-1">
              Zugang anfragen
            </h3>
            <p className="text-white/50 text-sm mb-6">
              Hinterlassen Sie Ihre Kontaktdaten. Unser Team meldet sich bei Ihnen mit den
              Zugangsinformationen.
            </p>

            <div className="space-y-4">
              {/* Name */}
              <div>
                <label className="block text-xs font-medium text-white/60 mb-1.5 tracking-wide uppercase">
                  Name <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                  <input
                    ref={firstFieldRef}
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Dr. Max Mustermann"
                    data-testid="contact-name-input"
                    className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-white/30 text-sm focus:outline-none focus:border-[#3b82f6]/60 focus:bg-white/8 transition-all"
                  />
                </div>
              </div>

              {/* Email */}
              <div>
                <label className="block text-xs font-medium text-white/60 mb-1.5 tracking-wide uppercase">
                  E-Mail <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="ihre.email@beispiel.de"
                    data-testid="contact-email-input"
                    className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-white/30 text-sm focus:outline-none focus:border-[#3b82f6]/60 focus:bg-white/8 transition-all"
                  />
                </div>
              </div>

              {/* Phone (optional) */}
              <div>
                <label className="block text-xs font-medium text-white/60 mb-1.5 tracking-wide uppercase">
                  Telefon <span className="text-white/30 normal-case font-normal">(optional)</span>
                </label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+43 ..."
                    data-testid="contact-phone-input"
                    className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-white/30 text-sm focus:outline-none focus:border-[#3b82f6]/60 focus:bg-white/8 transition-all"
                  />
                </div>
              </div>

              {/* Message (optional) */}
              <div>
                <label className="block text-xs font-medium text-white/60 mb-1.5 tracking-wide uppercase">
                  Nachricht <span className="text-white/30 normal-case font-normal">(optional)</span>
                </label>
                <div className="relative">
                  <MessageSquare className="absolute left-3 top-3 w-4 h-4 text-white/30" />
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Was möchten Sie wissen?"
                    rows={3}
                    maxLength={1000}
                    data-testid="contact-message-input"
                    className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-white/30 text-sm focus:outline-none focus:border-[#3b82f6]/60 focus:bg-white/8 transition-all resize-none"
                  />
                </div>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={submitting}
              data-testid="contact-submit-btn"
              className="w-full mt-6 py-3 rounded-xl text-sm font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed btn-medical flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Wird gesendet…
                </>
              ) : (
                <>
                  Anfrage senden
                  <Send className="w-4 h-4" />
                </>
              )}
            </button>

            <p className="text-[11px] text-white/30 text-center mt-4 leading-relaxed">
              Mit dem Absenden stimmen Sie der Verarbeitung Ihrer Daten zur Bearbeitung Ihrer
              Anfrage zu.
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
