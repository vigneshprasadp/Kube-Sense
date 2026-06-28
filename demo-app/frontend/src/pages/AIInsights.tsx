import { useState } from 'react';
import { motion } from 'framer-motion';
import { Bot, Sparkles, ShieldAlert, CheckSquare, Square, Shield, Lightbulb, AlertCircle, RefreshCw } from 'lucide-react';
import { Badge } from '../components/common/Badge';
import type { Recommendation, RCAReport } from '../types';

interface AIInsightsProps {
  recommendation: Recommendation | null;
  activeRca: RCAReport | null;
  generatingRecommend: boolean;
  onGenerate: (rcaId?: number) => void;
}

export function AIInsights({ recommendation, activeRca, generatingRecommend, onGenerate }: AIInsightsProps) {
  const [checkedItems, setCheckedItems] = useState<Set<number>>(new Set());

  const toggleCheck = (i: number) => {
    setCheckedItems(prev => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 bg-purple-100 rounded-lg"><Bot className="h-4 w-4 text-purple-600" /></div>
            <h2 className="page-header-title">AI Operations Center</h2>
          </div>
          <p className="page-header-subtitle">Root Cause Analysis & SRE Recommendations</p>
        </div>
      </div>

      {/* Active RCA Card */}
      {activeRca && (
        <div className={`solid-card p-6 border ${
          activeRca.chaos_active
            ? 'border-danger-100 bg-danger-50/30'
            : 'border-surface-200 bg-surface-50/30'
        }`}>
          <div className="flex items-start gap-4">
            <div className={`p-3 rounded-xl flex-shrink-0 ${
              activeRca.chaos_active ? 'bg-danger-100' : 'bg-surface-100'
            }`}>
              <ShieldAlert className={`h-6 w-6 ${
                activeRca.chaos_active ? 'text-danger-600' : 'text-surface-500'
              }`} />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <h3 className="text-base font-700 text-surface-900">
                  {activeRca.chaos_active ? 'Active Root Cause' : 'Last Root Cause'}
                </h3>
                <Badge severity={activeRca.chaos_active ? activeRca.severity : 'Info'} />
              </div>
              <p className={`text-sm font-700 mb-1 ${
                activeRca.chaos_active ? 'text-danger-700' : 'text-surface-700'
              }`}>{activeRca.root_cause}</p>
              <p className="text-sm text-surface-600 leading-relaxed">{activeRca.message}</p>
              <div className="flex items-center gap-6 mt-3 text-xs font-600 text-surface-500">
                <span>Affected: <span className={activeRca.chaos_active ? 'text-danger-600' : 'text-surface-600'}>{activeRca.affected_services}</span></span>
                <span>Confidence: <span className={activeRca.chaos_active ? 'text-danger-600' : 'text-surface-600'}>{Math.round(activeRca.confidence_score * 100)}%</span></span>
                <span>Time: {new Date(activeRca.timestamp).toLocaleTimeString()}</span>
              </div>
              {/* Confidence bar */}
              <div className="mt-3 h-1.5 bg-surface-200 rounded-full overflow-hidden">
                <motion.div
                  className={`h-full rounded-full ${
                    activeRca.chaos_active ? 'bg-danger-500' : 'bg-surface-500'
                  }`}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.round(activeRca.confidence_score * 100)}%` }}
                  transition={{ duration: 0.8 }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {!recommendation ? (
        <div className="solid-card p-16 flex flex-col items-center text-center">
          <div className="p-4 bg-purple-50 rounded-2xl mb-4">
            <Bot className="h-10 w-10 text-purple-400" />
          </div>
          <h3 className="text-base font-700 text-surface-700">No AI Analysis Yet</h3>
          <p className="text-sm text-surface-400 mt-2 max-w-sm">Waiting for the AI Operations Center to generate SRE recommendations for the active incident.</p>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Explanation */}
          <div className="solid-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <AlertCircle className="h-5 w-5 text-brand-600" />
              <h3 className="text-sm font-700 text-surface-900">Incident Explanation</h3>
            </div>
            <p className="text-sm text-surface-600 leading-relaxed whitespace-pre-wrap">{recommendation.explanation}</p>
          </div>

          {/* Recommendations */}
          <div className="solid-card p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-danger-600" />
                <h3 className="text-sm font-700 text-surface-900">Remediation Actions</h3>
              </div>
              <span className="text-xs text-surface-400 font-500">
                {checkedItems.size}/{(recommendation.recommended_fixes || []).length} completed
              </span>
            </div>
            <div className="space-y-2.5">
              {(recommendation.recommended_fixes || []).map((rec, i) => (
                <button
                  key={i}
                  onClick={() => toggleCheck(i)}
                  className={`w-full flex items-start gap-3 p-4 rounded-xl border text-left transition-all
                    ${checkedItems.has(i) ? 'bg-success-50 border-success-200' : 'bg-surface-50 border-surface-100 hover:border-brand-200'}`}
                >
                  {checkedItems.has(i)
                    ? <CheckSquare className="h-4 w-4 text-success-600 flex-shrink-0 mt-0.5" />
                    : <Square className="h-4 w-4 text-surface-300 flex-shrink-0 mt-0.5" />
                  }
                  <span className={`text-sm ${checkedItems.has(i) ? 'line-through text-surface-400' : 'text-surface-700 font-500'}`}>{rec}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Preventive Measures */}
          <div className="solid-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Lightbulb className="h-5 w-5 text-warning-500" />
              <h3 className="text-sm font-700 text-surface-900">Preventive Measures</h3>
            </div>
            <div className="space-y-2.5">
              {(recommendation.preventive_measures || []).map((m, i) => (
                <div key={i} className="flex items-start gap-3 p-4 bg-warning-50/60 border border-warning-100 rounded-xl">
                  <Shield className="h-4 w-4 text-warning-500 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-surface-700 font-500">{m}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
