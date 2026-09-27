import React from 'react';
import { useLanguage, useAppData } from '../../context/AppContext';
import { Logo } from '../common/Logo';
import { Bookmark, BookmarkCheck, CheckSquare, AlertTriangle, Scale, ExternalLink } from 'lucide-react';

export const ChatMessage = ({ message, conversationCategory = "General Guidance", footer = null }) => {
  const { t } = useLanguage();
  const { toggleSaveAnswer, isAnswerSaved } = useAppData();
  const isUser = message.sender === 'user';

  // Check if this specific assistant response can be bookmarked
  const canBookmark = !isUser && message.text;
  const isSaved = canBookmark ? isAnswerSaved(message.text) : false;

  const handleBookmark = () => {
    // Collect context to save
    const fullAnswerText = message.text;
    toggleSaveAnswer(
      fullAnswerText,
      fullAnswerText, 
      conversationCategory,
      message.sources || []
    );
  };

  const formatTime = (timeString) => {
    if (!timeString) return "";
    const date = new Date(timeString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-4 sm:mb-6 animate-message-appear">
        <div className="max-w-[80%] sm:max-w-[70%]">
          <div className="bg-primary-600 text-white rounded-2xl rounded-tr-none px-4 py-3 shadow-md shadow-primary-600/10">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.text}</p>
          </div>
          <div className="text-right mt-1.5 px-1">
            <span className="text-[10px] text-slate-400 dark:text-slate-500 font-medium">
              {formatTime(message.time)}
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 sm:gap-4 mb-6 sm:mb-8 animate-message-appear">
      {/* Sahayak Brand Avatar */}
      <div className="h-9 w-9 rounded-xl bg-primary-100 dark:bg-primary-950 flex items-center justify-center shrink-0 border border-primary-200 dark:border-primary-900/60 shadow-sm">
        <Logo className="h-5 w-5" />
      </div>

      {/* Message Bubble Wrapper */}
      <div className="flex-1 min-w-0 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl rounded-tl-none p-4 shadow-sm relative group">
        
        {/* Assistant Header & Actions */}
        <div className="flex justify-between items-center mb-2.5">
          <span className="text-xs font-bold text-slate-800 dark:text-slate-200 font-display">
            Sahayak
          </span>
          
          {canBookmark && (
            <button
              onClick={handleBookmark}
              className={`p-1.5 rounded-lg border transition-colors ${
                isSaved
                  ? 'border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400'
                  : 'border-slate-200 dark:border-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
              title={isSaved ? "Saved" : "Save Answer"}
              aria-label={isSaved ? "Saved Answer" : "Save Answer"}
            >
              {isSaved ? (
                <BookmarkCheck className="h-4.5 w-4.5" />
              ) : (
                <Bookmark className="h-4.5 w-4.5" />
              )}
            </button>
          )}
        </div>

        {/* Main Text Content */}
        <div className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
          {message.text}
        </div>

        {/* 1. Bullet Steps Section */}
        {message.steps && message.steps.length > 0 && (
          <ol className="mt-4 space-y-2.5 list-decimal pl-4.5 text-sm text-slate-700 dark:text-slate-300 font-medium">
            {message.steps.map((step, idx) => (
              <li key={idx} className="pl-1 leading-relaxed">{step}</li>
            ))}
          </ol>
        )}

        {/* 2. Documents required checklists */}
        {message.documents && message.documents.length > 0 && (
          <div className="mt-4.5 p-3.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
            <h5 className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5 mb-2.5">
              <CheckSquare className="h-4 w-4 text-primary-600 dark:text-primary-400" />
              Required Checklist
            </h5>
            <ul className="space-y-2">
              {message.documents.map((doc, idx) => (
                <li key={idx} className="flex gap-2 items-start text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                  <span className="text-emerald-500 font-bold">✓</span>
                  <span>{doc}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 3. Important Takeaways/Notes */}
        {message.notes && message.notes.length > 0 && (
          <div className="mt-4 p-3.5 bg-amber-50 dark:bg-amber-950/10 border border-amber-200 dark:border-amber-900/40 rounded-xl text-xs text-amber-850 dark:text-amber-300 flex items-start gap-2.5 leading-relaxed">
            <AlertTriangle className="h-4.5 w-4.5 text-amber-500 shrink-0 mt-0.5" />
            <div>
              {message.notes.map((note, idx) => (
                <p key={idx}>{note}</p>
              ))}
            </div>
          </div>
        )}

        {/* 4. Relevant legal provisions */}
        {message.provisions && message.provisions.length > 0 && (
          <div className="mt-4 p-3.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-600 dark:text-slate-400 flex items-start gap-2.5 leading-relaxed">
            <Scale className="h-4.5 w-4.5 text-slate-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-700 dark:text-slate-350 mb-1">Legal Provisions:</p>
              {message.provisions.map((prov, idx) => (
                <p key={idx} className="italic">“{prov}”</p>
              ))}
            </div>
          </div>
        )}

        {/* 5. Trust line, source, actions and search report (see AnswerFooter.jsx) */}
        {footer}

        {/* Footer timestamp */}
        <div className="mt-3.5 flex items-center justify-between">
          <span className="text-[10px] text-slate-400 dark:text-slate-500 font-medium">
            {formatTime(message.time || message.timestamp)}
          </span>
          <span className="text-[10px] text-slate-350 dark:text-slate-600 font-medium italic">
            Cooperative Governance Helper
          </span>
        </div>

      </div>
    </div>
  );
};
export default ChatMessage;
