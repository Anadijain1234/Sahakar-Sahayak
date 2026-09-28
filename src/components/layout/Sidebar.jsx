import React from 'react';
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth, useLanguage } from '../../context/AppContext';
import { Logo } from '../common/Logo';
import { 
  LayoutDashboard, 
  MessageSquare, 
  BookOpen, 
  Scale, 
  FileText, 
  Bookmark, 
  History, 
  HelpCircle, 
  Settings, 
  User, 
  LogOut, 
  ShieldAlert,
  BarChart3,
  Lock
} from 'lucide-react';

export const Sidebar = ({ isOpen, toggleSidebar }) => {
  const { user, isGuest, logout } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const menuItems = [
    { to: "/dashboard", label: t('dashboard'), icon: LayoutDashboard },
    { to: "/chat", label: t('askSahayak'), icon: MessageSquare, highlight: true },
    { to: "/guide", label: t('cooperativeGuide'), icon: BookOpen },
    { to: "/resources", label: t('legalResources'), icon: Scale },
    { to: "/documents", label: t('documents'), icon: FileText },
    { to: "/saved", label: t('savedAnswers'), icon: Bookmark, disabledForGuest: true },
    { to: "/history", label: t('chatHistory'), icon: History, disabledForGuest: true },
    { to: "/help", label: t('helpSupport'), icon: HelpCircle },
  ];

  const bottomItems = [
    { to: "/settings", label: t('settings'), icon: Settings },
    { to: "/profile", label: t('profile'), icon: User },
  ];

  return (
    <aside 
      className={`fixed inset-y-0 left-0 z-30 w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col justify-between transform transition-sidebar ${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      } lg:translate-x-0 lg:static lg:h-screen lg:w-64`}
    >
      {/* Sidebar Header */}
      <div className="h-16 px-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
        <Link to="/dashboard">
          <Logo withText={true} />
        </Link>
        <button 
          onClick={toggleSidebar}
          className="lg:hidden p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"
          aria-label="Close Sidebar"
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isDisabled = isGuest && item.disabledForGuest;
          
          if (isDisabled) {
            return (
              <div 
                key={item.to}
                title="Sign in to unlock this feature"
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-300 dark:text-slate-600 cursor-not-allowed select-none text-sm font-medium"
              >
                <Icon className="h-5 w-5" />
                <span>{item.label}</span>
                <span className="ml-auto text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-normal">Locked</span>
              </div>
            );
          }

          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => {
                // Close sidebar on mobile after clicking
                if (window.innerWidth < 1024) toggleSidebar();
              }}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? item.highlight 
                      ? 'bg-primary-600 text-white shadow-md shadow-primary-500/10' 
                      : 'bg-primary-50 dark:bg-primary-950/20 text-primary-600 dark:text-primary-400 font-semibold'
                    : item.highlight
                      ? 'bg-primary-50 dark:bg-primary-950/10 text-primary-700 dark:text-primary-400 hover:bg-primary-100 dark:hover:bg-primary-950/20'
                      : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white'
                }`
              }
            >
              <Icon className={`h-5 w-5 ${item.highlight ? 'animate-pulse-subtle' : ''}`} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}

        {/* Proof & admin: easy for judges to find */}
        <div className="pt-4 mt-3 border-t border-slate-200 dark:border-slate-800 space-y-1">
          <p className="px-3 pb-1 text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">Transparency</p>
          <a
            href={(import.meta.env.VITE_API_URL || "https://sahakar-sahayak-4.onrender.com").replace(/\/$/, "") + "/scoreboard"}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <BarChart3 className="h-5 w-5" />
            <span>Accuracy results</span>
          </a>
          <NavLink
            to="/admin"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary-50 dark:bg-primary-950/20 text-primary-600 dark:text-primary-400 font-semibold'
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`
            }
          >
            <Lock className="h-5 w-5" />
            <span>Admin insights</span>
          </NavLink>
        </div>
      </nav>

      {/* Sidebar Footer */}
      <div className="p-4 border-t border-slate-200 dark:border-slate-800 space-y-3 bg-slate-50/50 dark:bg-slate-900/50">
        <div className="space-y-1">
          {bottomItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => {
                  if (window.innerWidth < 1024) toggleSidebar();
                }}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-slate-150 dark:bg-slate-800 text-slate-900 dark:text-white font-semibold'
                      : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-800 dark:hover:text-slate-200'
                  }`
                }
              >
                <Icon className="h-4.5 w-4.5" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </div>

        {/* User Card */}
        {user && (
          <div className="pt-2 border-t border-slate-200 dark:border-slate-800">
            <div className="flex items-center justify-between gap-2 p-1.5 bg-white dark:bg-slate-800/50 rounded-lg border border-slate-200/60 dark:border-slate-700/50">
              <div className="flex items-center gap-2 overflow-hidden">
                <div className="h-8 w-8 rounded-full bg-primary-100 dark:bg-primary-950 flex items-center justify-center text-primary-700 dark:text-primary-300 font-bold font-display text-sm shrink-0">
                  {user.name.charAt(0)}
                </div>
                <div className="overflow-hidden">
                  <p className="text-xs font-semibold text-slate-700 dark:text-slate-200 truncate leading-none mb-0.5">{user.name}</p>
                  <p className="text-[10px] text-slate-400 truncate leading-none">{isGuest ? "Guest Access" : user.userType}</p>
                </div>
              </div>
              <button 
                onClick={handleLogout}
                className="p-1 rounded text-slate-400 hover:text-red-500 hover:bg-slate-100 dark:hover:bg-slate-800 shrink-0"
                title="Logout"
                aria-label="Logout"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;
