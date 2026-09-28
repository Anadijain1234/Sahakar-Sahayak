import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Lock, RefreshCw, Download, LogOut, BarChart3, AlertTriangle, ArrowLeft } from 'lucide-react';

// Admin Insights: what farmers are asking. Data comes from the backend's
// /insights.json, protected by the INSIGHTS_KEY password set in Render.
const API = (import.meta.env.VITE_API_URL || 'https://sahakar-sahayak-4.onrender.com').replace(/\/$/, '');
const KEY_STORE = 'sahakar_insights_key';

const LANG_NAMES = { en: 'English', hi: 'Hindi', kn: 'Kannada', ne: 'Nepali', ta: 'Tamil', te: 'Telugu', ml: 'Malayalam' };
const AI_NAMES = { sarvam: 'Sarvam AI', groq: 'Groq (backup)', cloudflare: 'Cloudflare (backup)', search_only: 'Search only (no AI)', unknown: 'Not recorded' };
const TRUST = {
  verified: '🟢 Verified', partial: '🟡 Partly verified', general: '🔵 General guidance',
  refused: 'Refused (off-topic)', error: 'Error',
};

const readKey = () => { try { return sessionStorage.getItem(KEY_STORE) || ''; } catch { return ''; } };
const saveKey = (k) => { try { k ? sessionStorage.setItem(KEY_STORE, k) : sessionStorage.removeItem(KEY_STORE); } catch { /* private mode */ } };

const Card = ({ label, value }) => (
  <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 py-3">
    <div className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100">{value}</div>
    <div className="text-sm text-slate-500 dark:text-slate-400 mt-1">{label}</div>
  </div>
);

const Panel = ({ title, children, className = '' }) => (
  <section className={`rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 ${className}`}>
    <h2 className="text-base font-bold text-slate-800 dark:text-slate-100 mb-3">{title}</h2>
    {children}
  </section>
);

const Bars = ({ pairs, names }) => {
  if (!pairs || pairs.length === 0) return <p className="text-sm text-slate-400">No data yet.</p>;
  const top = Math.max(...pairs.map(([, n]) => n)) || 1;
  return (
    <div className="space-y-1.5">
      {pairs.map(([k, n]) => (
        <div key={k || 'none'} className="grid grid-cols-[minmax(0,9rem)_1fr_2.5rem] items-center gap-2 text-sm">
          <span className="truncate text-slate-600 dark:text-slate-300" title={(names && names[k]) || k}>{(names && names[k]) || k || '—'}</span>
          <span className="h-3 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
            <span className="block h-full rounded-full bg-primary-500" style={{ width: `${(100 * n) / top}%` }} />
          </span>
          <span className="text-right font-mono tabular-nums text-slate-700 dark:text-slate-200">{n}</span>
        </div>
      ))}
    </div>
  );
};

