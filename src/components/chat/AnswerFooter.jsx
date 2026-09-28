import React, { useState, useEffect } from 'react';
import { chatService } from '../../services/chatService';
import {
  CheckCircle2, AlertCircle, Info, FileText, ExternalLink,
  Volume2, Send, Search, ChevronDown, ChevronUp, Phone, Scale, BarChart3, AlertTriangle,
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
    help: 'Need more help? Talk to a person',
    check: 'AI check',
    checking: 'Other AIs are checking this answer…',
    good: 'Good', partly: 'Partly right', poor: 'Needs checking',
    scorecard: 'Scorecard',
    checkWarn: 'AI check found problems · please verify with the source',
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
    help: 'और मदद चाहिए? किसी व्यक्ति से बात करें',
    check: 'AI जाँच',
    checking: 'दूसरे AI इस उत्तर की जाँच कर रहे हैं…',
    good: 'सही', partly: 'आंशिक रूप से सही', poor: 'जाँच ज़रूरी',
    scorecard: 'स्कोरकार्ड',
    checkWarn: 'AI जाँच में गड़बड़ी मिली · कृपया स्रोत से पुष्टि करें',
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
    help: 'ಇನ್ನಷ್ಟು ಸಹಾಯ ಬೇಕೇ? ವ್ಯಕ್ತಿಯೊಂದಿಗೆ ಮಾತನಾಡಿ',
    check: 'AI ಪರಿಶೀಲನೆ',
    checking: 'ಬೇರೆ AI ಗಳು ಈ ಉತ್ತರವನ್ನು ಪರಿಶೀಲಿಸುತ್ತಿವೆ…',
    good: 'ಸರಿ', partly: 'ಭಾಗಶಃ ಸರಿ', poor: 'ಪರಿಶೀಲನೆ ಅಗತ್ಯ',
    scorecard: 'ಸ್ಕೋರ್‌ಕಾರ್ಡ್',
    checkWarn: 'AI ಪರಿಶೀಲನೆಯಲ್ಲಿ ಸಮಸ್ಯೆ ಕಂಡುಬಂದಿದೆ · ದಯವಿಟ್ಟು ಮೂಲದಿಂದ ಖಚಿತಪಡಿಸಿಕೊಳ್ಳಿ',
  },
};

