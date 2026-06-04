import { useState, useCallback, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Upload, FileText, ArrowLeft, CheckCircle, XCircle, AlertCircle, Loader2, Eye, Sparkles, Download, FileDown } from "lucide-react";

export default function AdminQuestionImportPage() {
  const { token } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };
  const fileInputRef = useRef(null);

  const [importId, setImportId] = useState(null);
  const [jobStatus, setJobStatus] = useState("idle");
  const [files, setFiles] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [validationSummary, setValidationSummary] = useState(null);
  const [generationSummary, setGenerationSummary] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const pollIntervalRef = useRef(null);

  const pollJobStatus = useCallback(async (jobId) => {
    try {
      const res = await axios.get(`${API}/admin/question-import/${jobId}`, { headers, timeout: 10000 });
      const status = res.data.status;
      setJobStatus(status);

      if (status === "parsed") {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
        const qs = res.data.questions || [];
        setQuestions(qs);
        setFiles((res.data.files || []).map((f) => ({ name: f.filename, status: f.status })));
        setProcessing(false);
        toast.success(`${qs.length} questions extracted`);
      } else if (status === "failed") {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
        setFiles((res.data.files || []).map((f) => ({ name: f.filename, status: f.status })));
        setProcessing(false);
        toast.error("Extraction failed");
      }
      // else still "processing" or "uploaded" — keep polling
    } catch (err) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
      setProcessing(false);
      setJobStatus("failed");
      toast.error(err.response?.data?.detail || err.message || "Failed to check job status");
    }
  }, [headers, API]);

  const handleUpload = useCallback(async (fileList) => {
    if (!fileList?.length) return;
    setProcessing(true);
    setValidationSummary(null);
    setGenerationSummary(null);
    setQuestions([]);

    try {
      const formData = new FormData();
      for (const f of fileList) {
        formData.append("files", f);
      }
      const res = await axios.post(`${API}/admin/question-import`, formData, {
        headers: { ...headers, "Content-Type": "multipart/form-data" },
        timeout: 60000,
      });
      const jobId = res.data.import_id;
      setImportId(jobId);
      setJobStatus("uploaded");
      setFiles(Array.from(fileList).map((f) => ({ name: f.name, status: "uploaded" })));

      // Start processing (non-blocking — returns immediately)
      await axios.post(`${API}/admin/question-import/${jobId}/process`, {}, { headers, timeout: 15000 });
      setJobStatus("processing");

      // Poll for completion
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = setInterval(() => pollJobStatus(jobId), 2000);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Upload failed";
      toast.error(msg);
      setJobStatus("failed");
      setProcessing(false);
    }
  }, [headers, API, pollJobStatus]);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    handleUpload(e.dataTransfer.files);
  }, [handleUpload]);

  const handleFileSelect = useCallback((e) => {
    handleUpload(e.target.files);
  }, [handleUpload]);

  const handleValidate = useCallback(async () => {
    if (!importId) return;
    try {
      const res = await axios.post(`${API}/admin/question-import/${importId}/validate`, {}, { headers });
      setValidationSummary(res.data);
      toast.success(`Validation: ${res.data.valid} valid, ${res.data.invalid} invalid`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Validation failed");
    }
  }, [importId, headers, API]);

  const handleGenerateOptions = useCallback(async () => {
    if (!importId) return;
    setGenerating(true);
    setGenerationSummary(null);
    try {
      const res = await axios.post(`${API}/admin/question-import/${importId}/generate-options`, {}, { headers, timeout: 120000 });
      setGenerationSummary(res.data);
      const jobRes = await axios.get(`${API}/admin/question-import/${importId}`, { headers });
      setQuestions(jobRes.data.questions || []);
      toast.success(`Generated options: ${res.data.updated} updated, ${res.data.skipped} skipped`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Generation failed");
    } finally {
      setGenerating(false);
    }
  }, [importId, headers, API]);

  const handleExportJSON = useCallback(async () => {
    if (!importId) return;
    try {
      const res = await axios.get(`${API}/admin/question-import/${importId}/export/json`, { headers });
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `questions_${importId}.json`; a.click();
      URL.revokeObjectURL(url);
      toast.success("JSON exported");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Export failed");
    }
  }, [importId, headers, API]);

  const handleExportXLSX = useCallback(async () => {
    if (!importId) return;
    try {
      const res = await axios.get(`${API}/admin/question-import/${importId}/export/xlsx`, {
        headers, responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = `questions_${importId}.xlsx`; a.click();
      URL.revokeObjectURL(url);
      toast.success("Excel exported");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Export failed");
    }
  }, [importId, headers, API]);

  const statusBadge = (status) => {
    switch (status) {
      case "parsed": return <span className="inline-flex items-center gap-1 text-xs text-green-600"><CheckCircle className="w-3 h-3" /> Parsed</span>;
      case "completed": return <span className="inline-flex items-center gap-1 text-xs text-blue-600"><CheckCircle className="w-3 h-3" /> Completed</span>;
      case "failed_generation": return <span className="inline-flex items-center gap-1 text-xs text-orange-600"><AlertCircle className="w-3 h-3" /> Incomplete</span>;
      case "failed": return <span className="inline-flex items-center gap-1 text-xs text-red-600"><XCircle className="w-3 h-3" /> Failed</span>;
      default: return <span className="inline-flex items-center gap-1 text-xs text-amber-600"><AlertCircle className="w-3 h-3" /> {status}</span>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Question Import Tool</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Upload PDF or Markdown files to extract and manage exam questions
          </p>
        </div>
        <Link to="/admin">
          <Button variant="ghost" className="gap-2">
            <ArrowLeft className="w-4 h-4" /> Admin
          </Button>
        </Link>
      </div>

      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors cursor-pointer ${
          dragOver ? "border-amber-500 bg-amber-500/5" : "border-zinc-300 dark:border-zinc-600 hover:border-amber-400"
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.md,.markdown,.txt"
          className="hidden"
          onChange={handleFileSelect}
        />
        <Upload className="w-12 h-12 mx-auto mb-4 text-zinc-400" />
        <p className="text-lg font-medium">Drop files here or click to browse</p>
        <p className="text-sm text-muted-foreground mt-1">PDF, Markdown (.md, .markdown) or text files</p>
      </div>

      {/* Processing Status */}
      {processing && (
        <div className="flex items-center gap-3 p-4 bg-amber-50 dark:bg-amber-950/20 rounded-lg border border-amber-200 dark:border-amber-800">
          <Loader2 className="w-5 h-5 animate-spin text-amber-600" />
          <span>Processing files — OCR, parsing, and extracting questions...</span>
        </div>
      )}

      {/* Generating Status */}
      {generating && (
        <div className="flex items-center gap-3 p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
          <span>Generating AI distractors — this may take a moment...</span>
        </div>
      )}

      {/* Files Status */}
      {files.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-lg font-semibold">Files</h2>
          {files.map((f, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-card rounded-lg border">
              <div className="flex items-center gap-3">
                <FileText className="w-4 h-4 text-amber-500" />
                <span className="text-sm font-medium">{f.name}</span>
              </div>
              {statusBadge(f.status)}
            </div>
          ))}
        </div>
      )}

      {/* Questions Preview Table */}
      {questions.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              Extracted Questions ({questions.length})
            </h2>
            <div className="flex gap-2 flex-wrap">
              <Button variant="outline" size="sm" className="gap-2" onClick={handleValidate}>
                <Eye className="w-4 h-4" /> Validate
              </Button>
              <Button variant="outline" size="sm" className="gap-2" onClick={handleGenerateOptions} disabled={generating}>
                <Sparkles className="w-4 h-4" /> Generate Options
              </Button>
              <Button variant="outline" size="sm" className="gap-2" onClick={handleExportJSON}>
                <Download className="w-4 h-4" /> JSON
              </Button>
              <Button variant="outline" size="sm" className="gap-2" onClick={handleExportXLSX}>
                <FileDown className="w-4 h-4" /> Excel
              </Button>
            </div>
          </div>

          {/* Validation Summary */}
          {validationSummary && (
            <div className="flex gap-4 p-4 bg-card rounded-lg border">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{validationSummary.total_questions}</div>
                <div className="text-xs text-muted-foreground">Total</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{validationSummary.valid}</div>
                <div className="text-xs text-muted-foreground">Valid</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{validationSummary.invalid}</div>
                <div className="text-xs text-muted-foreground">Invalid</div>
              </div>
            </div>
          )}

          {/* Generation Summary */}
          {generationSummary && (
            <div className="flex gap-4 p-4 bg-card rounded-lg border">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{generationSummary.total}</div>
                <div className="text-xs text-muted-foreground">Total</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{generationSummary.updated}</div>
                <div className="text-xs text-muted-foreground">Updated</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-amber-600">{generationSummary.skipped}</div>
                <div className="text-xs text-muted-foreground">Skipped</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{generationSummary.failed}</div>
                <div className="text-xs text-muted-foreground">Failed</div>
              </div>
            </div>
          )}

          {/* Table */}
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="text-left p-3 font-medium">#</th>
                  <th className="text-left p-3 font-medium">Question</th>
                  <th className="text-center p-3 font-medium">Original Options</th>
                  <th className="text-center p-3 font-medium">Generated Options</th>
                  <th className="text-center p-3 font-medium">Final Options</th>
                  <th className="text-center p-3 font-medium">Correct Answers</th>
                  <th className="text-center p-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {questions.map((q, i) => {
                  const origCount = q.options?.length || 0;
                  const genCount = q.generated_options?.length || 0;
                  return (
                    <tr key={i} className="hover:bg-muted/30">
                      <td className="p-3 text-muted-foreground">{i + 1}</td>
                      <td className="p-3 max-w-md truncate">{q.question || <span className="italic text-muted-foreground">(empty)</span>}</td>
                      <td className="p-3 text-center">{origCount}</td>
                      <td className="p-3 text-center">{genCount}</td>
                      <td className="p-3 text-center">{origCount + genCount}</td>
                      <td className="p-3 text-center">
                        {q.correct_answers?.length
                          ? q.correct_answers.map((a) => a.replace(/^[A-Za-z]\)\s*/, "")).join(", ")
                          : <span className="text-muted-foreground">—</span>
                        }
                      </td>
                      <td className="p-3 text-center">{statusBadge(q.status)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Generation Detail */}
          {generationSummary?.results?.filter(r => r.generated?.length).length > 0 && (
            <div className="space-y-2">
              <h3 className="font-medium text-blue-600">Generated Options Detail</h3>
              {generationSummary.results.filter(r => r.generated?.length).map((r, i) => (
                <div key={i} className="p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-800">
                  <p className="text-sm font-medium">Q{r.index + 1}: {r.question}</p>
                  <ul className="text-xs text-blue-700 mt-1 list-disc list-inside">
                    {r.generated.map((g, j) => <li key={j}>{g}</li>)}
                  </ul>
                </div>
              ))}
            </div>
          )}

          {/* Validation Errors Detail */}
          {validationSummary?.errors?.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-medium text-red-600">Validation Errors</h3>
              {validationSummary.errors.map((err, i) => (
                <div key={i} className="p-3 bg-red-50 dark:bg-red-950/20 rounded-lg border border-red-200 dark:border-red-800">
                  <p className="text-sm font-medium">Question #{err.index + 1}: {err.question}</p>
                  <ul className="text-xs text-red-600 mt-1 list-disc list-inside">
                    {err.errors.map((e, j) => <li key={j}>{e}</li>)}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
