import { memo } from "react";

const REASON_LABELS = {
  contains_html:    "HTML-Markup",
  phi_detected:     "Patientendaten (PHI)",
  dangerous_advice: "Gefährlicher Ratschlag",
  multiple_reports: "Mehrfach gemeldet",
  high_report_rate: "Häufige Meldungen",
  new_user_links:   "Neuer Nutzer + Links",
  all_caps_title:   "GROSSBUCHSTABEN-Titel",
  profanity:        "Anstößige Sprache",
};

const REASON_COLORS = {
  phi_detected:     "bg-rose-500/10 text-rose-600 dark:text-rose-400",
  dangerous_advice: "bg-rose-500/10 text-rose-600 dark:text-rose-400",
  contains_html:    "bg-orange-500/10 text-orange-600 dark:text-orange-400",
  multiple_reports: "bg-red-500/10 text-red-600 dark:text-red-400",
  high_report_rate: "bg-red-500/10 text-red-600 dark:text-red-400",
  profanity:        "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  new_user_links:   "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  all_caps_title:   "bg-muted text-muted-foreground",
};

export const ReportReasonBadge = memo(function ReportReasonBadge({ reasonKey }) {
  const label = REASON_LABELS[reasonKey] || reasonKey;
  const color = REASON_COLORS[reasonKey] || "bg-muted text-muted-foreground";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium ${color}`}>
      {label}
    </span>
  );
});
