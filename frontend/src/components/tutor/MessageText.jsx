import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MessageText({ content, selectedLang }) {
  return (
    <div dir={selectedLang === "ar" ? "rtl" : "ltr"}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h2: ({ children }) => (
            <h2 className="text-base font-bold text-white mt-5 mb-2 leading-relaxed">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold text-white/90 mt-4 mb-1.5 leading-relaxed">{children}</h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-sm font-medium text-white/80 mt-3 mb-1 leading-relaxed">{children}</h4>
          ),
          p: ({ children }) => (
            <p className="text-white/80 leading-relaxed mb-2 last:mb-0">{children}</p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside space-y-1 mb-2 text-white/80 leading-relaxed">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside space-y-1 mb-2 text-white/80 leading-relaxed">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="text-white/80 leading-relaxed">{children}</li>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-white/90">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="text-white/70 italic">{children}</em>
          ),
          code: ({ children }) => (
            <code
              className="px-1 py-0.5 rounded text-xs"
              style={{ background: "rgba(59,130,246,0.1)", color: "#93c5fd" }}
            >{children}</code>
          ),
          pre: ({ children }) => (
            <pre
              className="px-3 py-2 rounded-lg mb-2 overflow-x-auto text-sm leading-relaxed"
              style={{ background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.06)" }}
            >{children}</pre>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto mb-2">
              <table className="w-full text-sm border-collapse">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="text-white/60 text-xs uppercase tracking-wider">{children}</thead>
          ),
          th: ({ children }) => (
            <th
              className="border px-3 py-2 text-left font-medium"
              style={{ borderColor: "rgba(255,255,255,0.08)" }}
            >{children}</th>
          ),
          td: ({ children }) => (
            <td
              className="border px-3 py-2 text-white/80"
              style={{ borderColor: "rgba(255,255,255,0.08)" }}
            >{children}</td>
          ),
          hr: () => (
            <hr className="my-3 border-0" style={{ height: "1px", background: "rgba(255,255,255,0.06)" }} />
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:underline"
            >{children}</a>
          ),
          blockquote: ({ children }) => (
            <blockquote
              className="pl-3 py-1 mb-2 text-white/60 italic text-xs leading-relaxed"
              style={{ borderLeft: "2px solid rgba(59,130,246,0.3)" }}
            >{children}</blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
