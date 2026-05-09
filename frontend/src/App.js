import { createContext, useContext, useState, useEffect, useCallback, lazy, Suspense } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";
import ErrorBoundary from "@/components/ErrorBoundary";
import KeyboardShortcuts from "@/components/KeyboardShortcuts";
import { Loader2 } from "lucide-react";

// Eager load critical pages
import HomePage from "@/pages/HomePage";
import LoginPage from "@/pages/LoginPage";
import Layout from "@/components/Layout";

// Lazy load non-critical pages
const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const ExamSimulationPage = lazy(() => import("@/pages/ExamSimulationPage"));
const RegisterPage = lazy(() => import("@/pages/RegisterPage"));
// AuthCallback removed - Google Auth disabled
const SpecialtyPage = lazy(() => import("@/pages/SpecialtyPage"));
const QuizPage = lazy(() => import("@/pages/QuizPage"));
const FavoritesPage = lazy(() => import("@/pages/FavoritesPage"));
const ReviewPage = lazy(() => import("@/pages/ReviewPage"));
const SearchResultsPage = lazy(() => import("@/pages/SearchResultsPage"));
const StatsPage = lazy(() => import("@/pages/StatsPage"));
const AdminPage = lazy(() => import("@/pages/AdminPage"));
const AdminAnalyticsPage = lazy(() => import("@/pages/AdminAnalyticsPage"));
const LeaderboardPage = lazy(() => import("@/pages/LeaderboardPage"));
const NotebookPage = lazy(() => import("@/pages/NotebookPage"));
const CustomQuizPage = lazy(() => import("@/pages/CustomQuizPage"));
const AnalyzerPage = lazy(() => import("@/pages/AnalyzerPage"));
const MyNotesPage = lazy(() => import("@/pages/MyNotesPage"));
const BillingPage = lazy(() => import("@/pages/BillingPage"));
const BillingSuccessPage = lazy(() => import("@/pages/BillingSuccessPage"));
const DailyPodcastPage = lazy(() => import("@/pages/DailyPodcastPage"));
const LerntoolsPage = lazy(() => import("@/pages/LerntoolsPage"));
const RagPage = lazy(() => import("@/pages/RagPage"));
const DicomPage = lazy(() => import("@/pages/DicomPage"));
const GuestQuizPage = lazy(() => import("@/pages/GuestQuizPage"));
const ChallengePage = lazy(() => import("@/pages/ChallengePage"));
const SEOSpecialtyPage = lazy(() => import("@/pages/SEOSpecialtyPage"));
const SpacedReviewPage = lazy(() => import("@/pages/SpacedReviewPage"));
const BlogPage = lazy(() => import("@/pages/BlogPage"));
const ImpressumPage = lazy(() => import("@/pages/ImpressumPage"));
const PrivacyPage = lazy(() => import("@/pages/PrivacyPage"));
const TermsPage = lazy(() => import("@/pages/TermsPage"));
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage"));
const VerifyEmailPage = lazy(() => import("@/pages/VerifyEmailPage"));
const ForgotPasswordPage = lazy(() => import("@/pages/ForgotPasswordPage"));
const ResetPasswordPage = lazy(() => import("@/pages/ResetPasswordPage"));
const MessagingPage = lazy(() => import("@/pages/MessagingPage"));
const CommunityPage = lazy(() => import("@/pages/CommunityPage"));
const CommunityPostPage = lazy(() => import("@/pages/CommunityPostPage"));

// API Configuration - Use relative URL for production, full URL for development
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';

