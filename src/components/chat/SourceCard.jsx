import React from 'react';
import { FileText, ArrowUpRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const SourceCard = ({ source, onView }) => {
  const navigate = useNavigate();

  const handleView = (e) => {
    e.preventDefault();
    if (onView) {
      onView(source);
    } else if (source.link) {
      window.open(source.link, '_blank', 'noopener,noreferrer');
    } else if (source.id) {
      // Navigate to detailed resource page
      navigate(`/resources/${source.id}`);
    }
  };

  return (
    <div className="flex flex-col justify-between p-3.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl transition-all hover:bg-slate-100 dark:hover:bg-slate-800/80 group">
      <div className="flex gap-2.5 items-start">
        <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400 group-hover:scale-105 transition-transform">
          <FileText className="h-4.5 w-4.5" />
        </div>
        <div className="min-w-0">
          <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate leading-snug">
            {source.documentName}
          </h4>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate mt-0.5">
            {source.provision}
          </p>
        </div>
      </div>
      
      <button
        onClick={handleView}
        className="mt-3 inline-flex items-center justify-center gap-1 w-full py-1.5 border border-slate-200 dark:border-slate-800 rounded-lg text-[10px] font-semibold text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-800 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
      >
        <span>View Source</span>
        <ArrowUpRight className="h-3 w-3" />
      </button>
    </div>
  );
};
export default SourceCard;
