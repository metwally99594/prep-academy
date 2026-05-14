import { Link } from "react-router-dom";
import { ArrowLeft, Building2 } from "lucide-react";

export default function ImpressumPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors">
        <ArrowLeft size={16} /> Zurück zur Startseite
      </Link>

      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(59,130,246,0.1)' }}>
          <Building2 size={20} style={{ color: '#3b82f6' }} />
        </div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "'Playfair Display', serif" }}>Impressum</h1>
      </div>

      <div className="prose prose-sm dark:prose-invert max-w-none space-y-6 text-muted-foreground leading-relaxed">
        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2">Angaben gemäß § 5 TMG</h2>
          <p>
            <strong className="text-foreground">Mohamed Metwally</strong><br />
            Lussmer Ring 69<br />
            28777 Bremen<br />
            Deutschland
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2">Kontakt</h2>
          <p>
            Telefon: <a href="tel:+4915561785638" className="text-[#3b82f6] hover:underline">+49 15561 785638</a><br />
            E-Mail: <a href="mailto:mohamedmetwle99@gmail.com" className="text-[#3b82f6] hover:underline">mohamedmetwle99@gmail.com</a>
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2">Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV</h2>
          <p>
            Mohamed Metwally<br />
            Lussmer Ring 69<br />
            28777 Bremen<br />
            Deutschland
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2">Haftungsausschluss</h2>

          <h3 className="font-medium text-foreground mt-3 mb-1">Haftung für Inhalte</h3>
          <p>
            Die Inhalte unserer Seiten wurden mit größter Sorgfalt erstellt. Für die Richtigkeit, Vollständigkeit
            und Aktualität der Inhalte können wir jedoch keine Gewähr übernehmen. Als Diensteanbieter sind wir
            gemäß § 7 Abs. 1 TMG für eigene Inhalte auf diesen Seiten nach den allgemeinen Gesetzen verantwortlich.
          </p>

          <h3 className="font-medium text-foreground mt-3 mb-1">Haftung für Links</h3>
          <p>
            Unser Angebot enthält Links zu externen Websites Dritter, auf deren Inhalte wir keinen Einfluss haben.
            Deshalb können wir für diese fremden Inhalte auch keine Gewähr übernehmen. Für die Inhalte der
            verlinkten Seiten ist stets der jeweilige Anbieter oder Betreiber der Seiten verantwortlich.
          </p>

          <h3 className="font-medium text-foreground mt-3 mb-1">Urheberrecht</h3>
          <p>
            Die durch den Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten unterliegen dem deutschen
            Urheberrecht. Die Vervielfältigung, Bearbeitung, Verbreitung und jede Art der Verwertung außerhalb der
            Grenzen des Urheberrechtes bedürfen der schriftlichen Zustimmung des jeweiligen Autors bzw. Erstellers.
          </p>

          <h3 className="font-medium text-foreground mt-3 mb-1">Medizinischer Hinweis</h3>
          <p>
            Die bereitgestellten Inhalte dienen ausschließlich Bildungszwecken und ersetzen keine professionelle
            ärztliche Beratung, Diagnose oder Behandlung. Bei medizinischen Fragen wenden Sie sich bitte an einen
            zugelassenen Arzt oder medizinisches Fachpersonal.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground mb-2">Online-Streitbeilegung</h2>
          <p>
            Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit:{" "}
            <a href="https://ec.europa.eu/consumers/odr/" target="_blank" rel="noopener noreferrer" className="text-[#3b82f6] hover:underline">
              ec.europa.eu/consumers/odr
            </a>
            . Unsere E-Mail-Adresse finden Sie oben im Impressum. Wir sind nicht verpflichtet und nicht bereit,
            an einem Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle teilzunehmen.
          </p>
        </section>

        <p className="text-xs text-muted-foreground/50 pt-4 border-t border-border">
          Letzte Aktualisierung: Mai 2026
        </p>
      </div>
    </div>
  );
}
