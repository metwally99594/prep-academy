import { Link } from "react-router-dom";
import { ArrowLeft, Building2 } from "lucide-react";

export default function ImpressumPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors">
        <ArrowLeft size={16} /> Zurück zur Startseite
      </Link>

      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(201,168,76,0.1)' }}>
          <Building2 size={20} style={{ color: '#c9a84c' }} />
        </div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "'Playfair Display', serif" }}>Impressum</h1>
      </div>

      <div className="prose prose-sm dark:prose-invert max-w-none space-y-6 text-muted-foreground leading-relaxed">
        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2">Angaben gemäß § 5 TMG / § 25 MedienG</h2>
          <p>
            <strong className="text-foreground">PrepAcademy Elite</strong><br />
            [Name des Unternehmens / Inhabers]<br />
            [Straße und Hausnummer]<br />
            [PLZ Ort]<br />
            Österreich
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2">Kontakt</h2>
          <p>
            E-Mail: <a href="mailto:kontakt@prepacademy.at" className="text-[#c9a84c] hover:underline">kontakt@prepacademy.at</a><br />
            Website: <a href="https://prepacademy.at" className="text-[#c9a84c] hover:underline">prepacademy.at</a>
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2">Unternehmensgegenstand</h2>
          <p>
            PrepAcademy Elite bietet eine KI-gestützte Online-Lernplattform für die medizinische Prüfungsvorbereitung an.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2">Haftungsausschluss</h2>
          <h3 className="font-medium text-foreground mt-3 mb-1">Haftung für Inhalte</h3>
          <p>
            Die Inhalte dieser Plattform wurden mit größter Sorgfalt erstellt. Für die Richtigkeit, Vollständigkeit und Aktualität der Inhalte können wir jedoch keine Gewähr übernehmen. Die auf PrepAcademy bereitgestellten medizinischen Inhalte dienen ausschließlich zu Lernzwecken und ersetzen keine ärztliche Beratung oder Diagnose.
          </p>
          <h3 className="font-medium text-foreground mt-3 mb-1">Haftung für Links</h3>
          <p>
            Unser Angebot enthält Links zu externen Webseiten Dritter, auf deren Inhalte wir keinen Einfluss haben. Deshalb können wir für diese fremden Inhalte auch keine Gewähr übernehmen.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2">Urheberrecht</h2>
          <p>
            Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten unterliegen dem österreichischen und deutschen Urheberrecht. Die Vervielfältigung, Bearbeitung, Verbreitung und jede Art der Verwertung außerhalb der Grenzen des Urheberrechtes bedürfen der schriftlichen Zustimmung des jeweiligen Autors bzw. Erstellers.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2">Online-Streitbeilegung</h2>
          <p>
            Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit:{" "}
            <a href="https://ec.europa.eu/consumers/odr/" target="_blank" rel="noopener noreferrer" className="text-[#c9a84c] hover:underline">
              ec.europa.eu/consumers/odr
            </a>
          </p>
        </section>

        <p className="text-xs text-muted-foreground/50 pt-4 border-t border-border">
          Letzte Aktualisierung: Mai 2026
        </p>
      </div>
    </div>
  );
}
