import { motion } from 'framer-motion';
import { TrendingUp, ShieldAlert, CheckCircle, AlertTriangle, TrendingDown, Minus } from 'lucide-react';
import { Badge } from '../components/common/Badge';
import { LineMetricChart } from '../components/charts/LineMetricChart';
import type { Forecast } from '../types';

/** Breach probability: 0–100% based on how full the buffer is and how fast trend is growing */
function calcBreachProbability(fc: Forecast): number {
  const pct = Math.min(100, Math.max(0, (fc.current_value / fc.threshold) * 100));
  const slopeFactor = fc.minutes_to_breach !== null
    ? Math.max(0, 1 - fc.minutes_to_breach / 120)   // 0 min → 100%, 120 min → 0%
    : 0;
  // Weighted: 60% utilization proximity, 40% time-to-breach urgency
  const raw = (pct / 100) * 0.6 + slopeFactor * 0.4;
  return Math.min(99, Math.round(raw * 100));
}

interface ForecastProps { forecasts: Forecast[]; }

function generateTrend(fc: Forecast) {
  const current = fc.current_value || 0;
  const slope = fc.trend_slope || 0;
  const data: any[] = [];
  for (let i = 5; i > 0; i--) data.push({ time: `-${i * 30}s`, current: +(current - i * slope).toFixed(4), predicted: null });
  data.push({ time: 'Now', current: +current.toFixed(4), predicted: +current.toFixed(4) });
  for (let i = 1; i <= 10; i++) data.push({ time: `+${i * 30}s`, current: null, predicted: +(current + i * slope).toFixed(4) });
  return data;
}

const SEVERITY_STYLE: Record<string, { border: string; bg: string; icon: any; iconCls: string }> = {
  Critical: { border: 'border-danger-200',  bg: 'bg-danger-50/40',  icon: ShieldAlert,   iconCls: 'text-danger-600 bg-danger-50' },
  Warning:  { border: 'border-warning-200', bg: 'bg-warning-50/40', icon: AlertTriangle, iconCls: 'text-warning-600 bg-warning-50' },
  Info:     { border: 'border-brand-100',   bg: '',                  icon: CheckCircle,   iconCls: 'text-success-600 bg-success-50' },
};