// Global 401 interceptor — clears stale token and redirects to login
axios.interceptors.response.use(
  response => response,
  error => {
    if (
      error.response?.status === 401 &&
      localStorage.getItem("token") &&
      !error.config?.url?.includes('/auth/')
    ) {
      localStorage.removeItem("token");
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth Context
export const AuthContext = createContext(null);

// Theme Context
export const ThemeContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
};

const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "dark");

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => setTheme(prev => prev === "light" ? "dark" : "light");

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    if (token) {
      try {
        const response = await axios.get(`${API}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setUser(response.data);
      } catch (error) {
        console.error("Token verification failed:", error);
        localStorage.removeItem("token");
        setToken(null);
      }
    }
    setLoading(false);
  }, [token]);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Heartbeat to track online status - use user.id to avoid re-runs from object reference changes
  const userId = user?.id;
  useEffect(() => {
    if (!token || !userId) return;
    
    let isMounted = true;
    const sendHeartbeat = async () => {
      if (!isMounted) return;
      try {
        await axios.post(`${API}/admin/activity/heartbeat`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
      } catch (error) {
        // Silently fail - not critical
      }
    };
    
    // Send immediately and every 2 minutes
    sendHeartbeat();
    const interval = setInterval(sendHeartbeat, 120000);
    
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [token, userId]);

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    const { token: newToken, user: userData } = response.data;
    localStorage.setItem("token", newToken);
    setToken(newToken);
    setUser(userData);
    return userData;
  };

  const register = async (email, password, name) => {
    const response = await axios.post(`${API}/auth/register`, { email, password, name });
    const data = response.data;
    if (data.token) {
      localStorage.setItem("token", data.token);
      setToken(data.token);
      setUser(data.user);
    }
    return data;
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// Protected Route
const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && !user.is_admin) {
    return <Navigate to="/" replace />;
  }

  return children;
};

const PageLoader = () => (
  <div className="flex items-center justify-center min-h-[60vh]">
    <Loader2 className="w-8 h-8 animate-spin text-primary" />
  </div>
);

// App Router with OAuth callback detection
function AppRouter() {
  
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/guest-quiz" element={<GuestQuizPage />} />
          <Route path="/fragen/:specialtyId" element={<SEOSpecialtyPage />} />
          <Route path="/blog" element={<BlogPage />} />
          <Route path="/blog/:slug" element={<BlogPage />} />
          <Route path="/challenge/:challengeId" element={
            <ProtectedRoute><ChallengePage /></ProtectedRoute>
          } />
          <Route path="/spaced-review" element={
            <ProtectedRoute><SpacedReviewPage /></ProtectedRoute>
          } />
          <Route path="/dashboard" element={
            <ProtectedRoute><DashboardPage /></ProtectedRoute>
          } />
          <Route path="/exam-simulation" element={
            <ProtectedRoute><ExamSimulationPage /></ProtectedRoute>
          } />
          <Route path="/specialty/:specialtyId" element={
            <ProtectedRoute><SpecialtyPage /></ProtectedRoute>
          } />
          <Route path="/quiz/:specialtyId" element={
            <ProtectedRoute><QuizPage /></ProtectedRoute>
          } />
          <Route path="/favorites" element={
            <ProtectedRoute><FavoritesPage /></ProtectedRoute>
          } />
          <Route path="/review" element={
            <ProtectedRoute><ReviewPage /></ProtectedRoute>
          } />
          <Route path="/search" element={
            <ProtectedRoute><SearchResultsPage /></ProtectedRoute>
          } />
          <Route path="/stats" element={
            <ProtectedRoute><StatsPage /></ProtectedRoute>
          } />
          <Route path="/leaderboard" element={
            <ProtectedRoute><LeaderboardPage /></ProtectedRoute>
          } />
          <Route path="/admin" element={
            <ProtectedRoute adminOnly><AdminPage /></ProtectedRoute>
          } />
          <Route path="/admin/analytics" element={
            <ProtectedRoute adminOnly><AdminAnalyticsPage /></ProtectedRoute>
          } />
          <Route path="/notebook" element={
            <ProtectedRoute><NotebookPage /></ProtectedRoute>
          } />
          <Route path="/custom-quiz" element={
            <ProtectedRoute><CustomQuizPage /></ProtectedRoute>
          } />
          <Route path="/analyzer" element={
            <ProtectedRoute><AnalyzerPage /></ProtectedRoute>
          } />
          {process.env.REACT_APP_ADVANCED === "true" && (
            <>
              <Route path="/rag" element={
                <ProtectedRoute><RagPage /></ProtectedRoute>
              } />
              <Route path="/dicom" element={
                <ProtectedRoute><DicomPage /></ProtectedRoute>
              } />
            </>
          )}
          <Route path="/my-notes" element={
            <ProtectedRoute><MyNotesPage /></ProtectedRoute>
          } />
          <Route path="/billing" element={
            <ProtectedRoute><BillingPage /></ProtectedRoute>
          } />
          <Route path="/billing/success" element={
            <ProtectedRoute><BillingSuccessPage /></ProtectedRoute>
          } />
          <Route path="/lerntools" element={
            <ProtectedRoute><LerntoolsPage /></ProtectedRoute>
          } />
          <Route path="/messages" element={
            <ProtectedRoute><MessagingPage /></ProtectedRoute>
          } />
          <Route path="/community" element={
            <ProtectedRoute><CommunityPage /></ProtectedRoute>
          } />
          <Route path="/community/:postId" element={
            <ProtectedRoute><CommunityPostPage /></ProtectedRoute>
          } />
          <Route path="/podcast" element={<DailyPodcastPage />} />
          <Route path="/impressum" element={<ImpressumPage />} />
          <Route path="/datenschutz" element={<PrivacyPage />} />
          <Route path="/agb" element={<TermsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

function App() {
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/service-worker.js').catch(() => {});
    }
  }, []);

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <AppRouter />
            <KeyboardShortcuts />
            <Toaster position="top-center" richColors closeButton dir="ltr" />
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
