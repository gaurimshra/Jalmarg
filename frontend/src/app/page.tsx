'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Hotspot, Report } from '@/lib/types';
import FloodMap from '@/components/map/FloodMap';
import HotspotDetailPanel from '@/components/HotspotDetailPanel';

export default function DashboardOverview() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedHotspotId, setSelectedHotspotId] = useState<number | null>(null);
  const [mapRefreshTrigger, setMapRefreshTrigger] = useState(0);

  useEffect(() => {
    const loadData = async () => {
      try {
        const reps = await api.getReports();
        setReports(reps);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const activeReports = reports.length;
  const verifiedReports = reports.filter(r => r.verification_status === 'VERIFIED').length;

  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg shadow-sm">
          <p className="text-sm font-medium text-slate-400 capitalize">Active Reports</p>
          <div className="text-2xl font-bold text-teal-400 mt-2">{loading ? '--' : activeReports}</div>
        </div>
        <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg shadow-sm">
          <p className="text-sm font-medium text-slate-400 capitalize">Verified True</p>
          <div className="text-2xl font-bold text-blue-400 mt-2">{loading ? '--' : verifiedReports}</div>
        </div>
        <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg shadow-sm">
          <p className="text-sm font-medium text-slate-400 capitalize">Critical Risks</p>
          <div className="text-2xl font-bold text-rose-400 mt-2">{loading ? '--' : reports.filter(r => r.severity === 'CRITICAL').length}</div>
        </div>
        <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg shadow-sm">
          <p className="text-sm font-medium text-slate-400 capitalize">Total Nodes</p>
          <div className="text-2xl font-bold text-indigo-400 mt-2">{loading ? '--' : reports.length > 0 ? (reports.map(r => r.hotspot_id).filter((v, i, a) => v && a.indexOf(v) === i).length) : '--'}</div>
        </div>
      </div>
      
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 min-h-[400px]">
        <div className="lg:col-span-3 rounded-lg overflow-hidden border border-slate-800 shadow-sm relative">
           <FloodMap 
               onSelectHotspot={(id) => setSelectedHotspotId(id)} 
               refreshTrigger={mapRefreshTrigger}
           />
        </div>
        
        <div className="lg:col-span-1 flex flex-col h-[500px] lg:h-auto overflow-hidden">
           {selectedHotspotId ? (
              <HotspotDetailPanel 
                 hotspotId={selectedHotspotId}
                 onClose={() => setSelectedHotspotId(null)}
                 onRiskUpdated={() => setMapRefreshTrigger(prev => prev + 1)}
              />
           ) : (
              <div className="bg-slate-950 rounded-lg border border-slate-800 p-4 flex flex-col h-full">
                <h3 className="font-semibold text-slate-200 mb-3 border-b border-slate-800 pb-2">Recent Reports</h3>
                <div className="flex-1 overflow-auto space-y-3">
                   {loading ? (
                      <div className="text-sm text-slate-500 text-center py-4">Loading reports...</div>
                   ) : reports.length > 0 ? (
                      reports.map(r => (
                        <div key={r.id} className="p-3 bg-slate-900 border border-slate-700 rounded text-sm">
                          <div className="flex justify-between items-start mb-1">
                            <span className="font-medium text-teal-300">#{r.id} {r.is_simulated ? '(DEMO)' : ''}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded ${r.verification_status === 'VERIFIED' ? 'bg-blue-900 text-blue-300' : 'bg-slate-800 text-slate-300'}`}>
                              {r.verification_status}
                            </span>
                          </div>
                          <p className="text-slate-400 mb-2 truncate">{r.description || 'No description'}</p>
                          <div className="flex justify-between text-xs text-slate-500">
                            <span>Trust: {(r.trust_score * 100).toFixed(0)}%</span>
                            <span>{new Date(r.created_at).toLocaleTimeString()}</span>
                          </div>
                        </div>
                      ))
                   ) : (
                      <div className="text-sm text-slate-500 text-center py-4">No recent reports</div>
                   )}
                </div>
              </div>
           )}
        </div>
      </div>
    </div>
  )
}
