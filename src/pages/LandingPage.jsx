import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/AppContext';
import { Navbar } from '../components/layout/Navbar';
import { FeatureCard } from '../components/common/FeatureCard';
import { 
  MessageSquare, 
  ArrowRight, 
  HelpCircle, 
  Globe, 
  Compass, 
  Users, 
  Scale, 
  FileText, 
  FileCheck, 
  ShieldCheck, 
  Zap 
} from 'lucide-react';

export const LandingPage = () => {
  const { t } = useLanguage();
  const navigate = useNavigate();

  const handleQuickQuestion = (question, category) => {
    navigate('/chat', { state: { initialQuery: question, initialCategory: category } });
  };

  const quickQuestions = [
    { text: "How do I register a cooperative?", category: "Registration" },
    { text: "What are the responsibilities of cooperative members?", category: "Membership" },
    { text: "How is a cooperative committee formed?", category: "Governance" },
    { text: "What documents are required for registration?", category: "Registration" },
    { text: "What rights do cooperative members have?", category: "Membership" },
    { text: "How can a cooperative dispute be handled?", category: "Dispute Resolution" },
  ];

  const features = [
    { title: t('featAiAssistantTitle'), description: t('featAiAssistantDesc'), icon: MessageSquare },
    { title: t('featMultilingualTitle'), description: t('featMultilingualDesc'), icon: Globe },
    { title: t('featLegalInfoTitle'), description: t('featLegalInfoDesc'), icon: Scale },
    { title: t('featDocGuidanceTitle'), description: t('featDocGuidanceDesc'), icon: FileText },
    { title: t('featSourceBasedTitle'), description: t('featSourceBasedDesc'), icon: FileCheck },
    { title: t('featAvailableAnytimeTitle'), description: t('featAvailableAnytimeDesc'), icon: Zap },
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col transition-colors duration-150">
      <Navbar />

      {/* Hero Section */}
      <header className="relative py-16 sm:py-24 overflow-hidden border-b border-slate-200/50 dark:border-slate-800/40 bg-white dark:bg-slate-900 transition-colors">
        {/* Subtle grid pattern background */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:14px_24px] pointer-events-none" />
        
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            
            {/* Hero text content */}
            <div className="lg:col-span-7 space-y-6 text-left">
              
              {/* Trust Indicators */}
              <div className="flex flex-wrap gap-2.5">
                <span className="text-[10px] uppercase font-bold tracking-wider text-primary-650 bg-primary-50 dark:bg-primary-950/20 dark:text-primary-400 border border-primary-100 dark:border-primary-900/40 px-2.5 py-1 rounded-full">
                  ✓ {t('trustIndicatorMultilingual')}
                </span>
                <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-650 bg-emerald-50 dark:bg-emerald-950/20 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-900/40 px-2.5 py-1 rounded-full">
                  ✓ {t('trustIndicatorEasy')}
                </span>
                <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-650 bg-indigo-50 dark:bg-indigo-950/20 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-900/40 px-2.5 py-1 rounded-full">
                  ✓ {t('trustIndicatorAvailable')}
                </span>
              </div>

              {/* Headline */}
              <h1 className="text-3.5xl sm:text-5xl font-black font-display text-slate-850 dark:text-white leading-tight tracking-tight">
                {t('landingTitle')}
              </h1>

              {/* Supporting Text */}
              <p className="text-sm sm:text-base text-slate-550 dark:text-slate-400 leading-relaxed max-w-xl">
                {t('landingSubtitle')}
              </p>

              {/* CTAs */}
              <div className="flex flex-wrap gap-4 pt-2">
                <button
                  onClick={() => navigate('/chat')}
                  className="inline-flex items-center gap-2 px-6 py-3 border border-transparent rounded-xl text-sm font-bold text-white bg-primary-600 hover:bg-primary-700 dark:bg-primary-600 dark:hover:bg-primary-700 shadow-md shadow-primary-500/10 hover:translate-y-[-1px] active:translate-y-0 transition-all cursor-pointer"
                >
                  <MessageSquare className="h-4.5 w-4.5" />
                  <span>{t('ctaAskSahayak')}</span>
                  <ArrowRight className="h-4 w-4" />
                </button>
                
                <button
                  onClick={() => navigate('/guide')}
                  className="inline-flex items-center gap-2 px-6 py-3 border border-slate-200 dark:border-slate-700 rounded-xl text-sm font-bold text-slate-700 dark:text-slate-250 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                >
                  <Compass className="h-4.5 w-4.5 text-slate-400" />
                  <span>{t('ctaExploreGuide')}</span>
                </button>
              </div>

            </div>

            {/* Hero graphic / illustration placeholder */}
            <div className="lg:col-span-5 flex justify-center">
              <div className="w-full max-w-[380px] aspect-[4/3] rounded-3xl bg-slate-50 dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800 shadow-xl shadow-slate-100/50 dark:shadow-none flex flex-col items-center justify-center p-6 relative overflow-hidden group">
                {/* Decorative background glow */}
                <div className="absolute -right-20 -top-20 w-44 h-44 rounded-full bg-primary-600/10 blur-3xl pointer-events-none" />
                
                <div className="h-16 w-16 bg-primary-50 dark:bg-primary-950/40 rounded-2xl flex items-center justify-center text-primary-600 dark:text-primary-400 mb-4 shadow-sm border border-primary-100/40 dark:border-primary-900/30">
                  <ShieldCheck className="h-8 w-8" />
                </div>
                
                <span className="text-sm font-extrabold text-slate-800 dark:text-slate-200 font-display">
                  Platform Verification
                </span>
                <p className="text-[11px] text-slate-400 dark:text-slate-555 text-center mt-1.5 max-w-[240px]">
                  Guided search across municipal bylaws, national cooperative acts, and financial auditing guidelines.
                </p>

                {/* Animated graphic elements */}
                <div className="flex gap-2.5 mt-5">
                  <div className="h-7 w-7 rounded-lg bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400 border border-emerald-100/40 flex items-center justify-center shadow-sm">
                    <Users className="h-4 w-4" />
                  </div>
                  <div className="h-7 w-7 rounded-lg bg-indigo-50 dark:bg-indigo-950/20 text-indigo-600 dark:text-indigo-400 border border-indigo-100/40 flex items-center justify-center shadow-sm">
                    <Scale className="h-4 w-4" />
                  </div>
                  <div className="h-7 w-7 rounded-lg bg-amber-50 dark:bg-amber-950/20 text-amber-600 dark:text-amber-400 border border-amber-100/40 flex items-center justify-center shadow-sm">
                    <FileText className="h-4 w-4" />
                  </div>
                </div>

              </div>
            </div>

          </div>
        </div>
      </header>

      {/* Quick Questions Section */}
      <section className="py-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-8">
        <div className="space-y-2">
          <h2 className="text-xl sm:text-2xl font-black font-display text-slate-850 dark:text-white">
            {t('whatCanHelpWith')}
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Click any question to open the AI assistant and get immediate responses.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 max-w-5xl mx-auto">
          {quickQuestions.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleQuickQuestion(q.text, q.category)}
              className="flex items-start gap-3 p-4 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl text-left hover:border-primary-400 dark:hover:border-primary-900/60 hover:shadow-md transition-all group cursor-pointer"
            >
              <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-950 text-slate-400 group-hover:text-primary-600 dark:group-hover:text-primary-400 shrink-0">
                <HelpCircle className="h-4 w-4" />
              </div>
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-350 leading-snug pt-1 flex-1 group-hover:text-slate-900 dark:group-hover:text-white">
                {q.text}
              </span>
              <ArrowRight className="h-4 w-4 text-slate-300 group-hover:text-primary-600 dark:group-hover:text-primary-400 group-hover:translate-x-0.5 shrink-0 self-center transition-all" />
            </button>
          ))}
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-white dark:bg-slate-900 border-t border-b border-slate-200/50 dark:border-slate-800/40 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-12">
          
          <div className="space-y-2">
            <h2 className="text-xl sm:text-2xl font-black font-display text-slate-850 dark:text-white">
              {t('featuresTitle')}
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-lg mx-auto">
              Empowering cooperative members with natural language AI governance assistants and official legal archives.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {features.map((feat, idx) => (
              <FeatureCard 
                key={idx}
                title={feat.title}
                description={feat.description}
                icon={feat.icon}
              />
            ))}
          </div>

        </div>
      </section>

      {/* Landing Footer Disclaimer */}
      <footer className="mt-auto py-10 bg-slate-50 dark:bg-slate-950 transition-colors text-center border-t border-slate-200/40 dark:border-slate-900/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-4">
          <p className="text-xs text-slate-400 dark:text-slate-500 leading-relaxed max-w-2xl mx-auto">
            {t('chatDisclaimer')}
          </p>
          <a
            href={(import.meta.env.VITE_API_URL || "https://sahakar-sahayak-4.onrender.com").replace(/\/$/, "") + "/scoreboard"}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block text-xs font-semibold text-primary-600 dark:text-primary-400 hover:underline"
          >
            📊 Accuracy tested on real questions from official documents: see our live scoreboard
          </a>
          <Link to="/admin" className="inline-block ml-3 text-xs font-semibold text-slate-500 dark:text-slate-400 hover:underline">
            🔒 Admin insights
          </Link>
          <div className="text-[10px] text-slate-450 dark:text-slate-650">
            &copy; {new Date().getFullYear()} Sahakar Sahayak. Platform developed for multilingual citizen support. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
};
export default LandingPage;