export function ForecastPage({ forecasts }: ForecastProps) {
  if (forecasts.length === 0) {
    return (
      <div className="space-y-6">
        <div><h2 className="page-header-title">Predictive Forecasts</h2><p className="page-header-subtitle">Machine learning saturation predictions</p></div>
        <div className="solid-card p-16 flex flex-col items-center text-center">
          <TrendingUp className="h-12 w-12 text-surface-200 mb-4 animate-pulse" />
          <h3 className="text-base font-700 text-surface-700">Warming Up Forecast Models</h3>
          <p className="text-sm text-surface-400 mt-2 max-w-sm">Requires ≥ 6 metric samples (≈ 3 minutes). Please wait...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div><h2 className="page-header-title">Predictive Forecasts</h2><p className="page-header-subtitle">Linear regression saturation ETA predictions from live Prometheus metrics</p></div>
        <div className="flex items-center gap-2 px-4 py-2 bg-purple-50 border border-purple-100 rounded-xl">
          <TrendingUp className="h-4 w-4 text-purple-600" />
          <span className="text-sm font-600 text-purple-700">{forecasts.length} Predictions Active</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {forecasts.map((fc, i) => {
          const s = SEVERITY_STYLE[fc.severity] || SEVERITY_STYLE.Info;
          const Icon = s.icon;
          const pct = Math.min(100, Math.max(0, (fc.current_value / fc.threshold) * 100));
          const data = generateTrend(fc);

          return (
            <motion.div
              key={fc.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className={`solid-card p-6 border ${s.border} ${s.bg} space-y-4`}
            >
              {/* Header */}
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-xl ${s.iconCls}`}><Icon className="h-4 w-4" /></div>
                  <div>
                    <p className="text-xs font-600 text-surface-400 uppercase tracking-wider">{fc.resource_type.replace('_', ' ')}</p>
                    <p className="text-sm font-700 text-surface-900 capitalize mt-0.5">{fc.service_name}</p>
                  </div>
                </div>
                <Badge severity={fc.severity} size="sm" />
              </div>

              {/* Breach Probability */}
              {(() => {
                const prob = calcBreachProbability(fc);
                const isRisky = prob >= 60;
                const isMedium = prob >= 30 && prob < 60;
                return (
                  <div className={`p-4 rounded-2xl border ${
                    isRisky  ? 'bg-danger-50 border-danger-100' :
                    isMedium ? 'bg-warning-50 border-warning-100' :
                               'bg-success-50 border-success-100'
                  }`}>
                    <div className="flex items-center justify-between mb-2">
                      <p className={`text-xs font-600 uppercase tracking-wider ${
                        isRisky ? 'text-danger-500' : isMedium ? 'text-warning-600' : 'text-success-600'
                      }`}>Breach Probability</p>
                      <span className={`text-2xl font-800 tracking-tight ${
                        isRisky ? 'text-danger-600' : isMedium ? 'text-warning-600' : 'text-success-600'
                      }`}>{prob}%</span>
                    </div>
                    <div className="h-2 bg-white/60 rounded-full overflow-hidden">
                      <motion.div
                        className={`h-full rounded-full ${
                          isRisky ? 'bg-danger-500' : isMedium ? 'bg-warning-500' : 'bg-success-500'
                        }`}
                        initial={{ width: 0 }}
                        animate={{ width: `${prob}%` }}
                        transition={{ duration: 0.9 }}
                      />
                    </div>
                    <p className={`text-[10px] mt-1.5 font-500 ${
                      isRisky ? 'text-danger-500' : isMedium ? 'text-warning-600' : 'text-success-600'
                    }`}>
                      {isRisky ? 'High risk — threshold breach imminent' :
                       isMedium ? 'Moderate risk — monitor closely' :
                       'Low risk — well within safe limits'}
                    </p>
                  </div>
                );
              })()}

              {/* Progress */}
              <div>
                <div className="flex justify-between text-xs text-surface-500 font-500 mb-1.5">
                  <span>Current utilization</span>
                  <span className="font-700">{pct.toFixed(1)}%</span>
                </div>
                <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                  <motion.div
                    className={`h-full rounded-full ${fc.severity === 'Critical' ? 'bg-danger-500' : fc.severity === 'Warning' ? 'bg-warning-500' : 'bg-success-500'}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.8, delay: i * 0.06 }}
                  />
                </div>
              </div>

              {/* Mini Chart */}
              <LineMetricChart data={data} dataKey="current" predKey="predicted" threshold={fc.threshold} color="#14B8A6" predColor="#7C3AED" height={150} />

              {/* Stats */}
              <div className="grid grid-cols-3 gap-3 pt-2 border-t border-surface-100">
                <div>
                  <p className="text-[10px] text-surface-400 font-500 uppercase tracking-wider">Utilization</p>
                  <p className="text-sm font-700 text-surface-800">{pct.toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-[10px] text-surface-400 font-500 uppercase tracking-wider">Trend</p>
                  <div className="flex items-center gap-1 mt-0.5">
                    {(fc.trend_slope ?? 0) > 0.0001
                      ? <TrendingUp className="h-3.5 w-3.5 text-danger-500" />
                      : (fc.trend_slope ?? 0) < -0.0001
                        ? <TrendingDown className="h-3.5 w-3.5 text-success-500" />
                        : <Minus className="h-3.5 w-3.5 text-surface-400" />}
                    <p className="text-sm font-700 text-surface-800">{(fc.trend_slope ?? 0) > 0 ? 'Rising' : (fc.trend_slope ?? 0) < 0 ? 'Falling' : 'Flat'}</p>
                  </div>
                </div>
                <div>
                  <p className="text-[10px] text-surface-400 font-500 uppercase tracking-wider">R² Fit</p>
                  <p className="text-sm font-700 text-surface-800">{fc.r_squared?.toFixed(3)}</p>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
