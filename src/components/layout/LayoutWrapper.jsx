import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import { useAuth, useLanguage, useTheme } from '../../context/AppContext';
import { Menu, Sun, Moon, Laptop, User, LogOut, MessageSquare } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { LanguageSelector } from '../common/LanguageSelector';

export const LayoutWrapper = ({ children, title = "" }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-950 overflow-hidden font-sans transition-colors duration-150">
      {/* Sidebar for Desktop / Mobile Drawer Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-20 bg-slate-900/50 backdrop-blur-sm lg:hidden"
          onClick={toggleSidebar}
        />
      )}
      
      <Sidebar isOpen={sidebarOpen} toggleSidebar={toggleSidebar} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-4 lg:px-6 shrink-0 transition-colors">
          <div className="flex items-center gap-3">
            <button
              onClick={toggleSidebar}
              className="lg:hidden p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 focus:outline-none"
              aria-label="Open Navigation Menu"
            >
              <Menu className="h-6 w-6" />
            </button>
            <h1 className="text-lg lg:text-xl font-bold font-display text-slate-800 dark:text-white truncate">
              {title}
            </h1>
          </div>

          <div className="flex items-center gap-2 lg:gap-4">
            {/* Language Selector */}
            <div className="hidden sm:block">
              <LanguageSelector border={true} />
            </div>

            {/* Dark Mode Switcher */}
            <div className="flex border border-slate-200 dark:border-slate-800 rounded-lg p-0.5 bg-slate-50 dark:bg-slate-900">
              <button
                onClick={() => setTheme('light')}
                className={`p-1 rounded-md transition-colors ${
                  theme === 'light' 
                    ? 'bg-white dark:bg-slate-800 text-amber-500 shadow-sm' 
                    : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
                }`}
                title={t('themeLight')}
                aria-label="Light Theme"
              >
                <Sun className="h-4 w-4" />
              </button>
              <button
                onClick={() => setTheme('dark')}
                className={`p-1 rounded-md transition-colors ${
                  theme === 'dark' 
                    ? 'bg-white dark:bg-slate-800 text-primary-500 dark:text-primary-400 shadow-sm' 
                    : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
                }`}
                title={t('themeDark')}
                aria-label="Dark Theme"
              >
                <Moon className="h-4 w-4" />
              </button>
              <button
                onClick={() => setTheme('system')}
                className={`p-1 rounded-md transition-colors ${
                  theme === 'system' 
                    ? 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 shadow-sm' 
                    : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
                }`}
                title={t('themeSystem')}
                aria-label="System Theme"
              >
                <Laptop className="h-4 w-4" />
              </button>
            </div>

            {/* Quick Chat Shortcut */}
            <Link 
              to="/chat" 
              className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
              title="Quick Chat with Sahayak"
            >
              <MessageSquare className="h-4.5 w-4.5 text-primary-600 dark:text-primary-400 animate-pulse-subtle" />
            </Link>

            {/* Top User Initials / Profile Shortcut */}
            {user && (
              <Link 
                to="/profile"
                className="h-8.5 w-8.5 rounded-full bg-primary-100 dark:bg-primary-950 flex items-center justify-center text-primary-700 dark:text-primary-300 font-bold border border-primary-200 dark:border-primary-900/60 hover:scale-105 transition-transform"
                title="View Profile"
              >
                {user.name.charAt(0)}
              </Link>
            )}
          </div>
        </header>

        {/* Scrollable Page Body */}
        <main className="flex-1 overflow-y-auto focus:outline-none bg-slate-50 dark:bg-slate-950 p-4 lg:p-6 transition-colors duration-150">
          <div className="max-w-6xl mx-auto space-y-6">
            {children}
            
            {/* Standard Footer Disclaimer inside dashboard wrapper */}
            <footer className="pt-8 pb-4 text-center border-t border-slate-200/60 dark:border-slate-800/60">
              <p className="text-[11px] lg:text-xs text-slate-400 dark:text-slate-500 leading-relaxed max-w-2xl mx-auto">
                {t('chatDisclaimer')}
              </p>
              <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
                <a
                  href={(import.meta.env.VITE_API_URL || "https://sahakar-sahayak-4.onrender.com").replace(/\/$/, "") + "/scoreboard"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold text-primary-700 dark:text-primary-300 bg-primary-50 dark:bg-primary-950/30 border border-primary-200 dark:border-primary-900/60 hover:bg-primary-100 dark:hover:bg-primary-950/50 transition-colors"
                >
                  📊 Accuracy results
                </a>
                <Link to="/admin" className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                  🔒 Admin
                </Link>
              </div>
            </footer>
          </div>
        </main>
      </div>
    </div>
  );
};
export default LayoutWrapper;
