let splashShownGlobal = false;
import { useState, useEffect, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import { API, useAuth } from "@/App";
import { fetchWithTimeout } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Scissors, Heart, Baby, Ambulance, Eye, Fingerprint, Ear, HeartPulse, Brain, Star, Activity,
  ArrowRight, BookOpen, Clock, CheckCircle,
  Target, Shield, FileText, Bot, Layers, Pill,
} from "lucide-react";
import { toast } from "sonner";


const iconMap = {
  Scissors, Heart, Baby, Ambulance, Eye, Fingerprint, Ear, HeartPulse, Brain, Star, Activity, Pill,
};


/* Splash */
const SplashOverlay = ({ onDone }) => {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    const t1 = setTimeout(() => setPhase(1), 80);
    const t2 = setTimeout(() => setPhase(2), 1000);
    const t3 = setTimeout(() => onDone(), 1600);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [onDone]);


  return (
    <div className={`fixed inset-0 z-[100] flex items-center justify-center transition-all duration-500 ${phase >= 2 ? "opacity-0 pointer-events-none" : "opacity-100"}`} style={{ background: "linear-gradient(135deg, #06081a 0%, #0a1128 40%, #06081a 100%)" }} data-testid="splash-overlay">
      <div className="text-center relative">
        <div className={`transition-all duration-600 ${phase >= 1 ? "opacity-100 scale-100" : "opacity-0 scale-75"}`}>
          <img src="/logo-elite.png" alt="Prep Academy" className="w-44 h-44 mx-auto object-contain" style={{ filter: "drop-shadow(0 0 40px rgba(201,168,76,0.25))" }} />
        </div>
      </div>
    </div>
  );
};


/* Section label */
const SectionLabel = ({ number, text }) => (
  <div className="flex items-center gap-3 mb-6">
    <span className="text-xs font-mono tracking-widest" style={{ color: '#c9a84c' }}>{number}</span>
    <div className="w-12 h-px" style={{ background: 'rgba(201,168,76,0.3)' }} />
    <span className="text-xs tracking-[0.2em] uppercase text-white/40">{text}</span>
  </div>
);


export default function HomePage() {
  const [specialties, setSpecialties] = useState([]);
  const [examTypes, setExamTypes] = useState([]);
  const [selectedExam, setSelectedExam] = useState(null);
  const [specialtiesLoading, setSpecialtiesLoading] = useState(true);
  const [examTypesLoading, setExamTypesLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const { user, token } = useAuth();
  const [requestingAccess, setRequestingAccess] = useState(false);
  const [showSplash, setShowSplash] = useState(() => {
    if (sessionStorage.getItem("splashSeen")) return false;
    sessionStorage.setItem("splashSeen", "1");
    return true;
  });
  const handleSplashDone = useCallback(() => { setShowSplash(false); }, []);


  const loadHomepageData = useCallback(() => {
    let cancelled = false;
    setSpecialtiesLoading(true);
