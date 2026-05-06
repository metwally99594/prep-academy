import { Link } from "react-router-dom";
import { ArrowLeft, Shield } from "lucide-react";

export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors">
        <ArrowLeft size={16} /> Zurück zur Startseite
      </Link>

      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(201,168,76,0.1)' }}>
          <Shield size={20} style={{ color: '#c9a84c' }} />
        </div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "'Playfair Display', serif" }}>Datenschutzerklärung</h1>
      </div>

      <div className="space-y-6 text-muted-foreground leading-relaxed text-sm">
        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">1. Verantwortlicher</h2>
          <p>
            Verantwortlich für die Datenverarbeitung auf dieser Plattform ist:<br />
            <strong className="text-foreground">PrepAcademy Elite</strong><br />
            E-Mail: <a href="mailto:kontakt@prepacademy.at" className="text-[#c9a84c] hover:underline">kontakt@prepacademy.at</a>
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">2. Welche Daten wir erheben</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li><strong className="text-foreground">Konto-Daten:</strong> E-Mail-Adresse, Passwort (gehasht), Name</li>
            <li><strong className="text-foreground">Nutzungsdaten:</strong> Lernfortschritt, Quiz-Ergebnisse, hochgeladene PDFs</li>
            <li><strong className="text-foreground">Technische Daten:</strong> IP-Adresse (anonymisiert), Browser-Typ, Zugriffszeitpunkte</li>
            <li><strong className="text-foreground">Zahlungsdaten:</strong> Werden ausschließlich von Stripe verarbeitet — wir speichern keine Kreditkartendaten</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">3. Zweck der Verarbeitung</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Bereitstellung und Personalisierung der Lernplattform</li>
            <li>Analyse des Lernfortschritts und Empfehlung von Inhalten</li>
            <li>Verarbeitung von Zahlungen (Premium-Abonnement)</li>
            <li>Sicherheit und Missbrauchsprävention</li>
          </ul>
          <p className="mt-2">Rechtsgrundlage: Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) und Art. 6 Abs. 1 lit. f DSGVO (berechtigte Interessen).</p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">4. Analytik</h2>
          <p>
            Wir verwenden <strong className="text-foreground">Plausible Analytics</strong> — ein datenschutzfreundliches, cookie-freies Analysetool, das keine personenbezogenen Daten speichert und keine Einwilligung erfordert. Plausible ist DSGVO-konform und sammelt keine Daten, die zur Identifizierung einzelner Personen verwendet werden könnten.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">5. Drittanbieter</h2>
          <ul className="list-disc pl-5 space-y-2">
            <li><strong className="text-foreground">MongoDB Atlas</strong> (Datenspeicherung — USA, SCCs gemäß Art. 46 DSGVO)</li>
            <li><strong className="text-foreground">Stripe</strong> (Zahlungsabwicklung — Datenschutzerklärung: stripe.com/privacy)</li>
            <li><strong className="text-foreground">OpenRouter / OpenAI</strong> (KI-Analysen — hochgeladene Inhalte werden für KI-Anfragen verwendet)</li>
            <li><strong className="text-foreground">Vercel</strong> (Frontend-Hosting)</li>
            <li><strong className="text-foreground">Render</strong> (Backend-Hosting)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">6. Ihre Rechte (DSGVO)</h2>
          <p>Sie haben das Recht auf:</p>
          <ul className="list-disc pl-5 space-y-1 mt-2">
            <li>Auskunft über gespeicherte Daten (Art. 15 DSGVO)</li>
            <li>Berichtigung unrichtiger Daten (Art. 16 DSGVO)</li>
            <li>Löschung Ihrer Daten (Art. 17 DSGVO) — Kontakt: <a href="mailto:kontakt@prepacademy.at" className="text-[#c9a84c] hover:underline">kontakt@prepacademy.at</a></li>
            <li>Einschränkung der Verarbeitung (Art. 18 DSGVO)</li>
            <li>Datenübertragbarkeit (Art. 20 DSGVO)</li>
            <li>Widerspruch gegen die Verarbeitung (Art. 21 DSGVO)</li>
          </ul>
          <p className="mt-2">
            Sie haben außerdem das Recht, eine Beschwerde bei der Datenschutzbehörde einzureichen:<br />
            <strong className="text-foreground">Österreich:</strong> Datenschutzbehörde (dsb.gv.at)<br />
            <strong className="text-foreground">Deutschland:</strong> Zuständige Landesdatenschutzbehörde
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">7. Datenspeicherung und -löschung</h2>
          <p>
            Konto-Daten werden für die Dauer der Mitgliedschaft gespeichert. Nach Kündigung werden personenbezogene Daten innerhalb von 30 Tagen gelöscht, sofern keine gesetzlichen Aufbewahrungspflichten bestehen.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-foreground mb-2">8. Datensicherheit</h2>
          <p>
            Alle Datenübertragungen sind SSL/TLS-verschlüsselt. Passwörter werden mit bcrypt gehasht und niemals im Klartext gespeichert. JWT-Tokens haben eine begrenzte Gültigkeitsdauer.
          </p>
        </section>

        <p className="text-xs text-muted-foreground/50 pt-4 border-t border-border">
          Letzte Aktualisierung: Mai 2026
        </p>
      </div>
    </div>
  );
}
