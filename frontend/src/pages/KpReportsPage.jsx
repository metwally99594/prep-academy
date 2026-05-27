import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { API } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, FileText, Filter, Search, BookOpen } from "lucide-react";
import axios from "axios";

export default function KpReportsPage() {
  const [reports, setReports] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ state: "", year: "", case: "", passed: "" });
  const [filterOptions, setFilterOptions] = useState({ states: [], years: [], cases: [] });
  const [pagination, setPagination] = useState({ offset: 0, limit: 50 });

  useEffect(() => {
    axios.get(`${API}/kp-reports/filters/aggregated`)
      .then(r => setFilterOptions(r.data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (filters.state) params.set("state", filters.state);
    if (filters.year) params.set("year", filters.year);
    if (filters.case) params.set("case", filters.case);
    if (filters.passed) params.set("passed", filters.passed);
    params.set("limit", pagination.limit);
    params.set("offset", pagination.offset);

    axios.get(`${API}/kp-reports?${params}`)
      .then(r => {
        setReports(r.data.reports);
        setTotal(r.data.total);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filters, pagination]);

  const resetFilters = () => {
    setFilters({ state: "", year: "", case: "", passed: "" });
    setPagination({ offset: 0, limit: 50 });
  };

  const passedColor = (p) => {
    if (p === "1/3") return "text-red-500 border-red-500/30";
    if (p === "2/3") return "text-amber-500 border-amber-500/30";
    if (p === "3/3") return "text-green-500 border-green-500/30";
    return "text-muted-foreground";
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <FileText className="w-8 h-8 text-primary" />
              Kenntnisprüfung Protokolle
            </h1>
            <p className="text-muted-foreground mt-1">
              Erfahrungsberichte von Ärzten aus der Kenntnisprüfung — durchsuchbar nach Bundesland, Jahr und Fachgebiet
            </p>
          </div>
        </div>

        {/* Filters */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Filter className="w-5 h-5" />
              Filter
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Bundesland</label>
                <Select value={filters.state} onValueChange={(v) => { setFilters(f => ({ ...f, state: v })); setPagination(p => ({ ...p, offset: 0 })); }}>
                  <SelectTrigger><SelectValue placeholder="Alle" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value=" ">Alle</SelectItem>
                    {filterOptions.states.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Jahr</label>
                <Select value={filters.year} onValueChange={(v) => { setFilters(f => ({ ...f, year: v })); setPagination(p => ({ ...p, offset: 0 })); }}>
                  <SelectTrigger><SelectValue placeholder="Alle" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value=" ">Alle</SelectItem>
                    {filterOptions.years.map(y => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Fall / Diagnose</label>
                <Input
                  placeholder="z.B. Divertikulitis"
                  value={filters.case}
                  onChange={(e) => { setFilters(f => ({ ...f, case: e.target.value })); setPagination(p => ({ ...p, offset: 0 })); }}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Status</label>
                <Select value={filters.passed} onValueChange={(v) => { setFilters(f => ({ ...f, passed: v })); setPagination(p => ({ ...p, offset: 0 })); }}>
                  <SelectTrigger><SelectValue placeholder="Alle" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value=" ">Alle</SelectItem>
                    <SelectItem value="1/3">1/3 bestanden</SelectItem>
                    <SelectItem value="2/3">2/3 bestanden</SelectItem>
                    <SelectItem value="3/3">3/3 bestanden</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end">
                <Button variant="outline" className="w-full gap-2" onClick={resetFilters}>
                  <Search className="w-4 h-4" />
                  Zurücksetzen
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Results */}
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : reports.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <BookOpen className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg">Keine Protokolle gefunden</p>
            <p className="text-sm mt-1">Versuche die Filter anzupassen</p>
          </div>
        ) : (
          <>
            <p className="text-sm text-muted-foreground mb-4">{total} Protokolle gefunden</p>
            <div className="space-y-4">
              {reports.map((report) => (
                <Link key={report.id} to={`/kp-reports/${report.id}`}>
                  <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                    <CardContent className="p-5">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap mb-2">
                            <Badge variant="outline">{report.state}</Badge>
                            <Badge variant="outline">{report.year}</Badge>
                            <Badge variant="secondary">{report.main_case}</Badge>
                            <span className={`text-sm font-medium ${passedColor(report.passed)}`}>
                              {report.passed} bestanden
                            </span>
                          </div>
                          <h3 className="font-medium text-base mb-1">
                            Kenntnisprüfung {report.state} {report.year}
                          </h3>
                          <p className="text-sm text-muted-foreground line-clamp-2">
                            {report.full_text}
                          </p>
                          <div className="flex items-center gap-2 mt-2">
                            {report.topics_asked?.slice(0, 5).map(t => (
                              <span key={t} className="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded">{t}</span>
                            ))}
                            {(report.topics_asked?.length || 0) > 5 && (
                              <span className="text-xs text-muted-foreground">+{report.topics_asked.length - 5}</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>

            {/* Pagination */}
            {total > pagination.limit && (
              <div className="flex items-center justify-center gap-4 mt-8">
                <Button
                  variant="outline"
                  disabled={pagination.offset === 0}
                  onClick={() => setPagination(p => ({ ...p, offset: Math.max(0, p.offset - p.limit) }))}
                >
                  Vorherige
                </Button>
                <span className="text-sm text-muted-foreground">
                  {pagination.offset + 1}–{Math.min(pagination.offset + pagination.limit, total)} von {total}
                </span>
                <Button
                  variant="outline"
                  disabled={pagination.offset + pagination.limit >= total}
                  onClick={() => setPagination(p => ({ ...p, offset: p.offset + p.limit }))}
                >
                  Nächste
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
