import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import axios from "axios";
import { API, useAuth } from "@/App";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH

export default function AuthCallback() {
  const navigate = useNavigate();
  const hasProcessed = useRef(false);
  const { loginWithGoogle } = useAuth();

  useEffect(() => {
    // Use useRef to prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      try {
        // Get session_id from URL hash
        const hash = window.location.hash;
        const sessionId = hash.split("session_id=")[1]?.split("&")[0];

        if (!sessionId) {
          console.error("No session_id found");
          navigate("/login");
          return;
        }

        // Exchange session_id for session data
        const response = await axios.post(
          `${API}/auth/google/callback`,
          { session_id: sessionId },
          { withCredentials: true }
        );

        if (response.data.user && response.data.token) {
          // Save the token and user data
          loginWithGoogle(response.data.user, response.data.token);
          
          // Clear the hash and redirect to home
          window.history.replaceState(null, "", "/");
          navigate("/", { replace: true });
        } else {
          throw new Error("No user data received");
        }
      } catch (error) {
        console.error("Auth callback error:", error);
        navigate("/login");
      }
    };

    processAuth();
  }, [navigate, loginWithGoogle]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
        <p className="text-lg text-muted-foreground">جاري تسجيل الدخول...</p>
      </div>
    </div>
  );
}
