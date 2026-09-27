import React, { useState } from 'react';
import {
  CheckCircle2, AlertCircle, Info, FileText, ExternalLink,
  Volume2, Send, Search, ChevronDown, ChevronUp,
} from 'lucide-react';

// Short, farmer-friendly labels in the language chosen on the website.
const LABELS = {
  en: {
    verified: 'Verified from official document',
    partial: 'Partly verified · please check the source',
    general: 'General guidance · please confirm with your cooperative office',
    page: 'Page',
    open: 'Open',
    listen: 'Read aloud',
    playing: 'Playing…',
    share: 'Share',
  },
  hi: {
    verified: 'आधिकारिक दस्तावेज़ से सत्यापित',
    partial: 'आंशिक रूप से सत्यापित · कृपया स्रोत देखें',
    general: 'सामान्य जानकारी · कृपया अपनी सहकारी समिति कार्यालय से पुष्टि करें',
    page: 'पृष्ठ',
    open: 'खोलें',
    listen: 'सुनें',
    playing: 'चल रहा है…',
    share: 'शेयर करें',
  },
  kn: {
    verified: 'ಅಧಿಕೃತ ದಾಖಲೆಯಿಂದ ಪರಿಶೀಲಿಸಲಾಗಿದೆ',
    partial: 'ಭಾಗಶಃ ಪರಿಶೀಲಿಸಲಾಗಿದೆ · ದಯವಿಟ್ಟು ಮೂಲವನ್ನು ನೋಡಿ',
    general: 'ಸಾಮಾನ್ಯ ಮಾರ್ಗದರ್ಶನ · ದಯವಿಟ್ಟು ನಿಮ್ಮ ಸಹಕಾರ ಸಂಘದ ಕಚೇರಿಯಲ್ಲಿ ಖಚಿತಪಡಿಸಿಕೊಳ್ಳಿ',
    page: 'ಪುಟ',
    open: 'ತೆರೆಯಿರಿ',
    listen: 'ಕೇಳಿ',
    playing: 'ಪ್ಲೇ ಆಗುತ್ತಿದೆ…',
    share: 'ಹಂಚಿಕೊಳ್ಳಿ',
  },
};

const TRUST_STYLE = {
  verified: {
    Icon: CheckCircle2,
    box: 'bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-950/30 dark:border-emerald-900/60 dark:text-emerald-300',
  },
  partial: {
    Icon: AlertCircle,
    box: 'bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/30 dark:border-amber-900/60 dark:text-amber-300',
  },
  general: {
    Icon: Info,
    box: 'bg-sky-50 border-sky-200 text-sky-800 dark:bg-sky-950/30 dark:border-sky-900/60 dark:text-sky-300',
  },
};

// Works for new answers (trust_level) and for older saved chats (answer_source only).
const getTrustLevel = (message) => {
  if (message.trust_level) return message.trust_level;
  if (message.answer_source === 'documents') return 'partial';
  if (message.answer_source === 'general') return 'general';
  return null;
};

const fmt = (value) => (typeof value === 'number' ? `${value.toFixed(2)}%` : '—');

