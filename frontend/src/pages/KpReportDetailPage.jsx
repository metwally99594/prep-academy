import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { API } from "@/App";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, ArrowLeft, FileText, User, Calendar, AlertTriangle, Lightbulb, Stethoscope } from "lucide-react";
import axios from "axios";

export default function KpReportDetailPage() {
  const { reportId } = useParams();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/kp-reports/${reportId}`)
      .then(r => setReport(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [reportId]);

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <p className="text-lg text-muted-foreground">Protokoll nicht gefunden</p>
          <Link to="/kp-reports"><Button variant="outline" className="mt-4 gap-2"><ArrowLeft className="w-4 h-4" />Zurück</Button></Link>
        </div>
      </div>
    );
  }

  const passedColor = (p) => {
    if (p === "1/3") return "text-red-500 border-red-500/30";
    if (p === "2/3") return "text-amber-500 border-amber-500/30";
    if (p === "3/3") return "text-green-500 border-green-500/30";
    return "";
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Link to="/kp-reports" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6">
          <ArrowLeft className="w-4 h-4" />
          Alle Protokolle
        </Link>

        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 flex-wrap mb-3">
            <Badge variant="outline" className="text-base py-1 px-3">{report.state}</Badge>
            <Badge variant="outline" className="text-base py-1 px-3">{report.year}</Badge>
            <Badge variant="secondary" className="text-base py-1 px-3">{report.main_case}</Badge>
            <span className={`text-base font-semibold ${passedColor(report.passed)}`}>
              {report.passed} bestanden
            </span>
          </div>
          <h1 className="text-3xl font-bold">
            Kenntnisprüfung {report.state} {report.year}
          </h1>
          <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
            {report.author && <span className="flex items-center gap-1"><User className="w-4 h-4" />{report.author}</span>}
            {report.date && <span className="flex items-center gap-1"><Calendar className="w-4 h-4" />{report.date}</span>}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Full text */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><FileText className="w-5 h-5" />Prüfungsbericht</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="whitespace-pre-line text-sm leading-relaxed">
                  {report.full_text}
                </div>
              </CardContent>
            </Card>

            {/* Examiner notes */}
            {report.examiner_notes && (
              <Card className="border-amber-500/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-amber-500"><AlertTriangle className="w-5 h-5" />Prüfer-Notizen</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm">{report.examiner_notes}</p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Topics asked */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg"><Stethoscope className="w-5 h-5" />Gefragte Themen</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {report.topics_asked?.map(t => (
                    <Badge key={t} variant="secondary">{t}</Badge>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Highlights */}
            {report.questions_highlighted?.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg"><Lightbulb className="w-5 h-5" />Wichtige Fragen</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {report.questions_highlighted.map((q, i) => (
                      <li key={i} className="text-sm flex items-start gap-2">
                        <span className="text-primary mt-0.5">•</span>
                        {q}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* Difficulty */}
            {report.difficulty && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">Schwierigkeit</CardTitle>
                </CardHeader>
                <CardContent>
                  <Badge variant={report.difficulty === "schwer" ? "destructive" : report.difficulty === "mittel" ? "secondary" : "outline"}>
                    {report.difficulty === "schwer" ? "Schwer" : report.difficulty === "mittel" ? "Mittel" : "Leicht"}
                  </Badge>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
