import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play, Square, Trash2, AlertTriangle, ShieldAlert, Cpu, HardDrive, Wifi, Server,
  Activity, CheckCircle, Info, RefreshCw, Check
} from 'lucide-react';
import { apiService } from '../services/api';
import { Badge } from '../components/common/Badge';
import type { ChaosEvent, Telemetry } from '../types';

interface ChaosLabProps {
  telemetry: Telemetry;
}

const TEMPLATE_ICONS: Record<string, any> = {
  cpu: Cpu,
  storage: HardDrive,
  network: Wifi,
};

const TEMPLATE_COLORS: Record<string, string> = {
  cpu: 'from-blue-500 to-indigo-500',
  storage: 'from-cyan-500 to-blue-500',
  network: 'from-orange-500 to-red-500',
};

export function ChaosLab({ telemetry }: ChaosLabProps) {
  const [templates, setTemplates] = useState<string[]>(['cpu', 'storage', 'network']);
  const [activeEvents, setActiveEvents] = useState<ChaosEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [chaosRca, setChaosRca] = useState<any>(null);

  // Form states
  const [selectedType, setSelectedType] = useState<string>('cpu');
  const [selectedTarget, setSelectedTarget] = useState<string>('backend');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('medium');

  // Parse URL query parameters on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const scenario = params.get('scenario');
    const service = params.get('service');
    const severity = params.get('severity');
    if (scenario) setSelectedType(scenario);
    if (service) setSelectedTarget(service);
    if (severity) setSelectedSeverity(severity);
  }, []);

  // Elapsed time for active event tracking
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  const fetchActiveEvents = useCallback(async () => {
    setSyncing(true);
    try {
      const data = await apiService.getActiveChaosEvents();
      setActiveEvents(data);
    } catch (err) {
      console.error("Failed to load active chaos events:", err);
    } finally {
      setSyncing(false);
    }
  }, []);

  useEffect(() => {
    fetchActiveEvents();
    const interval = setInterval(fetchActiveEvents, 5000);
    return () => clearInterval(interval);
  }, [fetchActiveEvents]);

  // Fetch chaos-correlated RCA every 10s
  const fetchChaosRca = useCallback(async () => {
    const rca = await apiService.getChaosRca();
    setChaosRca(rca);
  }, []);

  useEffect(() => {
    fetchChaosRca();
    const interval = setInterval(fetchChaosRca, 10000);
    return () => clearInterval(interval);
  }, [fetchChaosRca]);

  // Track elapsed seconds
  const activeEvent = activeEvents[0];
  useEffect(() => {
    if (!activeEvent) {
      setElapsedSeconds(0);
      return () => {};
    }
    const start = new Date(activeEvent.start_time).getTime();
    const updateElapsed = () => {
      const seconds = Math.floor((Date.now() - start) / 1000);
      setElapsedSeconds(seconds >= 0 ? seconds : 0);
    };
    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);
    return () => clearInterval(interval);
  }, [activeEvent]);

  const handleStartChaos = async () => {
    setLoading(true);
    try {
      await apiService.startChaos(selectedType, selectedTarget, selectedSeverity);
      await fetchActiveEvents();
    } catch (err) {
      alert("Failed to start simulation: " + err);
    } finally {
      setLoading(false);
    }
  };

  const handleStopChaos = async (eventId: string) => {
    setLoading(true);
    try {
      await apiService.stopChaos(eventId);
      await fetchActiveEvents();
    } catch (err) {
      alert("Failed to stop simulation: " + err);
    } finally {
      setLoading(false);
    }
  };

  // Timeline check helpers
  const getTimelineStatus = (stepSeconds: number) => {
    if (!activeEvent) return 'waiting';
    if (elapsedSeconds >= stepSeconds) return 'completed';
    return 'active';
  };

  // Generate demo steps based on scenario
  const getDemoSteps = () => {
    if (activeEvent?.event_type === 'storage') {
      return [
        { label: 'Healthy State', seconds: 0, desc: 'Normal volume writes' },
        { label: 'Abnormal Growth Alert', seconds: 60, desc: 'Growth rate anomaly logged' },
        { label: 'Capacity Forecast', seconds: 120, desc: 'Exhaustion warning created' },
        { label: 'Critical PVC Alert & RCA', seconds: 180, desc: 'PVC saturation root cause generated' }
      ];
    }

    // Default CPU, Memory, Network: 30/60/90/120s
    return [
      { label: 'Healthy State', seconds: 0, desc: 'Normal telemetry collection' },
      { label: 'Anomaly Warning Alert', seconds: 30, desc: 'High saturation spike alert' },
      { label: 'Saturation Forecast', seconds: 60, desc: 'Predictive ETA breach forecast' },
      { label: 'Critical Threshold Alert', seconds: 90, desc: 'Resource limit exceeded warning' },
      { label: 'Root Cause Correlated', seconds: 120, desc: 'RCA pipeline maps outage explanation' }
    ];
  };

  const currentSteps = getDemoSteps();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="page-header-title">Chaos Simulation Engine</h2>
          <p className="page-header-subtitle">Inject synthetic faults, saturate workloads, and simulate cluster incidents to test the KubeSense pipeline.</p>
        </div>
        <button
          onClick={fetchActiveEvents}
          disabled={syncing}
          className="p-2 border border-surface-200 rounded-xl hover:bg-surface-50 text-surface-600 transition-all flex items-center gap-1.5"
        >
          <RefreshCw className={`h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
          <span className="text-xs font-600">Sync State</span>
        </button>
      </div>

      {/* Active Event Timeline Track Banner */}
      <AnimatePresence mode="wait">
        {activeEvent && (
          <motion.div
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            className="p-6 bg-gradient-to-r from-red-50 via-rose-50/50 to-amber-50/50 border border-red-100 shadow-md shadow-red-500/5"
            style={{ borderRadius: '1.5rem' }}
          >
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-danger-500/10 text-danger-500 border border-danger-500/20 rounded-2xl shadow-lg flex-shrink-0 animate-pulse">
                  <Activity className="h-6 w-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-800 text-danger-600 bg-red-100 border border-red-200 px-2 py-0.5 rounded-full uppercase tracking-wider">
                      Simulation Active
                    </span>
                  </div>
                  <h3 className="text-xl font-800 text-surface-900 capitalize mt-1">
                    {activeEvent.event_type.replace('_', ' ')} Saturation on <span className="text-brand-700 font-900">{activeEvent.target_service}</span>
                  </h3>
                  <p className="text-sm text-surface-500 mt-0.5">
                    Severity Level: <span className="text-surface-700 font-750 uppercase">{activeEvent.severity}</span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleStopChaos(activeEvent.id)}
                disabled={loading}
                className="lg:self-center flex items-center justify-center gap-2 px-5 py-3 bg-danger-600 hover:bg-danger-500 text-white text-sm font-700 rounded-xl transition-all shadow-md hover:shadow-lg shadow-danger-500/25 border border-danger-500/10"
              >
                <Square className="h-4 w-4 fill-current" /> Stop Simulation
              </button>
            </div>

            {/* Timeline Progress Tracker */}
            <div className="mt-8">
              <div className="relative flex justify-between items-start gap-4">
                <div className="absolute top-4 left-6 right-6 h-0.5 bg-surface-200 z-0" />
                
                {currentSteps.map((step, idx) => {
                  const status = getTimelineStatus(step.seconds);
                  return (
                    <div key={idx} className="relative z-10 flex flex-col items-center text-center flex-1 max-w-[140px]">
                      <div
                        className={`w-9 h-9 rounded-full flex items-center justify-center border-2 transition-all duration-500 ${
                          status === 'completed'
                            ? 'bg-success-600 border-success-600 text-white shadow-[0_0_12px_rgba(22,163,74,0.25)]'
                            : status === 'active' && elapsedSeconds >= step.seconds
                            ? 'bg-white border-brand-500 text-brand-600 animate-pulse'
                            : 'bg-white border-surface-200 text-surface-400'
                        }`}
                      >
                        {status === 'completed' ? (
                          <Check className="h-4.5 w-4.5 stroke-[3] text-white" />
                        ) : (
                          <span className="text-xs font-700">{step.seconds}s</span>
                        )}
                      </div>
                      <p className="text-xs font-700 text-surface-800 mt-2">{step.label}</p>
                      <p className="text-[10px] text-surface-400 font-500 mt-0.5 leading-tight">{step.desc}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Controls Panel */}
        <div className="lg:col-span-5 space-y-6">
          <div className="solid-card p-6 space-y-6">
            <div>
              <h3 className="text-lg font-700 text-surface-900">Configure Scenario</h3>
              <p className="text-sm text-surface-400 mt-1">Select simulation settings to start.</p>
            </div>

            {/* 1. Scenario Templates */}
            <div className="space-y-2">
              <label className="text-xs font-700 text-surface-500 uppercase tracking-wider">1. Select Scenario</label>
              <div className="grid grid-cols-1 gap-2.5">
                {templates.map(type => {
                  const Icon = TEMPLATE_ICONS[type] || AlertTriangle;
                  const colors = TEMPLATE_COLORS[type] || 'from-surface-500 to-surface-600';
                  const isSelected = selectedType === type;
                  return (
                    <button
                      key={type}
                      type="button"
                      onClick={() => {
                        setSelectedType(type);
                        if (type === 'storage') {
                          setSelectedTarget('database'); // Storage usually targets postgres db
                        }
                      }}
                      className={`flex items-center gap-4 p-4 rounded-2xl border text-left transition-all ${
                        isSelected
                          ? 'border-brand-600 bg-brand-50/10 shadow-sm'
                          : 'border-surface-200 hover:border-surface-300 bg-white'
                      }`}
                    >
                      <div className={`p-2.5 rounded-xl bg-gradient-to-br ${colors} text-white shadow-sm`}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-700 text-surface-900 capitalize">
                          {type.replace('_', ' ')} Saturation
                        </p>
                        <p className="text-xs text-surface-400 mt-0.5">
                          {type === 'cpu' && 'Simulate extreme CPU spikes'}
                          {type === 'storage' && 'Trigger PVC volume explosion'}
                          {type === 'network' && 'Simulate target link network latency'}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 2. Target Service */}
            <div className="space-y-2">
              <label className="text-xs font-700 text-surface-500 uppercase tracking-wider">2. Target Service</label>
              <select
                value={selectedTarget}
                onChange={e => setSelectedTarget(e.target.value)}
                disabled={selectedType === 'storage'} // lock storage target to database (postgres pvc)
                className="w-full px-4 py-3 rounded-xl border border-surface-200 focus:outline-none focus:border-brand-500 text-sm font-600 text-surface-800 bg-white"
              >
                <option value="backend">backend (Go/Python workload)</option>
                <option value="frontend">frontend (Visual React client)</option>
                <option value="database">database (Postgres replica storage)</option>
              </select>
            </div>

            {/* 3. Severity Level */}
            <div className="space-y-2">
              <label className="text-xs font-700 text-surface-500 uppercase tracking-wider">3. Severity Level</label>
              <div className="grid grid-cols-3 gap-2">
                {['low', 'medium', 'high'].map(sev => (
                  <button
                    key={sev}
                    type="button"
                    onClick={() => setSelectedSeverity(sev)}
                    className={`py-2 px-3 text-xs font-700 uppercase rounded-xl border transition-all ${
                      selectedSeverity === sev
                        ? 'border-brand-600 bg-brand-50/10 text-brand-700'
                        : 'border-surface-200 text-surface-500 hover:border-surface-300 bg-white'
                    }`}
                  >
                    {sev}
                  </button>
                ))}
              </div>
            </div>

            {/* Start Button */}
            <button
              onClick={handleStartChaos}
              disabled={loading || !!activeEvent}
              className="w-full flex items-center justify-center gap-2 py-4 bg-brand-600 hover:bg-brand-700 text-white font-700 rounded-2xl transition-all shadow-lg hover:shadow-xl shadow-brand-500/25 disabled:bg-surface-150 disabled:text-surface-400 disabled:shadow-none"
            >
              <Play className="h-4 w-4 fill-current" /> Start Incident Simulation
            </button>
          </div>
        </div>

        {/* Telemetry Output Pipeline */}
        <div className="lg:col-span-7 space-y-6">
          {/* Section: Live Pipeline Diagnostics */}
          <div className="solid-card p-6 space-y-5">
            <div>
              <h3 className="text-lg font-700 text-surface-900">Live Telemetry Pipeline</h3>
              <p className="text-sm text-surface-400 mt-1">Real-time alerts, forecasts, and RCA results responding to chaos.</p>
            </div>

            {/* Dependency Graph status */}
            <div className="p-4 bg-surface-50 rounded-2xl border border-surface-100">
              <div className="flex justify-between items-center mb-3">
                <span className="text-xs font-700 text-surface-500 uppercase tracking-wider">Cluster Topology Nodes</span>
                <span className="text-[10px] bg-emerald-100 text-emerald-800 font-700 px-2 py-0.5 rounded-full">Reactive Discovery</span>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {['frontend', 'backend', 'database'].map(svc => {
                  const metrics = telemetry.metrics || {};
                  // Search for target pods
                  const podKeys = Object.keys(metrics).filter(k => k.startsWith(svc) || (svc === 'database' && k.includes('postgres')));
                  const matchingMetric = podKeys.length > 0 ? metrics[podKeys[0]] : null;
                  
                  // Deduce status based on pod crash simulation
                  let isCrashed = activeEvent?.event_type === 'pod_crash' && activeEvent.target_service === svc;
                  
                  return (
                    <div key={svc} className={`p-3 rounded-xl border flex flex-col items-center text-center ${
                      isCrashed ? 'bg-red-50 border-red-200' : 'bg-white border-surface-150'
                    }`}>
                      <Server className={`h-5 w-5 mb-1.5 ${isCrashed ? 'text-red-500 animate-bounce' : 'text-brand-600'}`} />
                      <p className="text-xs font-850 capitalize text-surface-800">{svc}</p>
                      <p className="text-[10px] text-surface-400 font-500 mt-0.5">
                        {isCrashed ? '0 pods (Failed)' : '1 pod (Healthy)'}
                      </p>
                      {matchingMetric && !isCrashed && (
                        <p className="text-[9px] text-surface-500 mt-1 font-600">
                          {matchingMetric.cpu_cores ? `CPU: ${(matchingMetric.cpu_cores * 100).toFixed(0)}%` : ''}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Current Alerts */}
            <div className="space-y-2">
              <span className="text-xs font-700 text-surface-500 uppercase tracking-wider">Active Alerts</span>
              {telemetry.alerts && telemetry.alerts.length > 0 ? (
                <div className="max-h-[160px] overflow-y-auto space-y-1.5 pr-1">
                  {telemetry.alerts.slice(0, 4).map(alert => (
                    <div key={alert.id} className="p-3 bg-red-50/50 border border-red-100 rounded-xl flex items-start gap-2.5">
                      <ShieldAlert className="h-4.5 w-4.5 text-red-600 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-xs font-600 text-red-800">{alert.message}</p>
                        <p className="text-[9px] text-red-500 font-500 mt-0.5">
                          {alert.type?.toUpperCase() ?? 'ALERT'} · {alert.pod_name}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 bg-white border border-surface-150 rounded-2xl text-center text-xs text-surface-400">
                  No active incidents. System healthy.
                </div>
              )}
            </div>



            {/* RCA Findings */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-700 text-surface-500 uppercase tracking-wider">Root Cause Analysis</span>
                {chaosRca?.chaos_active && !chaosRca?.pending && (
                  <span className="text-[10px] font-700 px-2 py-0.5 bg-brand-100 text-brand-700 rounded-full">Live · Current Chaos</span>
                )}
                {chaosRca && !chaosRca.chaos_active && (
                  <span className="text-[10px] font-600 px-2 py-0.5 bg-surface-100 text-surface-500 rounded-full">Most Recent</span>
                )}
              </div>

              {/* Chaos active but RCA not yet generated */}
              {chaosRca?.pending && (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl flex items-center gap-3">
                  <div className="w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                  <div>
                    <p className="text-xs font-700 text-amber-800">
                      Generating RCA for {chaosRca.chaos_type} chaos on {chaosRca.chaos_target}...
                    </p>
                    <p className="text-[11px] text-amber-600 mt-0.5">Waiting for alert triggers (~60s after chaos starts)</p>
                  </div>
                </div>
              )}

              {/* RCA found */}
              {chaosRca && !chaosRca.pending && chaosRca.root_cause && (
                <div className={`p-4 rounded-2xl space-y-2.5 shadow-md border ${
                  chaosRca.chaos_active
                    ? 'bg-gradient-to-r from-red-50 to-rose-50 border-red-200 text-red-950 shadow-red-500/5'
                    : 'bg-gradient-to-r from-surface-50 to-white border-surface-200 text-surface-800 shadow-surface-900/5'
                }`}>
                  <div className="flex justify-between items-start">
                    <div>
                      <span className={`text-[10px] font-800 uppercase tracking-wider leading-none ${
                        chaosRca.chaos_active ? 'text-red-500' : 'text-surface-500'
                      }`}>
                        {chaosRca.chaos_active ? `${chaosRca.chaos_type?.toUpperCase()} CHAOS · RCA Engine` : 'RCA Core Engine · Last Incident'}
                      </span>
                      <h4 className={`text-base font-800 mt-0.5 ${
                        chaosRca.chaos_active ? 'text-red-900' : 'text-surface-900'
                      }`}>{chaosRca.root_cause}</h4>
                    </div>
                    <span className={`px-2.5 py-0.5 text-xs font-800 rounded-full flex-shrink-0 border ${
                      chaosRca.chaos_active
                        ? 'bg-red-100/80 text-red-800 border-red-200'
                        : 'bg-surface-100 text-surface-700 border-surface-200'
                    }`}>
                      {Math.round((chaosRca.confidence_score ?? 0) * 100)}%
                    </span>
                  </div>
                  <p className={`text-xs leading-relaxed ${
                    chaosRca.chaos_active ? 'text-red-700' : 'text-surface-600'
                  }`}>{chaosRca.message}</p>
                  <div className={`flex items-center justify-between text-[10px] pt-2 border-t ${
                    chaosRca.chaos_active
                      ? 'border-red-200/50 text-red-500'
                      : 'border-surface-150 text-surface-400'
                  }`}>
                    <span>Affected: <strong>{chaosRca.affected_services}</strong></span>
                    <span className={`px-2 py-0.5 rounded-full font-700 ${
                      chaosRca.severity === 'Critical' ? 'bg-red-100 text-red-700' :
                      chaosRca.severity === 'Warning'  ? 'bg-amber-100 text-amber-700' :
                      'bg-surface-100 text-surface-600'
                    }`}>{chaosRca.severity ?? 'Info'}</span>
                  </div>
                </div>
              )}

              {/* Nothing at all */}
              {!chaosRca && (
                <div className="p-4 bg-white border border-surface-150 rounded-2xl text-center text-xs text-surface-400">
                  RCA idle. Start a simulation to generate incidents.
                </div>
              )}
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
