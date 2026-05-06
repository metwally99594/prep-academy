import { Link } from "react-router-dom";
import { ArrowLeft, FileText } from "lucide-react";

export default function TermsPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors">
        <ArrowLeft size={16} /> Zurück zur Startseite
      </Link>

      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(201,168,76,0.1)' }}>
          <FileText size={20} style={{ color: '#c9a84c' }} />
        </div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "'Playfair Display', serif" }}>Allgemeine Geschäftsbedingungen (AGB)</h1>
      </div>

      <div className="space-y-6 text-muted-foreground leading-relaxed text-sm">
        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">§ 1 Geltungsbereich</h2>
          <p>
            Diese Allgemeinen Geschäftsbedingungen gelten für alle Leistungen von PrepAcademy Elite gegenüber Nutzern der Online-Lernplattform unter prepacademy.at. Mit der Registrierung akzeptieren Sie diese AGB.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">§ 2 Leistungsumfang</h2>
          <p>PrepAcademy Elite bietet:</p>
          <ul className="list-disc pl-5 space-y-1 mt-2">
            <li>Zugang zu medizinischen Prüfungsfragen und Quiz-Funktionen</li>
            <li>KI-gestützte Analysen von medizinischen Bildern (EKG, Röntgen)</li>
            <li>PDF Notebook mit KI-Lernfunktionen</li>
            <li>Tägliche medizinische Podcasts</li>
            <li>Statistiken und Lernfortschrittsverfolgung</li>
          </ul>
          <p className="mt-2">
            <strong className="text-foreground">Wichtiger Hinweis:</strong> Alle KI-generierten Inhalte dienen ausschließlich zu Lernzwecken und ersetzen keine ärztliche Diagnose oder Beratung.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">§ 3 Registrierung und Konto</h2>
          <p>
            Die Nutzung erfordert eine Registrierung mit einer gültigen E-Mail-Adresse. Sie verpflichten sich, keine falschen Angaben zu machen und Ihre Zugangsdaten vertraulich zu behandeln. Pro Person ist nur ein Konto erlaubt.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">§ 4 Free-Tier und Premium</h2>
          <div className="space-y-3">
            <div>
              <strong className="text-foreground">Free-Tier (kostenlos):</strong>
              <ul className="list-disc pl-5 mt-1 space-y-1">
                <li>5 KI-Analysen pro Tag</li>
                <li>3 PDF-Uploads pro Tag</li>
                <li>Unbegrenzter Quiz-Zugang</li>
              </ul>
            </div>
            <div>
              <strong className="text-foreground">Premium-Abonnement:</strong>
              <ul className="list-disc pl-5 mt-1 space-y-1">
                <li>Unbegrenzte KI-Analysen</li>
                <li>Unbegrenzte PDF-Uploads</li>
                <li>Prioritäts-KI-Verarbeitung</li>
                <li>Alle Premium-Features</li>
              </ul>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">§ 5 Zahlungsbedingungen</h2>
          <p>
            Premium-Abonnements werden über Stripe abgewickelt. Der Kaufpreis ist zum Zeitpunkt des Kaufs fällig. Preise verstehen sich inklusive gesetzlicher Mehrwertsteuer. Zeitliche Zugangspässe (1 Monat, 6 Monate, 1 Jahr) verlängern sich nicht automatisch.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">§ 6 Widerrufsrecht</h2>
          <p>
            Als Verbraucher haben Sie ein 14-tägiges Widerrufsrecht. Da es sich um digitale Inhalte handelt, erlischt das Widerrufsrecht mit Beginn der Ausführung des Vertrags, wenn Sie ausdrücklich zugestimmt haben, dass wir vor Ablauf der Widerrufsfrist mit der Ausführung beginnen.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">§ 7 Nutzungsbedingungen</h2>
          <p>Folgendes ist untersagt:</p>
          <ul className="list-disc pl-5 space-y-1 mt-2">
            <li>Weitergabe von Zugangsdaten an Dritte</li>
            <li>Automatisierter Zugriff (Scraping, Bots)</li>
            <li>Upload urheberrechtlich geschützter Inhalte ohne Berechtigung</li>
            <li>Missbrauch der KI-Funktionen für nicht-medizinische Zwecke</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">§ 8 Haftungsbeschränkung</h2>
          <p>
            PrepAcademy Elite haftet nicht für Schäden, die durch die Nutzung von KI-generierten Inhalten entstehen. Medizinische Entscheidungen dürfen nicht allein auf Basis unserer Inhalte getroffen werden. Die Verfügbarkeit der Plattform wird mit bestmöglicher Sorgfalt sichergestellt, jedoch nicht garantiert.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">§ 9 Kündigung</h2>
          <p>
            Sie können Ihr Konto jederzeit durch Kontaktaufnahme unter <a href="mailto:kontakt@prepacademy.at" className="text-[#c9a84c] hover:underline">kontakt@prepacademy.at</a> löschen lassen. Bereits bezahlte Premium-Zugangspässe werden nicht zurückerstattet.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">§ 10 Anwendbares Recht</h2>
          <p>
            Es gilt österreichisches Recht unter Ausschluss des UN-Kaufrechts. Gerichtsstand ist Wien, Österreich.
          </p>
        </section>

        <p className="text-xs text-muted-foreground/50 pt-4 border-t border-border">
          Letzte Aktualisierung: Mai 2026
        </p>
      </div>
    </div>
  );
}
