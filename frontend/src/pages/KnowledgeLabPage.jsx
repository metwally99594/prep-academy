import { useEffect, useState, useContext, useCallback, useRef } from "react";
import axios from "axios";
import { AuthContext, API } from "@/App";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Search,
  BookOpen,
  FileText,
  Layers,
  Database,
  ChevronRight,
  ChevronDown,
  Loader2,
  ExternalLink,
  Image as ImageIcon,
  X,
} from "lucide-react";

// ── Category config ──────────────────────────────────────────────

const CATEGORY_CONFIG = {
  specialty: { label: "Specialties", icon: BookOpen, color: "text-blue-400" },
  concept: { label: "Concepts", icon: Layers, color: "text-emerald-400" },
  source: { label: "Source Summaries", icon: Database, color: "text-amber-400" },
  licensing: { label: "Licensing", icon: FileText, color: "text-violet-400" },
};

const CATEGORY_ORDER = ["specialty", "concept", "source", "licensing"];

// ── Helpers ──────────────────────────────────────────────────────

function formatDate(ts) {
  if (!ts) return "";
  const d = new Date(ts * 1000);
  return d.toLocaleDateString("de-DE", { day: "numeric", month: "short", year: "numeric" });
}

// ── KB Markdown Renderer ─────────────────────────────────────────