// Which AI wrote the answer (Sarvam first, then backups -- see backend/services/llm_chain.py)
const AI_NAMES = {
  sarvam: 'Sarvam AI',
  groq: 'Groq (backup AI)',
  cloudflare: 'Cloudflare (backup AI)',
  search_only: 'Search only (AI unavailable)',
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

const WARN_BOX = 'bg-amber-50 border-amber-300 text-amber-800 dark:bg-amber-950/30 dark:border-amber-900/60 dark:text-amber-300';

// Works for new answers (trust_level) and for older saved chats (answer_source only).
const getTrustLevel = (message) => {
  if (message.trust_level) return message.trust_level;
  if (message.answer_source === 'documents') return 'partial';
  if (message.answer_source === 'general') return 'general';
  return null;
};

const fmt = (value) => (typeof value === 'number' ? `${value.toFixed(2)}%` : '—');

// ---- Live AI check (other AIs grade the answer) ----
const CHECK_STORE = 'sahakar_ai_checks';
const readCheck = (rid) => {
  try { return (JSON.parse(localStorage.getItem(CHECK_STORE) || '{}') || {})[rid] || null; } catch { return null; }
};
const saveCheck = (rid, data) => {
  try {
    const all = JSON.parse(localStorage.getItem(CHECK_STORE) || '{}') || {};
    all[rid] = data;
    const keys = Object.keys(all);
    if (keys.length > 100) keys.slice(0, keys.length - 100).forEach((k) => delete all[k]);
    localStorage.setItem(CHECK_STORE, JSON.stringify(all));
  } catch { /* storage unavailable: the check just won't survive a refresh */ }
};
const inFlight = {};   // one check per answer, even if the message re-renders
const runCheck = (rid) => {
  if (!inFlight[rid]) {
    inFlight[rid] = chatService.judgeAnswer(rid).then((data) => {
      if (data && data.status === 'ok') saveCheck(rid, data);
      return data;
    });
  }
  return inFlight[rid];
};
const VERDICT_STYLE = {
  good: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300',
  partly: 'bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300',
  poor: 'bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-300',
};
const JUDGE_SHORT = { groq: 'Groq', cloudflare: 'Cloudflare', sarvam: 'Sarvam' };

const AiCheck = ({ check }) => (
  <div className="rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-2.5 space-y-2">
    <div className="flex items-baseline justify-between gap-2">
      <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Checked by other AIs</p>
      {typeof check.score === 'number' && (
        <p className="text-sm font-mono font-black text-slate-800 dark:text-slate-100">{check.score}<span className="text-[10px] text-slate-400">/100</span></p>
      )}
    </div>
    {(check.judges || []).map((j) => (
      <div key={j.judge} className="text-[11px] border-t border-slate-100 dark:border-slate-800 pt-1.5">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="font-semibold text-slate-700 dark:text-slate-200">{j.name}</span>
          {j.status === 'ok' ? (
            <>
              <span className={`px-1.5 py-0.5 rounded font-bold ${VERDICT_STYLE[j.grade] || ''}`}>{j.grade}</span>
              <span className="text-slate-500 dark:text-slate-400">
                Faithful to documents {j.faithful ?? '—'}/10 · Answers the question {j.helpful ?? '—'}/10
                {j.language_ok === true ? ' · Right language ✓' : j.language_ok === false ? ' · Wrong language ✗' : ''}
              </span>
            </>
          ) : (
            <span className="text-slate-400">{j.status === 'limit' ? 'daily check limit reached' : 'not available right now'}</span>
          )}
        </div>
        {j.reason && <p className="text-slate-500 dark:text-slate-400 italic mt-0.5">"{j.reason}"</p>}
      </div>
    ))}
    <p className="text-[10px] text-slate-400">An AI never checks its own answer. Other AIs compare it with the official passages.</p>
  </div>
);

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

const SearchReport = ({ report, check, title }) => {
  const meaningOn = report.meaning_available && typeof report.meaning_score === 'number';
  return (
    <div className="mt-3 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-3.5 animate-message-appear">
      <div className="flex items-baseline justify-between">
        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">{title}</p>
        <p className="text-sm font-mono font-black text-primary-700 dark:text-primary-300">
          {fmt(report.final_confidence)} <span className="text-[10px] font-sans font-semibold text-slate-400">final confidence</span>
        </p>
      </div>

      {check && check.judges && <AiCheck check={check} />}

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

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        <Stat label="Translated by" value={AI_NAMES[report.translated_by] || (report.translated_by ? report.translated_by : 'Not needed')} />
        <Stat label="Answered by" value={AI_NAMES[report.answered_by] || report.answered_by || '—'} />
        <Stat label="Request ID" value={report.request_id || '—'} />
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

// Mandi prices (backend/services/mandi_prices.py) -- only ever sent for price questions.
const PRICE_LABELS = {
  en: { title: 'Latest mandi prices', unit: '₹ per quintal', market: 'Market', min: 'Min', modal: 'Usual', max: 'Max', asOf: 'As of', source: 'Source', via: 'via GitHub', check: 'Check mandi prices',
    official: 'Official mandi prices (AGMARKNET)', today: 'today', yesterday: 'yesterday', daysOld: (n) => `${n} days old`, mayChange: 'prices may have changed' },
  hi: { title: 'ताज़ा मंडी भाव', unit: '₹ प्रति क्विंटल', market: 'मंडी', min: 'न्यूनतम', modal: 'आम भाव', max: 'अधिकतम', asOf: 'तारीख', source: 'स्रोत', via: 'GitHub द्वारा', check: 'मंडी भाव देखें',
    official: 'आधिकारिक मंडी भाव (AGMARKNET)', today: 'आज', yesterday: 'कल', daysOld: (n) => `${n} दिन पुराने`, mayChange: 'भाव बदल चुके हो सकते हैं' },
  kn: { title: 'ಇತ್ತೀಚಿನ ಮಾರುಕಟ್ಟೆ ಬೆಲೆ', unit: '₹ ಪ್ರತಿ ಕ್ವಿಂಟಾಲ್', market: 'ಮಾರುಕಟ್ಟೆ', min: 'ಕನಿಷ್ಠ', modal: 'ಸಾಮಾನ್ಯ', max: 'ಗರಿಷ್ಠ', asOf: 'ದಿನಾಂಕ', source: 'ಮೂಲ', via: 'GitHub ಮೂಲಕ', check: 'ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ನೋಡಿ',
    official: 'ಅಧಿಕೃತ ಮಾರುಕಟ್ಟೆ ಬೆಲೆ (AGMARKNET)', today: 'ಇಂದು', yesterday: 'ನಿನ್ನೆ', daysOld: (n) => `${n} ದಿನ ಹಳೆಯದು`, mayChange: 'ಬೆಲೆ ಬದಲಾಗಿರಬಹುದು' },
  ne: { title: 'पछिल्लो मण्डी भाउ', unit: '₹ प्रति क्विन्टल', market: 'मण्डी', min: 'न्यूनतम', modal: 'सामान्य', max: 'अधिकतम', asOf: 'मिति', source: 'स्रोत', via: 'GitHub मार्फत', check: 'मण्डी भाउ हेर्नुहोस्',
    official: 'आधिकारिक मण्डी भाउ (AGMARKNET)', today: 'आज', yesterday: 'हिजो', daysOld: (n) => `${n} दिन पुरानो`, mayChange: 'भाउ फेरिएको हुन सक्छ' },
};

const rupees = (n) => (typeof n === 'number' && Number.isFinite(n) ? Math.round(n).toLocaleString('en-IN') : '—');

// How old the prices are: '25/09/2026' -> { days: 3, day: Date } (days counted on the phone's calendar)
const priceAge = (ddmmyyyy) => {
  const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(String(ddmmyyyy || '').trim());
  if (!m) return null;
  const day = new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]));
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return { days: Math.max(0, Math.round((today - day) / 86400000)), day };
};
const DATE_LOCALE = { en: 'en-IN', hi: 'hi-IN', kn: 'kn-IN', ne: 'ne-NP' };
const ageText = (age, P) => (!age ? '' : age.days === 0 ? P.today : age.days === 1 ? P.yesterday : P.daysOld(age.days));