const QuestionTable = ({ rows, cols, empty }) => (
  <div className="overflow-x-auto">
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs uppercase tracking-wider text-slate-400 border-b border-slate-200 dark:border-slate-800">
          {cols.map((c) => <th key={c.label} className="py-2 pr-3 font-semibold">{c.label}</th>)}
        </tr>
      </thead>
      <tbody>
        {rows.length === 0 ? (
          <tr><td colSpan={cols.length} className="py-3 text-slate-400">{empty}</td></tr>
        ) : rows.map((r, i) => (
          <tr key={i} className="border-b border-slate-100 dark:border-slate-800/70 align-top">
            {cols.map((c) => <td key={c.label} className={`py-2 pr-3 ${c.className || ''}`}>{c.render(r)}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

export const Admin = () => {
  const [key, setKey] = useState(readKey);
  const [input, setInput] = useState('');
  const [data, setData] = useState(null);
  const [status, setStatus] = useState(readKey() ? 'loading' : 'login'); // login | loading | ready | error
  const [error, setError] = useState('');

  const load = useCallback(async (k) => {
    setStatus('loading');
    setError('');
    try {
      const res = await fetch(`${API}/insights.json`, { headers: { 'X-Insights-Key': k } });
      if (res.status === 401) { saveKey(''); setKey(''); setStatus('login'); setError('Wrong password.'); return; }
      if (res.status === 503) { setStatus('error'); setError('Insights are not set up yet: add INSIGHTS_KEY (any password) in Render → Environment, then redeploy.'); return; }
      if (!res.ok) throw new Error(`Server replied ${res.status}`);
      setData(await res.json());
      setStatus('ready');
    } catch (e) {
      setStatus('error');
      setError('Could not reach the server. On the free plan it may be waking up. Wait a minute and press Refresh.');
    }
  }, []);

  useEffect(() => { if (key) load(key); }, [key, load]);

  const login = (e) => {
    e.preventDefault();
    const k = input.trim();
    if (!k) return;
    saveKey(k);
    setKey(k);
    setInput('');
  };

  const logout = () => { saveKey(''); setKey(''); setData(null); setStatus('login'); };

  const downloadCsv = async () => {
    try {
      const res = await fetch(`${API}/insights.csv`, { headers: { 'X-Insights-Key': key } });
      if (!res.ok) throw new Error();
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement('a');
      a.href = url;
      a.download = 'sahakar_questions.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('CSV download failed. Try again.');
    }
  };

  const since = data && data.since ? new Date(data.since * 1000).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—';
  const days = (data && data.per_day) || [];
  const topDay = Math.max(1, ...days.map((d) => d.count));

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100">
      <div className="max-w-6xl mx-auto px-4 py-6 space-y-5">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Link to="/" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-primary-600 mb-1">
              <ArrowLeft className="h-3.5 w-3.5" /> Sahakar Sahayak
            </Link>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <BarChart3 className="h-6 w-6 text-primary-600" /> Admin · Insights
            </h1>
            <p className="text-sm sm:text-base text-slate-500 dark:text-slate-400">What farmers and cooperative members are asking{status === 'ready' ? ` · logged since ${since}` : ''}</p>
          </div>
          {status === 'ready' || (status === 'error' && key) ? (
            <div className="flex flex-wrap gap-2">
              <button onClick={() => load(key)} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold border border-slate-200 dark:border-slate-700 hover:bg-white dark:hover:bg-slate-800">
                <RefreshCw className="h-3.5 w-3.5" /> Refresh
              </button>
              {status === 'ready' && (
                <button onClick={downloadCsv} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold border border-slate-200 dark:border-slate-700 hover:bg-white dark:hover:bg-slate-800">
                  <Download className="h-3.5 w-3.5" /> Download CSV
                </button>
              )}
              <button onClick={logout} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold border border-slate-200 dark:border-slate-700 hover:bg-white dark:hover:bg-slate-800">
                <LogOut className="h-3.5 w-3.5" /> Log out
              </button>
            </div>
          ) : null}
        </header>

        {status === 'login' && (
          <form onSubmit={login} className="max-w-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-3">
            <p className="text-sm font-semibold flex items-center gap-2"><Lock className="h-4 w-4" /> Admin password</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">The INSIGHTS_KEY you set in Render → Environment.</p>
            <input
              type="password"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Password"
              autoFocus
            />
            {error && <p className="text-xs text-red-600">{error}</p>}
            <button type="submit" className="w-full rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm font-semibold py-2">Open insights</button>
          </form>
        )}

        {status === 'loading' && <p className="text-sm text-slate-500">Loading… (the free server can take up to a minute to wake up)</p>}

        {status === 'error' && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-900 px-4 py-3 text-sm text-amber-800 dark:text-amber-300 flex gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" /> {error}
          </div>
        )}

        {status === 'ready' && data && (
          <>
            {error && <p className="text-xs text-red-600">{error}</p>}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Card label="Questions asked" value={data.total} />
              <Card label="In the last 7 days" value={data.last_7_days} />
              <Card label="Answered from official documents" value={`${data.from_documents_pct.toFixed(2)}%`} />
              <Card label="🟢 Verified answers" value={`${data.verified_pct.toFixed(2)}%`} />
              <Card label="🔵 General guidance" value={`${data.general_pct.toFixed(2)}%`} />
              <Card label="Off-topic refused" value={`${data.refused_pct.toFixed(2)}%`} />
              <Card label="Avg response time" value={`${data.avg_response_s.toFixed(2)} s`} />
              <Card label="AI-check score (graded by other AIs)" value={typeof data.avg_judge_score === 'number' ? `${Math.round(data.avg_judge_score)}/100` : '—'} />
            </div>

            <Panel title="Questions per day (last 14 days)">
              <div className="flex items-end gap-1 h-32">
                {days.map((d) => (
                  <div key={d.days_ago} className="flex-1 rounded-t bg-primary-400/80 dark:bg-primary-600/80 min-h-[2px]"
                    style={{ height: `${Math.max(2, (128 * d.count) / topDay)}px` }}
                    title={`${d.count} questions, ${d.days_ago === 0 ? 'today' : `${d.days_ago} days ago`}`} />
                ))}
              </div>
              <div className="flex justify-between text-xs text-slate-400 mt-1"><span>14 days ago</span><span>today</span></div>
            </Panel>

            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              <Panel title="Languages used"><Bars pairs={data.languages} names={LANG_NAMES} /></Panel>
              <Panel title="Schemes & laws asked about"><Bars pairs={data.topics} /></Panel>
              <Panel title="Type of question"><Bars pairs={data.intents} /></Panel>
              <Panel title="Which AI answered"><Bars pairs={data.answered_by} names={AI_NAMES} /></Panel>
            </div>

            <Panel title="Latest questions and their scorecards">
              <QuestionTable
                rows={data.recent || []}
                empty="No questions yet."
                cols={[
                  { label: 'When', render: (r) => (r.ts ? new Date(r.ts * 1000).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'), className: 'whitespace-nowrap text-slate-500' },
                  { label: 'Question', render: (r) => r.english_question || r.question },
                  { label: 'Answer', render: (r) => TRUST[r.trust_level] || r.trust_level, className: 'whitespace-nowrap' },
                  { label: 'Document match', render: (r) => (typeof r.final_score === 'number' ? `${Math.round(r.final_score)}%` : '—'), className: 'font-mono' },
                  { label: 'AI check', render: (r) => (typeof r.judge_score === 'number' ? `${Math.round(r.judge_score)}/100` : '—'), className: 'font-mono whitespace-nowrap' },
                  { label: 'Answered by', render: (r) => AI_NAMES[r.answered_by] || r.answered_by || '—', className: 'whitespace-nowrap' },
                  { label: 'Time', render: (r) => (r.response_ms ? `${(r.response_ms / 1000).toFixed(1)} s` : '—'), className: 'font-mono' },
                ]}
              />
            </Panel>

            <Panel title="Most asked questions">
              <QuestionTable
                rows={data.most_asked || []}
                empty="No questions yet."
                cols={[
                  { label: 'Question', render: (r) => r.question },
                  { label: 'Times', render: (r) => r.count, className: 'font-mono' },
                  { label: 'Answer', render: (r) => TRUST[r.trust_level] || r.trust_level, className: 'whitespace-nowrap' },
                ]}
              />
            </Panel>

            <Panel title="⚠️ Knowledge gaps: not fully answered from official documents">
              <p className="text-sm text-slate-500 dark:text-slate-400 -mt-1 mb-2">Add the missing official documents for these topics to backend/data/documents to improve answers.</p>
              <QuestionTable
                rows={data.gaps || []}
                empty="None. Every question was answered from the documents."
                cols={[
                  { label: 'Question', render: (r) => r.question },
                  { label: 'Language', render: (r) => LANG_NAMES[r.language] || r.language, className: 'whitespace-nowrap' },
                  { label: 'Answer', render: (r) => TRUST[r.trust_level] || r.trust_level, className: 'whitespace-nowrap' },
                ]}
              />
            </Panel>

            <p className="text-sm text-slate-400">
              Phone numbers and e-mail addresses are removed from questions before they are stored.{' '}
              {data.permanent ? 'Stored permanently in the database.' : "Stored on the server's temporary disk, so it starts again after each redeploy."}
              {' '}<a className="underline" href={`${API}/scoreboard`} target="_blank" rel="noopener noreferrer">See the accuracy test results</a>
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default Admin;
