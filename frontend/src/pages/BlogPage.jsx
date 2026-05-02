import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/App";
import { BookOpen, Calendar, Eye, Tag, ArrowLeft, ArrowRight, GraduationCap, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";

function BlogList() {
  const [posts, setPosts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/blog/posts?limit=20`)
      .then(r => { setPosts(r.data.posts || []); setTotal(r.data.total || 0); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin w-8 h-8 border-2 border-[#c9a84c] border-t-transparent rounded-full" /></div>;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8" data-testid="blog-list">
      <div className="text-center mb-10">
        <BookOpen className="w-10 h-10 mx-auto mb-3" style={{ color: '#c9a84c' }} />
        <h1 className="text-3xl sm:text-4xl font-bold" style={{ fontFamily: "'Playfair Display', serif" }}>
          Medical <span style={{ color: '#c9a84c' }}>Blog</span>
        </h1>
        <p className="text-muted-foreground mt-2">Fachartikel für die Prüfungsvorbereitung</p>
        <p className="text-xs text-muted-foreground mt-1">{total} Artikel</p>
      </div>

      {posts.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <p>Noch keine Artikel veröffentlicht.</p>
          <p className="text-xs mt-2">Admins können Artikel über das Admin-Panel generieren.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {posts.map(post => (
            <Link key={post.id || post.slug} to={`/blog/${post.slug}`}
              className="block p-6 rounded-2xl border border-border/30 transition-all hover:border-[#c9a84c]/30 group"
              style={{ background: 'rgba(201,168,76,0.02)' }} data-testid={`blog-post-${post.slug}`}>
              <h2 className="text-xl font-bold group-hover:text-[#c9a84c] transition-colors" style={{ fontFamily: "'Playfair Display', serif" }}>
                {post.title}
              </h2>
              {post.excerpt && <p className="text-sm text-muted-foreground mt-2 line-clamp-2">{post.excerpt}</p>}
              <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> {new Date(post.created_at).toLocaleDateString("de-DE", { day: "numeric", month: "short", year: "numeric" })}</span>
                <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {post.views || 0}</span>
                {post.tags?.length > 0 && <span className="flex items-center gap-1"><Tag className="w-3 h-3" /> {post.tags.slice(0, 3).join(", ")}</span>}
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* CTA */}
      <div className="mt-10 p-6 rounded-2xl text-center" style={{ background: 'linear-gradient(135deg, rgba(201,168,76,0.1), rgba(201,168,76,0.03))', border: '1px solid rgba(201,168,76,0.2)' }}>
        <GraduationCap className="w-8 h-8 mx-auto mb-2" style={{ color: '#c9a84c' }} />
        <p className="text-sm font-medium mb-2">3.000+ MCQ Fragen zum Üben</p>
        <div className="flex gap-2 justify-center">
          <Link to="/register"><Button size="sm" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}><UserPlus className="w-3 h-3 mr-1" /> Kostenlos starten</Button></Link>
          <Link to="/guest-quiz"><Button size="sm" variant="outline">Kostenlos testen <ArrowRight className="w-3 h-3 ml-1" /></Button></Link>
        </div>
      </div>
    </div>
  );
}

function BlogPost() {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/blog/posts/${slug}`)
      .then(r => setPost(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin w-8 h-8 border-2 border-[#c9a84c] border-t-transparent rounded-full" /></div>;
  if (!post) return <div className="text-center py-20"><p className="text-muted-foreground">Artikel nicht gefunden</p><Link to="/blog" className="text-sm text-[#c9a84c] hover:underline">Zurück zum Blog</Link></div>;

  // Simple markdown renderer
  const renderBold = (text) => {
    const parts = text.split(/\*\*(.*?)\*\*/g);
    return parts.map((part, j) => j % 2 === 1 ? <strong key={j} className="text-foreground">{part}</strong> : part);
  };

  const renderContent = (md) => {
    return md.split("\n").map((line, i) => {
      if (line.startsWith("### ")) return <h3 key={i} className="text-lg font-bold mt-6 mb-2" style={{ color: '#c9a84c' }}>{renderBold(line.replace("### ", ""))}</h3>;
      if (line.startsWith("## ")) return <h2 key={i} className="text-xl font-bold mt-8 mb-3" style={{ fontFamily: "'Playfair Display', serif" }}>{renderBold(line.replace("## ", ""))}</h2>;
      if (line.startsWith("- ") || line.startsWith("* ")) return <li key={i} className="ml-4 text-sm text-muted-foreground mb-1">{renderBold(line.replace(/^[-*] /, ""))}</li>;
      if (line.trim() === "") return <div key={i} className="h-2" />;
      return <p key={i} className="text-sm text-muted-foreground leading-relaxed mb-2">{renderBold(line)}</p>;
    });
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8" data-testid="blog-post">
      <Link to="/blog" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-[#c9a84c] mb-6">
        <ArrowLeft className="w-4 h-4" /> Zurück zum Blog
      </Link>
      <h1 className="text-2xl sm:text-3xl font-bold mb-3" style={{ fontFamily: "'Playfair Display', serif" }}>{post.title}</h1>
      <div className="flex items-center gap-4 text-xs text-muted-foreground mb-6">
        <span>{post.author}</span>
        <span><Calendar className="w-3 h-3 inline mr-1" />{new Date(post.created_at).toLocaleDateString("de-DE", { day: "numeric", month: "long", year: "numeric" })}</span>
        <span><Eye className="w-3 h-3 inline mr-1" />{post.views || 0} Aufrufe</span>
      </div>
      {post.tags?.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {post.tags.map(t => <span key={t} className="px-2 py-1 rounded-full text-xs" style={{ background: 'rgba(201,168,76,0.1)', color: '#c9a84c' }}>{t}</span>)}
        </div>
      )}
      <div className="prose prose-sm dark:prose-invert max-w-none">
        {renderContent(post.content || "")}
      </div>
      <div className="mt-10 p-6 rounded-2xl text-center" style={{ background: 'rgba(201,168,76,0.05)', border: '1px solid rgba(201,168,76,0.15)' }}>
        <p className="text-sm font-medium mb-2">Bereit für die Prüfung?</p>
        <div className="flex gap-2 justify-center">
          <Link to="/register"><Button size="sm" style={{ background: 'linear-gradient(135deg, #c9a84c, #dbb85c)', color: '#06081a' }}>Kostenlos registrieren</Button></Link>
          <Link to="/guest-quiz"><Button size="sm" variant="outline">Fragen testen</Button></Link>
        </div>
      </div>
    </div>
  );
}

export default function BlogPage() {
  const { slug } = useParams();
  return slug ? <BlogPost /> : <BlogList />;
}