// Price answers: "Official mandi prices (AGMARKNET) · today" (green) or "· 25 Sep, 3 days old · prices may have changed" (amber)
const priceBadgeText = (prices, language) => {
  const P = PRICE_LABELS[language] || PRICE_LABELS.en;
  const age = priceAge(prices.date);
  if (!age) return { text: P.official, fresh: false };
  if (age.days <= 1) return { text: `${P.official} · ${ageText(age, P)}`, fresh: true };
  let shown = prices.date;
  try { shown = age.day.toLocaleDateString(DATE_LOCALE[language] || 'en-IN', { day: 'numeric', month: 'short' }); } catch { /* keep dd/mm/yyyy */ }
  return { text: `${P.official} · ${shown}, ${ageText(age, P)} · ${P.mayChange}`, fresh: false };
};

const PricesCard = ({ prices, language }) => {
  const P = PRICE_LABELS[language] || PRICE_LABELS.en;
  const rows = Array.isArray(prices.records) ? prices.records : [];
  const portal = (Array.isArray(prices.links) && prices.links[0]) || { label: 'AGMARKNET (Govt. of India)', url: 'https://agmarknet.gov.in/' };
  const linkCls = 'font-semibold text-primary-700 dark:text-primary-300 hover:underline inline-flex items-center gap-0.5';

  // Price asked, but no fresh prices for it: just the official portal link
  if (prices.status !== 'ok' || rows.length === 0) {
    return (
      <p className="text-xs text-slate-600 dark:text-slate-300 px-1 flex flex-wrap items-center gap-x-1.5 gap-y-1">
        <BarChart3 className="h-3.5 w-3.5 text-emerald-600" />
        <span className="font-semibold">{P.check}:</span>
        <a href={portal.url} target="_blank" rel="noopener noreferrer" className={linkCls}>
          {portal.label} <ExternalLink className="h-3 w-3" />
        </a>
      </p>
    );
  }

  return (
    <div className="px-3 py-2.5 rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/60 dark:bg-emerald-950/20">
      <p className="text-[11px] font-bold text-emerald-800 dark:text-emerald-300 mb-1.5 flex flex-wrap items-center gap-x-1.5">
        <BarChart3 className="h-3.5 w-3.5" />
        {P.title} · {prices.commodity}
        <span className="font-medium text-emerald-700/70 dark:text-emerald-400/70">({P.unit})</span>
      </p>
      <table className="w-full text-xs text-slate-700 dark:text-slate-300">
        <thead>
          <tr className="text-[10px] uppercase tracking-wide text-slate-500 dark:text-slate-400">
            <th className="text-left font-semibold pb-1">{P.market}</th>
            <th className="text-right font-semibold pb-1 pl-2">{P.min}</th>
            <th className="text-right font-semibold pb-1 pl-2">{P.modal}</th>
            <th className="text-right font-semibold pb-1 pl-2">{P.max}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={`${r.market}-${r.variety}-${i}`} className="border-t border-emerald-100 dark:border-emerald-900/40">
              <td className="py-1 pr-1">
                <span className="font-semibold">{r.market}</span>
                <span className="block text-[10px] text-slate-500 dark:text-slate-400">
                  {[r.district, r.variety && r.variety !== prices.commodity ? r.variety : null].filter(Boolean).join(' · ')}
                </span>
              </td>
              <td className="py-1 pl-2 text-right font-mono">{rupees(r.min_price)}</td>
              <td className="py-1 pl-2 text-right font-mono font-bold text-emerald-800 dark:text-emerald-300">{rupees(r.modal_price)}</td>
              <td className="py-1 pl-2 text-right font-mono">{rupees(r.max_price)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-1.5 text-[11px] text-slate-500 dark:text-slate-400 flex flex-wrap items-center gap-x-1.5">
        {prices.date && <span>{P.asOf} {prices.date}{priceAge(prices.date) ? ` (${ageText(priceAge(prices.date), P)})` : ''} ·</span>}
        <span>{P.source}:</span>
        <a href={portal.url} target="_blank" rel="noopener noreferrer" className={linkCls}>
          {portal.label} <ExternalLink className="h-3 w-3" />
        </a>
        {prices.via_url && (
          <>
            <span className="text-slate-300">·</span>
            <a href={prices.via_url} target="_blank" rel="noopener noreferrer" className={linkCls}>
              {P.via} <ExternalLink className="h-3 w-3" />
            </a>
          </>
        )}
      </p>
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
  const rid = report && report.request_id;
  const [check, setCheck] = useState(() => (rid ? readCheck(rid) : null));
  const [checking, setChecking] = useState(false);

  // Which badge to show on top: AI-check warning > dated price badge > normal trust badge
  const checkFailed = !!(check && typeof check.score === 'number' && check.score < 50);
  const hasPriceTable = !!(message.prices && message.prices.status === 'ok' && Array.isArray(message.prices.records)
    && message.prices.records.length > 0 && trust !== 'refused');
  const priceBadge = hasPriceTable ? priceBadgeText(message.prices, language) : null;
  let badge = null;
  if (checkFailed) {
    badge = { Icon: AlertTriangle, box: WARN_BOX, text: L.checkWarn || LABELS.en.checkWarn };
  } else if (priceBadge) {
    badge = { Icon: BarChart3, box: priceBadge.fresh ? TRUST_STYLE.verified.box : WARN_BOX, text: priceBadge.text };
  } else if (style) {
    badge = { Icon: style.Icon, box: style.box, text: L[trust] };
  }

  // Ask other AIs to grade this answer, once, right after it appears
  useEffect(() => {
    if (!rid || check || !message.answered_by || message.answered_by === 'search_only') return undefined;
    const age = Date.now() - Date.parse(message.time || 0);
    if (!(age >= 0 && age < 20 * 60 * 1000)) return undefined;   // old chats: don't re-check
    let cancelled = false;
    setChecking(true);
    runCheck(rid).then((data) => {
      if (!cancelled && data && data.status === 'ok') setCheck(data);
    }).finally(() => { if (!cancelled) setChecking(false); });
    return () => { cancelled = true; };
  }, [rid]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleShare = async () => {
    const lines = ['🌾 Sahakar Sahayak', ''];
    if (question) lines.push(`❓ ${question}`, '');
    lines.push(`✅ ${message.text}`);
    if (showSource) {
      lines.push('', `📄 ${best.documentName}${best.page ? ` (${L.page} ${best.page})` : ''}`);
      if (best.link) lines.push(best.link);
    }
    const pr = message.prices;
    if (pr && pr.status === 'ok' && Array.isArray(pr.records) && pr.records.length) {
      lines.push('', `📈 ${pr.commodity} (₹/quintal${pr.date ? `, ${pr.date}` : ''}):`);
      pr.records.slice(0, 3).forEach((r) => lines.push(`• ${r.market}: ${rupees(r.modal_price)}`));
      lines.push(pr.source_url);
    }
    if (check && typeof check.score === 'number') lines.push('', `⚖️ ${L.check}: ${L[check.verdict] || check.verdict} (${check.score}/100)`);
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
      {/* 1. Trust line (+ best source). Replaced by the AI-check warning or the dated price badge when those apply. */}
      {badge && (
        <div className={`flex flex-wrap items-center gap-x-3 gap-y-1.5 px-3 py-2 rounded-xl border text-xs font-semibold ${badge.box}`}>
          <span className="inline-flex items-center gap-1.5">
            <badge.Icon className="h-4 w-4 shrink-0" />
            {badge.text}
          </span>
          {showSource && !priceBadge && (
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

      {/* 1a. Backup AI notice: shown only when Sarvam didn't answer */}
      {message.answered_by && message.answered_by !== 'sarvam' && AI_NAMES[message.answered_by] && (
        <p className="text-[11px] text-slate-500 dark:text-slate-400 px-1">
          🤖 {AI_NAMES[message.answered_by]}
        </p>
      )}

      {/* 1b. Live AI check: short verdict (details inside the scorecard) */}
      {checking && !check && (
        <p className="text-[11px] text-slate-400 dark:text-slate-500 px-1 flex items-center gap-1.5 animate-pulse">
          <Scale className="h-3.5 w-3.5" /> {L.checking}
        </p>
      )}
      {check && typeof check.score === 'number' && (
        <p className="text-xs text-slate-600 dark:text-slate-300 px-1 flex flex-wrap items-center gap-1.5">
          <Scale className="h-3.5 w-3.5" />
          <span className="font-semibold">{L.check}:</span>
          <span className={`px-1.5 py-0.5 rounded-md font-bold ${VERDICT_STYLE[check.verdict] || ''}`}>{L[check.verdict] || check.verdict}</span>
          <span className="font-mono font-bold">{check.score}/100</span>
          <span className="text-slate-400">
            · {(check.judges || []).filter((j) => j.status === 'ok').map((j) => JUDGE_SHORT[j.judge] || j.judge).join(' + ')}
          </span>
        </p>
      )}

      {/* 1b2. Live mandi prices (price questions only) */}
      {message.prices && trust !== 'refused' && <PricesCard prices={message.prices} language={language} />}

      {/* 1c. Talk to a person: official helplines (only under answers that aren't fully verified) */}
      {message.helplines && message.helplines.length > 0 && (
        <div className="px-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
          <p className="text-[11px] font-bold text-slate-600 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
            <Phone className="h-3.5 w-3.5" />
            {L.help}
          </p>
          <ul className="space-y-1">
            {message.helplines.map((h) => (
              <li key={h.id} className="text-xs text-slate-600 dark:text-slate-400 flex flex-wrap items-baseline gap-x-2">
                <span className="font-semibold text-slate-700 dark:text-slate-200">{h.label}</span>
                {h.phone ? (
                  <a href={`tel:${h.phone}`} className="font-mono font-bold text-primary-700 dark:text-primary-300 hover:underline">{h.display}</a>
                ) : h.url ? (
                  <a href={h.url} target="_blank" rel="noopener noreferrer" className="font-bold text-primary-700 dark:text-primary-300 hover:underline">{h.display}</a>
                ) : (
                  <span className="font-semibold">{h.display}</span>
                )}
                {h.note && <span className="text-[11px] text-slate-400 dark:text-slate-500">· {h.note}</span>}
              </li>
            ))}
          </ul>
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
        {report && ((trust && trust !== 'refused') || check) && (
          <button
            onClick={() => setShowReport((v) => !v)}
            className={`${btn} ${showReport ? 'border-primary-300 text-primary-700 bg-primary-50 dark:bg-primary-950/30 dark:text-primary-300 dark:border-primary-800' : btnIdle}`}
            aria-expanded={showReport}
          >
            <Search className="h-3.5 w-3.5" />
            {L.scorecard}
            {showReport ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>

      {/* 3. Detailed report (hidden until tapped) */}
      {showReport && report && <SearchReport report={report} check={check} title={L.scorecard} />}
    </div>
  );
};

export default AnswerFooter;
