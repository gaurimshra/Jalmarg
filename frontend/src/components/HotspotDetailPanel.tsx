'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { WeatherSnapshot, RiskRecord } from '@/lib/types';

interface HotspotDetailPanelProps {
  hotspotId: number;
  onClose: () => void;
  onRiskUpdated: () => void;
}

export default function HotspotDetailPanel({ hotspotId, onClose, onRiskUpdated }: HotspotDetailPanelProps) {
  const [weather, setWeather] = useState<WeatherSnapshot | null>(null);
  const [riskHistory, setRiskHistory] = useState<RiskRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [wData, rData] = await Promise.all([
          api.getWeather(hotspotId).catch(() => null),
          api.getRiskHistory(hotspotId).catch(() => [])
        ]);
        if (active) {
          setWeather(wData);
          setRiskHistory(rData);
        }
      } catch (err: any) {
         if (active) setError(err.message || 'Failed to load details');
      } finally {
        if (active) setLoading(false);
      }
    };
    loadData();
    return () => { active = false; };
  }, [hotspotId]);

  const handleRecalculate = async () => {
    setRefreshing(true);
    setError(null);
    try {
      await api.refreshWeather(hotspotId);
      await api.recalculateRisk(hotspotId);
      const [wData, rData] = await Promise.all([
          api.getWeather(hotspotId),
          api.getRiskHistory(hotspotId)
      ]);
      setWeather(wData);
      setRiskHistory(rData);
      onRiskUpdated();
    } catch (err: any) {
      setError(err.message || 'Failed to recalculate risk');
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
     return (
       <div className="h-full flex flex-col p-4 bg-slate-950 rounded-lg border border-slate-800">
         <div className="flex justify-between items-center pb-2 border-b border-slate-800 mb-3">
            <h3 className="font-semibold text-slate-200">Hotspot Details</h3>
            <button onClick={onClose} className="text-slate-500 hover:text-slate-300">✕</button>
         </div>
         <div className="flex-1 flex items-center justify-center text-sm text-slate-500">Loading details...</div>
       </div>
     )
  }

  const latestRisk = riskHistory[0];

  return (
    <div className="h-full flex flex-col p-4 bg-slate-950 rounded-lg border border-slate-800 text-sm overflow-y-auto">
       <div className="flex justify-between items-center pb-2 border-b border-slate-800 mb-3">
          <h3 className="font-semibold text-slate-200">Hotspot Details</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300">✕</button>
       </div>

       {error && (
         <div className="bg-rose-950/50 border border-rose-900 text-rose-400 p-2 rounded mb-4 text-xs">
            {error}
         </div>
       )}

       {/* Rainfall Panel */}
       <div className="mb-5 bg-slate-900 border border-slate-800 p-3 rounded">
          <div className="flex justify-between items-center mb-2">
             <h4 className="font-medium text-slate-300">Rainfall Forecast</h4>
             {weather?.data_source && (
                 <span className={`text-[10px] px-1.5 py-0.5 rounded uppercase font-semibold ${weather.data_source === 'live' ? 'bg-indigo-900 text-indigo-300' : weather.data_source === 'cached' ? 'bg-slate-700 text-slate-300' : 'bg-rose-900 text-rose-300'}`}>
                    {weather.data_source}
                 </span>
             )}
          </div>
          {weather ? (
             <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                   <span className="text-slate-500">Current / Near Hour</span>
                   <span className="text-slate-200 font-medium">{weather.precipitation_values} mm</span>
                </div>
                <div className="flex justify-between">
                   <span className="text-slate-500">Next 3 Hours</span>
                   <span className="text-slate-200 font-medium">{weather.precip_next_3h} mm</span>
                </div>
                <div className="flex justify-between">
                   <span className="text-slate-500">Probability</span>
                   <span className="text-slate-200 font-medium">{weather.precipitation_probability}%</span>
                </div>
                <div className="flex justify-between">
                   <span className="text-slate-500">Last Update</span>
                   <span className="text-slate-400">{new Date(weather.retrieval_time).toLocaleTimeString()}</span>
                </div>
             </div>
          ) : (
             <div className="text-xs text-slate-500">No forecast data available.</div>
          )}
       </div>

       {/* Risk Panel */}
       <div className="mb-5 bg-slate-900 border border-slate-800 p-3 rounded">
          <h4 className="font-medium text-slate-300 mb-2">Flood Risk Analysis</h4>
          {latestRisk ? (
             <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                   <span className="text-slate-500">Composite Score</span>
                   <span className="text-slate-200 font-medium flex gap-2 items-center">
                     {latestRisk.risk_score} / 100
                     <span className={`text-[10px] px-1 py-0.5 rounded bg-slate-800 ${latestRisk.risk_category === 'CRITICAL' ? 'text-rose-400' : latestRisk.risk_category === 'HIGH' ? 'text-orange-400' : 'text-emerald-400'}`}>
                       {latestRisk.risk_category}
                     </span>
                   </span>
                </div>
                
                <div className="pt-2 mt-2 border-t border-slate-800">
                    <div className="text-[10px] text-slate-500 mb-1 font-semibold uppercase">Risk Contributors (0-100)</div>
                    <div className="flex justify-between"><span>Rainfall Signal (40%)</span><span className="text-slate-300">{latestRisk.rainfall_signal.toFixed(1)}</span></div>
                    <div className="flex justify-between"><span>Flood Evidence (30%)</span><span className="text-slate-300">{latestRisk.flood_evidence_signal.toFixed(1)}</span></div>
                    <div className="flex justify-between"><span>Baseline (20%)</span><span className="text-slate-300">{latestRisk.baseline_signal.toFixed(1)}</span></div>
                    <div className="flex justify-between"><span>Corroboration (10%)</span><span className="text-slate-300">{latestRisk.corroboration_signal.toFixed(1)}</span></div>
                </div>

                {latestRisk.uncertainty_note && (
                   <div className="mt-2 text-amber-500/80 bg-amber-950/30 p-1.5 rounded border border-amber-900/50">
                      <span className="font-semibold text-amber-500">Note: </span>
                      {latestRisk.uncertainty_note}
                   </div>
                )}
             </div>
          ) : (
             <div className="text-xs text-slate-500">No risk records available.</div>
          )}
       </div>

       <div className="mt-auto pt-4">
          <button 
             onClick={handleRecalculate}
             disabled={refreshing}
             className="w-full bg-teal-600/20 hover:bg-teal-600/30 text-teal-400 border border-teal-500/30 py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
          >
             {refreshing ? 'Recalculating...' : 'Refresh Weather & Risk'}
          </button>
       </div>
    </div>
  );
}