function KBMarkdown({ content, onNavigate }) {
  const components = {
    h1: ({ children }) => (
      <h1 className="text-xl font-bold mt-6 mb-3 leading-snug">{children}</h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-lg font-bold mt-5 mb-2 leading-snug">{children}</h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-base font-semibold mt-4 mb-1.5 leading-snug">{children}</h3>
    ),
    p: ({ children }) => (
      <p className="text-sm leading-relaxed mb-3 last:mb-0">{children}</p>
    ),
    strong: ({ children }) => (
      <strong className="font-semibold text-foreground">{children}</strong>
    ),
    em: ({ children }) => <em className="italic">{children}</em>,
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
    blockquote: ({ children }) => (
      <blockquote className="border-l-2 border-primary/40 pl-4 my-3 text-muted-foreground italic text-sm">
        {children}
      </blockquote>
    ),
    ul: ({ children }) => (
      <ul className="list-disc list-outside space-y-1 my-2 text-sm pl-5">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal list-outside space-y-1 my-2 text-sm pl-5">{children}</ol>
    ),
    li: ({ children }) => <li className="leading-relaxed">{children}</li>,
    table: ({ children }) => (
      <div className="overflow-x-auto my-3">
        <table className="w-full text-xs border-collapse">{children}</table>
      </div>
    ),
    thead: ({ children }) => <thead className="bg-muted/60">{children}</thead>,
    tbody: ({ children }) => <tbody>{children}</tbody>,
    tr: ({ children }) => (
      <tr className="border-b border-border/40">{children}</tr>
    ),
    th: ({ children }) => (
      <th className="px-3 py-2 text-left font-semibold text-foreground/90">{children}</th>
    ),
    td: ({ children }) => (
      <td className="px-3 py-2 text-foreground/80">{children}</td>
    ),
    hr: () => <hr className="my-4 border-border/40" />,
    a: ({ href, children }) => {
      if (!href) return children;
      if (href.endsWith(".md")) {
        const target = href.replace(".md", "").replace("../", "");
        return (
          <button
            onClick={() => onNavigate?.(target)}
            className="text-primary underline underline-offset-2 hover:text-primary/80 transition-colors text-left inline cursor-pointer"
          >
            {children}
          </button>
        );
      }
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary underline underline-offset-2 hover:text-primary/80 transition-colors"
        >
          {children}
        </a>
      );
    },
  };

  const processed = content
    ?.replace(/@(\w+)/g, "**@$1**")
    .replace(/#(\w+)/g, "_#$1_");

  return (
    <div className="prose-sm max-w-none text-foreground/90">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
        disallowedElements={["script", "iframe", "object", "embed", "form", "input"]}
        unwrapDisallowed
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
}

// ── Sidebar ──────────────────────────────────────────────────────

function KBSidebar({ pages, selectedPath, onSelect, searchQuery, onSearchChange, loading }) {
  const [collapsed, setCollapsed] = useState({});

  const grouped = {};
  for (const cat of CATEGORY_ORDER) {
    grouped[cat] = pages.filter((p) => p.category === cat);
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search */}
      <div className="p-3 pb-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search wiki..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-8 h-9 text-sm"
          />
        </div>
      </div>
      <Separator />
      {/* Page list */}
      <ScrollArea className="flex-1 px-2 py-2">
        {loading ? (
          <div className="space-y-2 p-2">
            {[...Array(8)].map((_, i) => (
              <Skeleton key={i} className="h-6 w-full" />
            ))}
          </div>
        ) : (
          CATEGORY_ORDER.map((cat) => {
            const items = grouped[cat] || [];
            if (items.length === 0) return null;
            const cfg = CATEGORY_CONFIG[cat];
            const Icon = cfg.icon;
            const isCollapsed = collapsed[cat];
            return (
              <div key={cat} className="mb-1">
                <button
                  onClick={() =>
                    setCollapsed((prev) => ({ ...prev, [cat]: !prev[cat] }))
                  }
                  className="flex items-center gap-1.5 w-full px-2 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors rounded"
                >
                  {isCollapsed ? (
                    <ChevronRight className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                  <Icon className={`h-3.5 w-3.5 ${cfg.color}`} />
                  {cfg.label}
                  <Badge variant="outline" className="ml-auto text-[10px] h-4 px-1">
                    {items.length}
                  </Badge>
                </button>
                {!isCollapsed && (
                  <div className="ml-1">
                    {items.map((page) => (
                      <button
                        key={page.path}
                        onClick={() => onSelect(page.path)}
                        className={`w-full text-left px-3 py-1 text-sm rounded transition-colors ${
                          selectedPath === page.path
                            ? "bg-primary/10 text-primary font-medium"
                            : "text-foreground/70 hover:bg-muted hover:text-foreground"
                        }`}
                      >
                        <span className="truncate block">{page.title}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </ScrollArea>
    </div>
  );
}

// ── Image Gallery ────────────────────────────────────────────────

function KBImageGallery({ images, onImageClick }) {
  if (!images || images.length === 0) return null;

  return (
    <div className="mt-8 pt-6 border-t border-border/40">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
        <ImageIcon className="h-3.5 w-3.5" />
        Associated Images ({images.length})
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {images.map((img) => (
          <button
            key={img.id}
            onClick={() => onImageClick(img)}
            className="group relative aspect-[4/3] rounded-lg overflow-hidden border border-border/40 bg-muted/30 hover:border-primary/40 transition-all"
          >
            <img
              src={`${API}/knowledge-lab/assets/images/${img.filename}`}
              alt={img.caption_de || img.filename}
              loading="lazy"
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
              onError={(e) => {
                e.target.style.display = "none";
                e.target.nextSibling.style.display = "flex";
              }}
            />
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors hidden items-center justify-center text-white text-xs">
              <ImageIcon className="h-4 w-4" />
            </div>
            {img.caption_de && (
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-2">
                <p className="text-[10px] text-white/90 leading-tight line-clamp-2">{img.caption_de}</p>
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function KBImageLightbox({ image, onClose }) {
  if (!image) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div className="relative max-w-5xl max-h-[95vh]" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={onClose}
          className="absolute -top-3 -right-3 z-10 w-8 h-8 rounded-full bg-background border border-border/40 flex items-center justify-center hover:bg-muted transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
        <img
          src={`${API}/knowledge-lab/assets/images/${image.filename}`}
          alt={image.caption_de || ""}
          className="max-w-full max-h-[85vh] object-contain rounded-lg"
        />
        {image.caption_de && (
          <p className="text-white/80 text-sm mt-3 text-center">{image.caption_de}</p>
        )}
        <div className="flex items-center justify-center gap-4 mt-2 text-xs text-white/50">
          <span>{image.width} × {image.height}px</span>
          <span>{Math.round(image.size_bytes / 1024)} KB</span>
          <span className="capitalize">{image.category}</span>
          <span>Page {image.pdf_page}</span>
        </div>
      </div>
    </div>
  );
}

// ── Main Content ─────────────────────────────────────────────────

function KBPageViewer({ page, onNavigate, loading, images, onImageClick }) {
  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/6" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    );
  }

  if (!page) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground p-8">
        <BookOpen className="h-16 w-16 mb-4 opacity-20" />
        <h2 className="text-xl font-semibold mb-2">Knowledge Lab</h2>
        <p className="text-sm text-center max-w-md">
          Browse the medical knowledge base. Select a page from the sidebar or search for a topic.
        </p>
      </div>
    );
  }

  const cfg = CATEGORY_CONFIG[page.category] || {};

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          {cfg.icon && <cfg.icon className={`h-4 w-4 ${cfg.color || ""}`} />}
          <Badge variant="secondary" className="text-[10px]">
            {cfg.label || page.category}
          </Badge>
          <span className="text-[11px] text-muted-foreground ml-auto">
            {page.word_count?.toLocaleString()} words · updated {formatDate(page.last_modified)}
          </span>
        </div>
        <h1 className="text-2xl font-bold">{page.title}</h1>
        {page.properties && (page.properties.type || page.properties.status || page.properties.last_reviewed) && (
          <div className="flex flex-wrap items-center gap-2 mt-2">
            {page.properties.type && (
              <Badge variant="outline" className="text-[10px] font-normal">
                type: {page.properties.type}
              </Badge>
            )}
            {page.properties.status && (
              <Badge variant="outline" className="text-[10px] font-normal">
                status: {page.properties.status}
              </Badge>
            )}
            {page.properties.last_reviewed && (
              <span className="text-[10px] text-muted-foreground">
                reviewed: {page.properties.last_reviewed}
              </span>
            )}
          </div>
        )}
      </div>

      <Separator className="mb-6" />

      {/* Content */}
      <KBMarkdown content={page.content} onNavigate={onNavigate} />

      {/* Gallery */}
      <KBImageGallery images={images} onImageClick={onImageClick} />

      {/* Related Pages */}
      {page.related_pages?.length > 0 && (
        <div className="mt-10 pt-6 border-t border-border/40">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Related Pages
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {page.related_pages.map((rp) => (
              <button
                key={rp.path}
                onClick={() => onNavigate(rp.path)}
                className="text-left p-3 rounded-lg border border-border/40 hover:bg-muted/50 transition-colors"
              >
                <div className="text-sm font-medium text-primary">{rp.title}</div>
                {rp.description && (
                  <div className="text-xs text-muted-foreground mt-0.5">{rp.description}</div>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Sources */}
      {page.sources?.length > 0 && (
        <div className="mt-6 pt-4 border-t border-border/40">
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            Sources
          </h3>
          <div className="space-y-1">
            {page.sources.map((src, i) => (
              <div key={i} className="text-xs text-muted-foreground flex items-center gap-1.5">
                <Database className="h-3 w-3" />
                {src.path ? (
                  <button
                    onClick={() => onNavigate(src.path)}
                    className="text-primary underline underline-offset-2 hover:text-primary/80"
                  >
                    {src.title}
                  </button>
                ) : (
                  <span>{src.title}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Search Results ───────────────────────────────────────────────

function KBSearchResults({ results, query, onSelect, loading }) {
  if (loading) {
    return (
      <div className="p-6 space-y-4">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (!query) return null;

  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground p-8">
        <Search className="h-12 w-12 mb-3 opacity-20" />
        <p className="text-sm">No results for "{query}"</p>
      </div>
    );
  }

  const cfgLookup = (cat) => CATEGORY_CONFIG[cat] || {};

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-4">
        <p className="text-sm text-muted-foreground">
          {results.length} result{results.length !== 1 ? "s" : ""} for "<strong>{query}</strong>"
        </p>
      </div>
      <div className="space-y-2">
        {results.map((r) => {
          const cfg = cfgLookup(r.category);
          return (
            <button
              key={r.path}
              onClick={() => onSelect(r.path)}
              className="w-full text-left p-4 rounded-lg border border-border/40 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center gap-2 mb-1">
                {cfg.icon && <cfg.icon className={`h-3.5 w-3.5 ${cfg.color || ""}`} />}
                <span className="text-sm font-medium text-primary">{r.title}</span>
                <Badge variant="outline" className="text-[10px] h-4 ml-auto">
                  Score {r.score}
                </Badge>
              </div>
              {r.snippet && (
                <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                  {r.snippet}
                </p>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Stats Bar ────────────────────────────────────────────────────

function KBStatsBar({ stats, loading }) {
  if (loading || !stats) {
    return (
      <div className="px-4 py-1.5 border-t border-border/40">
        <Skeleton className="h-4 w-48" />
      </div>
    );
  }

  return (
    <div className="px-4 py-1.5 border-t border-border/40 text-[11px] text-muted-foreground flex items-center gap-4">
      <span>{stats.total_pages} pages</span>
      <span>·</span>
      <span>{stats.total_words?.toLocaleString()} words</span>
      <span>·</span>
      <span>{stats.specialty_count} specialties</span>
      <span>·</span>
      <span>{stats.concept_count} concepts</span>
      <span>·</span>
      <span>{stats.source_count} sources</span>
      {stats.last_updated > 0 && (
        <>
          <span>·</span>
          <span>Updated {formatDate(stats.last_updated)}</span>
        </>
      )}
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────

export default function KnowledgeLabPage() {
  const { token, user } = useContext(AuthContext) || {};
  const [pages, setPages] = useState([]);
  const [selectedPath, setSelectedPath] = useState(null);
  const [pageData, setPageData] = useState(null);
  const [pageLoading, setPageLoading] = useState(false);
  const [sidebarLoading, setSidebarLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [pageImages, setPageImages] = useState([]);
  const [lightboxImage, setLightboxImage] = useState(null);
  const searchTimeout = useRef(null);

  // Fetch page list + stats on mount
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [pagesRes, statsRes] = await Promise.all([
          axios.get(`${API}/knowledge-lab/pages`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          axios.get(`${API}/knowledge-lab/stats`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);
        if (cancelled) return;
        setPages(pagesRes.data.pages || []);
        setStats(statsRes.data);
      } catch (err) {
        console.error("Knowledge Lab: failed to load", err);
      } finally {
        if (!cancelled) setSidebarLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [token]);

  // Fetch page content + images
  const loadPage = useCallback(async (path) => {
    setSelectedPath(path);
    setPageLoading(true);
    setPageData(null);
    setPageImages([]);
    setSearchQuery("");
    setSearchResults([]);
    try {
      const [pageRes, imgRes] = await Promise.all([
        axios.get(`${API}/knowledge-lab/pages/${encodeURIComponent(path)}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        axios.get(`${API}/knowledge-lab/images?page=${encodeURIComponent(path)}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);
      setPageData(pageRes.data);
      setPageImages(imgRes.data.images || []);
    } catch (err) {
      console.error("Knowledge Lab: failed to load page", err);
      setPageData(null);
      setPageImages([]);
    } finally {
      setPageLoading(false);
    }
  }, [token]);

  // Search with debounce
  const handleSearchChange = useCallback((value) => {
    setSearchQuery(value);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);

    if (!value.trim()) {
      setSearchResults([]);
      return;
    }

    setSearchLoading(true);
    searchTimeout.current = setTimeout(async () => {
      try {
        const res = await axios.get(`${API}/knowledge-lab/search?q=${encodeURIComponent(value)}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setSearchResults(res.data.results || []);
        setSelectedPath(null);
        setPageData(null);
      } catch (err) {
        console.error("Knowledge Lab: search failed", err);
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
  }, [token]);

  // Navigate to a page (from sidebar, search results, related links, source links)
  const handleNavigate = useCallback((path) => {
    loadPage(path);
  }, [loadPage]);

  const showSearchResults = searchQuery.trim().length > 0;

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className="w-64 border-r border-border/40 flex-shrink-0 hidden md:flex flex-col bg-muted/20">
          <KBSidebar
            pages={pages}
            selectedPath={selectedPath}
            onSelect={handleNavigate}
            searchQuery={searchQuery}
            onSearchChange={handleSearchChange}
            loading={sidebarLoading}
          />
        </div>

        {/* Main content */}
        <div className="flex-1 overflow-y-auto bg-background">
          {showSearchResults ? (
            <KBSearchResults
              results={searchResults}
              query={searchQuery}
              onSelect={handleNavigate}
              loading={searchLoading}
            />
          ) : (
            <KBPageViewer
              page={pageData}
              onNavigate={handleNavigate}
              loading={pageLoading}
              images={pageImages}
              onImageClick={setLightboxImage}
            />
          )}
        </div>
      </div>

      {/* Stats bar */}
      <KBStatsBar stats={stats} loading={sidebarLoading} />

      {/* Image Lightbox */}
      <KBImageLightbox image={lightboxImage} onClose={() => setLightboxImage(null)} />
    </div>
  );
}