const ScoreBar = ({ label, value, hint }) => (
  <div>
    <div className="flex justify-between text-[11px] mb-1">
      <span className="font-semibold text-slate-600 dark:text-slate-300">{label}</span>
      <span className="font-mono font-bold text-slate-800 dark:text-slate-100">{fmt(value)}</span>
    </div>
    <div className="h-1.5 w-full rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
      <div
        className="h-full rounded-full bg-primary-600 dark:bg-primary-400"
        style={{ width: `${Math.max(0, Math.min(100, typeof value === 'number' ? value : 0))}%` }}
      />
    </div>
    {hint && <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">{hint}</p>}
  </div>
);

const Stat = ({ label, value }) => (
  <div className="rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 px-2.5 py-2">
    <p className="text-[10px] uppercase tracking-wide text-slate-400 dark:text-slate-500">{label}</p>
    <p className="text-xs font-mono font-bold text-slate-800 dark:text-slate-100">{value}</p>
  </div>
);

const SearchReport = ({ report }) => {
  const meaningOn = report.meaning_available && typeof report.meaning_score === 'number';
  return (
    <div className="mt-3 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-3.5 animate-message-appear">
      <div className="flex items-baseline justify-between">
        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Search report</p>
        <p className="text-sm font-mono font-black text-primary-700 dark:text-primary-300">
          {fmt(report.final_confidence)} <span className="text-[10px] font-sans font-semibold text-slate-400">final confidence</span>
        </p>
      </div>

      <div className="space-y-2.5">
        <ScoreBar label="Keyword match (BM25)" value={report.keyword_score} hint="Important words of the question found exactly" />
        <ScoreBar label="Spelling-tolerant match" value={report.spelling_score} hint="Word parts found, so kisan ≈ kishan" />
        {meaningOn ? (
          <ScoreBar label="Meaning match (Cloudflare bge-m3)" value={report.meaning_score} hint="Same meaning, even with different words" />
        ) : (
          <p className="text-[11px] text-slate-400 dark:text-slate-500">Meaning match: not available for this search</p>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <Stat label="Pieces searched" value={`${(report.pieces_searched || 0).toLocaleString('en-IN')} / ${report.pdfs_searched || 0} PDFs`} />
        <Stat label="Candidates" value={report.candidates_compared ?? '—'} />
        <Stat label="Search time" value={typeof report.search_time_ms === 'number' ? `${report.search_time_ms.toFixed(2)} ms` : '—'} />
        <Stat label="Total time" value={typeof report.total_time_ms === 'number' ? `${(report.total_time_ms / 1000).toFixed(2)} s` : '—'} />
      </div>

      {report.top_sources && report.top_sources.length > 0 && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-1.5">Top matching passages</p>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="text-left text-slate-400 dark:text-slate-500">
                  <th className="font-semibold pb-1 pr-2">Document</th>
                  <th className="font-semibold pb-1 pr-2">Page</th>
                  <th className="font-semibold pb-1 pr-2 text-right">Keyword</th>
                  <th className="font-semibold pb-1 pr-2 text-right">Meaning</th>
                  <th className="font-semibold pb-1 text-right">Final</th>
                </tr>
              </thead>
              <tbody className="font-mono text-slate-700 dark:text-slate-300">
                {report.top_sources.map((src, i) => (
                  <tr key={`${src.document}-${src.page}-${i}`} className="border-t border-slate-200/70 dark:border-slate-800/70">
                    <td className="py-1 pr-2 font-sans max-w-[160px] truncate">
                      <a href={src.link} target="_blank" rel="noopener noreferrer" className="hover:underline" title={src.document}>
                        {src.document}
                      </a>
                    </td>
                    <td className="py-1 pr-2">{src.page ?? '—'}</td>
                    <td className="py-1 pr-2 text-right">{fmt(src.keyword)}</td>
                    <td className="py-1 pr-2 text-right">{fmt(src.meaning)}</td>
                    <td className="py-1 text-right font-bold">{fmt(src.final)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!report.used_documents && (
        <p className="text-[11px] text-slate-500 dark:text-slate-400">
          No passage was strong enough to rely on, so the answer uses general knowledge.
        </p>
      )}
    </div>
  );
};

export const AnswerFooter = ({ message, question, language = 'en', onReadAloud, isPlayingAudio }) => {
  const [showReport, setShowReport] = useState(false);
  const L = LABELS[language] || LABELS.en;
  const trust = getTrustLevel(message);
  const style = trust ? TRUST_STYLE[trust] : null;
  const best = message.sources && message.sources.length > 0 ? message.sources[0] : null;
  const report = message.search_report;
  const showSource = best && (trust === 'verified' || trust === 'partial');

  const handleShare = async () => {
    const lines = ['🌾 Sahakar Sahayak', ''];
    if (question) lines.push(`❓ ${question}`, '');
    lines.push(`✅ ${message.text}`);
    if (showSource) {
      lines.push('', `📄 ${best.documentName}${best.page ? ` (${L.page} ${best.page})` : ''}`);
      if (best.link) lines.push(best.link);
    }
    lines.push('', `${window.location.origin}`);
    const text = lines.join('\n');

    const isPhone = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    if (isPhone && navigator.share) {
      try {
        await navigator.share({ title: 'Sahakar Sahayak', text });
        return;
      } catch (err) {
        if (err && err.name === 'AbortError') return; // user closed the share menu
      }
    }
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener,noreferrer');
  };

  const btn = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors disabled:opacity-50';
  const btnIdle = 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800';

  return (
    <div className="mt-4 pt-3.5 border-t border-slate-200/80 dark:border-slate-800/80 space-y-3">
      {/* 1. Trust line (+ best source) */}
      {style && (
        <div className={`flex flex-wrap items-center gap-x-3 gap-y-1.5 px-3 py-2 rounded-xl border text-xs font-semibold ${style.box}`}>
          <span className="inline-flex items-center gap-1.5">
            <style.Icon className="h-4 w-4 shrink-0" />
            {L[trust]}
          </span>
          {showSource && (
            <a
              href={best.link || undefined}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-medium underline decoration-dotted underline-offset-2 hover:decoration-solid min-w-0"
              title={best.documentName}
            >
              <FileText className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate max-w-[220px]">{best.documentName}</span>
              {best.page ? <span className="shrink-0">· {L.page} {best.page}</span> : null}
              <span className="shrink-0">· {L.open}</span>
              <ExternalLink className="h-3 w-3 shrink-0" />
            </a>
          )}
        </div>
      )}

      {/* 2. Actions */}
      <div className="flex flex-wrap items-center gap-2">
        {onReadAloud && (
          <button onClick={() => onReadAloud(message.text)} disabled={isPlayingAudio} className={`${btn} ${btnIdle}`}>
            <Volume2 className="h-3.5 w-3.5" />
            {isPlayingAudio ? L.playing : L.listen}
          </button>
        )}
        {trust && trust !== 'refused' && trust !== 'error' && (
          <button onClick={handleShare} className={`${btn} ${btnIdle}`}>
            <Send className="h-3.5 w-3.5" />
            {L.share}
          </button>
        )}
        {report && trust && trust !== 'refused' && (
          <button
            onClick={() => setShowReport((v) => !v)}
            className={`${btn} ${showReport ? 'border-primary-300 text-primary-700 bg-primary-50 dark:bg-primary-950/30 dark:text-primary-300 dark:border-primary-800' : btnIdle}`}
            aria-expanded={showReport}
          >
            <Search className="h-3.5 w-3.5" />
            Search report
            {showReport ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>

      {/* 3. Detailed report (hidden until tapped) */}
      {showReport && report && <SearchReport report={report} />}
    </div>
  );
};

export default AnswerFooter;
