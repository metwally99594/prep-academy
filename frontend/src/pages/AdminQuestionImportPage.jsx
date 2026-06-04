import { useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Upload, FileText, ArrowLeft, CheckCircle, XCircle, AlertCircle, Loader2, Eye, FileUp } from "lucide-react";

export default function AdminQuestionImportPage() {
  const { token } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };
  const fileInputRef = useRef(null);

  const [importId, setImportId] = useState(null);
  const [jobStatus, setJobStatus] = useState("idle");
  const [files, setFiles] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [validationSummary, setValidationSummary] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleUpload = useCallback(async (fileList) => {
    if (!fileList?.length) return;
    setProcessing(true);
    setValidationSummary(null);
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

      // Process the job
      const procRes = await axios.post(`${API}/admin/question-import/${jobId}/process`, {}, { headers, timeout: 300000 });
      setJobStatus(procRes.data.status);
      setFiles(procRes.data.errors?.length
        ? Array.from(fileList).map((f) => ({
            name: f.name,
            status: procRes.data.errors.find((e) => e.filename === f.name) ? "failed" : "parsed",
          }))
        : Array.from(fileList).map((f) => ({ name: f.name, status: "parsed" }))
      );

      // Load job details
      const jobRes = await axios.get(`${API}/admin/question-import/${jobId}`, { headers });
      setQuestions(jobRes.data.questions || []);

      if (procRes.data.errors?.length) {
        toast.warning(`${procRes.data.errors.length} file(s) had errors`);
      } else {
        toast.success(`${procRes.data.questions_extracted || 0} questions extracted`);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Upload failed";
      toast.error(msg);
      setJobStatus("failed");
    } finally {
      setProcessing(false);
    }
  }, [headers, API]);

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

  const statusBadge = (status) => {
    switch (status) {
      case "parsed": return <span className="inline-flex items-center gap-1 text-xs text-green-600"><CheckCircle className="w-3 h-3" /> Parsed</span>;
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
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="gap-2" onClick={handleValidate}>
                <Eye className="w-4 h-4" /> Validate
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

          {/* Table */}
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="text-left p-3 font-medium">#</th>
                  <th className="text-left p-3 font-medium">Question</th>
                  <th className="text-center p-3 font-medium">Options</th>
                  <th className="text-center p-3 font-medium">Correct Answers</th>
                  <th className="text-center p-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {questions.map((q, i) => (
                  <tr key={i} className="hover:bg-muted/30">
                    <td className="p-3 text-muted-foreground">{i + 1}</td>
                    <td className="p-3 max-w-md truncate">{q.question || <span className="italic text-muted-foreground">(empty)</span>}</td>
                    <td className="p-3 text-center">{q.options?.length || 0}</td>
                    <td className="p-3 text-center">
                      {q.correct_answers?.length
                        ? q.correct_answers.map((a) => a.replace(/^[A-Za-z]\)\s*/, "")).join(", ")
                        : <span className="text-muted-foreground">—</span>
                      }
                    </td>
                    <td className="p-3 text-center">{statusBadge(q.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

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
