import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// react-markdown v9 does NOT render raw HTML by default — safe out of the box.
// remarkGfm adds tables, strikethrough, task lists, autolinks.

const components = {
  // Headings
  h1: ({ children }) => <h1 className="text-lg font-bold mt-4 mb-2 leading-snug">{children}</h1>,
  h2: ({ children }) => <h2 className="text-base font-bold mt-3 mb-1.5 leading-snug">{children}</h2>,
  h3: ({ children }) => <h3 className="text-sm font-semibold mt-2 mb-1 leading-snug">{children}</h3>,

  // Paragraphs
  p: ({ children }) => <p className="text-sm leading-relaxed mb-2 last:mb-0">{children}</p>,

  // Bold / italic
  strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,

  // Code blocks
  code({ inline, className, children }) {
    const lang = className?.replace("language-", "") || "";
    if (inline) {
      return (
        <code className="px-1.5 py-0.5 rounded bg-muted font-mono text-[0.8em] text-foreground">
          {children}
        </code>
      );
    }
    return (
      <div className="relative my-3">
        {lang && (
          <div className="absolute top-2 right-3 text-[9px] font-mono text-muted-foreground uppercase tracking-wider">
            {lang}
          </div>
        )}
        <pre className="overflow-x-auto rounded-xl bg-muted/80 p-4 text-xs font-mono leading-relaxed">
          <code>{children}</code>
        </pre>
      </div>
    );
  },

  // Blockquote
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-primary/40 pl-4 my-3 text-muted-foreground italic text-sm">
      {children}
    </blockquote>
  ),

  // Lists
  ul: ({ children }) => <ul className="list-disc list-inside space-y-1 my-2 text-sm pl-2">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 my-2 text-sm pl-2">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,

  // Tables (remark-gfm)
  table: ({ children }) => (
    <div className="overflow-x-auto my-3">
      <table className="w-full text-xs border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-muted/60">{children}</thead>,
  tbody: ({ children }) => <tbody>{children}</tbody>,
  tr: ({ children }) => <tr className="border-b border-border/40">{children}</tr>,
  th: ({ children }) => (
    <th className="px-3 py-2 text-left font-semibold text-foreground/90">{children}</th>
  ),
  td: ({ children }) => <td className="px-3 py-2 text-foreground/80">{children}</td>,

  // Horizontal rule
  hr: () => <hr className="my-4 border-border/40" />,

  // Links — open external links in new tab, no raw href exposure
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary underline underline-offset-2 hover:text-primary/80 transition-colors"
    >
      {children}
    </a>
  ),

  // Task list items (remark-gfm)
  input: ({ checked }) => (
    <input
      type="checkbox"
      checked={checked}
      readOnly
      className="mr-1.5 accent-primary align-middle"
    />
  ),
};

export const MarkdownRenderer = memo(function MarkdownRenderer({ content, className = "" }) {
  if (!content) return null;

  // Highlight @mentions and #hashtags before passing to markdown
  // We do this as a plain text pre-process since react-markdown handles the rest
  const processed = content
    .replace(/@(\w+)/g, "**@$1**")
    .replace(/#(\w+)/g, "_#$1_");

  return (
    <div className={`prose-sm max-w-none text-foreground/90 ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
        // disallowedElements ensures no raw HTML slips through even if content has HTML
        disallowedElements={["script", "iframe", "object", "embed", "form", "input"]}
        unwrapDisallowed
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
});
