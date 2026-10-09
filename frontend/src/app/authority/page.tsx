'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { AgentEvent, DispatchPlan } from '@/lib/types';

export default function DashboardPage() {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [plans, setPlans] = useState<DispatchPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [actioningPlanId, setActioningPlanId] = useState<number | null>(null);

  const loadData = async () => {
    try {
      const [evData, pData] = await Promise.all([
        api.getAgentEvents(),
        api.getDispatchPlans()
      ]);
      setEvents(evData);
      setPlans(pData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (planId: number, status: string) => {
    try {
      setActioningPlanId(planId);
      await api.updateDispatchPlanStatus(planId, status);
      await loadData();
    } catch (e) {
      console.error("Failed to action plan", e);
      alert("Error saving action.");
    } finally {
      setActioningPlanId(null);
    }
  };

  return (
    <div className="py-4 h-full flex flex-col">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Authority Dashboard</h1>
          <p className="text-slate-400">Review aggregated reports, agent decisions, and dispatch proposals.</p>
        </div>
        <div className="flex space-x-3">
          <div className="bg-slate-950 border border-slate-800 px-4 py-2 rounded-lg text-center">
             <span className="block text-xs text-slate-500 font-medium uppercase">Execution Engine</span>
             <span className={`block text-sm font-bold mt-1 ${events[0]?.event_type === 'FALLBACK_INIT' || events[0]?.event_type === 'ERROR' ? 'text-amber-400' : 'text-teal-400'}`}>
                {events[0]?.event_type.includes('FALLBACK') ? 'DETERMINISTIC FALLBACK' : 'STRANDS + GEMINI'}
             </span>
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-0">
        <div className="bg-slate-950 rounded-xl border border-slate-800 p-5 flex flex-col h-[600px]">
           <h3 className="font-semibold text-slate-200 mb-4 border-b border-slate-800 pb-3">Pending Approvals</h3>
           <div className="flex-1 overflow-y-auto space-y-3">
             {loading && plans.length === 0 ? (
                <div className="flex items-center justify-center h-full text-slate-500 text-sm">Loading plans...</div>
             ) : plans.length === 0 ? (
                <div className="flex items-center justify-center h-full text-slate-500 text-sm">No pending human approvals.</div>
             ) : (
                plans.map(p => (
                   <div key={p.id} className="bg-slate-900 border border-slate-700 rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                         <span className="font-bold text-slate-200">Hotspot #{p.hotspot_id}</span>
                         <span className={`text-[10px] px-2 py-1 rounded font-bold ${
                           p.status === 'PROPOSED' ? 'bg-amber-900/50 text-amber-400' :
                           p.status === 'APPROVED' ? 'bg-teal-900/50 text-teal-400' : 
                           'bg-rose-900/50 text-rose-400'
                         }`}>
                           {p.status}
                         </span>
                      </div>
                      <div className="mb-3 text-sm">
                         <strong className="text-slate-400">Action:</strong> <span className="text-slate-200">{p.suggested_action}</span>
                      </div>
                      <div className="mb-4 text-xs text-slate-400 bg-slate-950 border border-slate-800 p-2 rounded">
                         <strong>Rationale:</strong> {p.explanation}
                      </div>
                      
                      {p.status === 'PROPOSED' && (
                         <div className="flex space-x-3 mt-4 border-t border-slate-800 pt-3">
                           <button 
                             onClick={() => handleAction(p.id, 'APPROVED')}
                             disabled={actioningPlanId === p.id}
                             className="flex-1 bg-teal-600 hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium py-2 px-4 rounded transition-colors"
                           >
                             Approve
                           </button>
                           <button 
                             onClick={() => handleAction(p.id, 'REJECTED')}
                             disabled={actioningPlanId === p.id}
                             className="flex-1 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-slate-200 text-sm font-medium py-2 px-4 rounded transition-colors"
                           >
                             Reject
                           </button>
                         </div>
                      )}
                      
                      {p.status !== 'PROPOSED' && (
                         <div className="mt-2 text-xs text-slate-500 flex justify-between">
                            <span>Actioned by: {p.approved_by || 'Unknown'}</span>
                            <span>{new Date(p.approved_at!).toLocaleString()}</span>
                         </div>
                      )}
                   </div>
                ))
             )}
           </div>
        </div>
        
        <div className="bg-slate-950 rounded-xl border border-slate-800 p-5 flex flex-col h-[600px] overflow-hidden">
           <div className="flex justify-between items-center mb-4 border-b border-slate-800 pb-3">
               <h3 className="font-semibold text-slate-200">Agent Activity Timeline</h3>
               <span className="text-xs text-slate-500">{events.length} events logged</span>
           </div>
           
           <div className="flex-1 overflow-y-auto pr-2 space-y-4">
             {loading && events.length === 0 ? (
                 <div className="flex items-center justify-center h-full text-slate-500 text-sm">Loading...</div>
             ) : events.length === 0 ? (
                 <div className="flex items-center justify-center h-full text-slate-500 text-sm">No activity recorded.</div>
             ) : (
                 events.map((ev) => (
                     <div key={ev.id} className="relative pl-6 before:inline-block before:absolute before:left-2 before:top-2 before:h-2 before:w-2 before:rounded-full before:bg-teal-500 after:absolute after:left-[11px] after:top-5 after:bottom-[-20px] after:w-px after:bg-slate-800 last:after:hidden">
                         <div className="bg-slate-900 border border-slate-800 rounded p-3 text-sm flex flex-col items-start gap-1">
                             <div className="flex justify-between w-full">
                                <span className={`font-bold ${ev.source_kind === 'HUMAN' ? 'text-blue-400' : 'text-teal-300'}`}>
                                   {ev.agent_name} <span className="text-slate-500 font-normal">via</span> {ev.tool_name}
                                </span>
                                <span className="text-[10px] text-slate-500">{new Date(ev.created_at).toLocaleTimeString()}</span>
                             </div>
                             
                             <div className="flex items-center space-x-2 mt-1 mb-2">
                                <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium uppercase ${ev.event_type.includes('FALLBACK') ? 'bg-rose-950 text-rose-400' : ev.source_kind === 'HUMAN' ? 'bg-blue-900/50 text-blue-300' : 'bg-slate-800 text-slate-300'}`}>
                                   {ev.event_type}
                                </span>
                                {ev.report_id && (
                                   <span className="text-[10px] text-slate-400">Report #{ev.report_id}</span>
                                )}
                             </div>
                             
                             {ev.event_type === 'CIVIC_GUIDANCE' ? (
                               <div className="mt-1 w-full bg-slate-950 p-2 rounded border border-slate-700">
                                  <div className="flex flex-col">
                                    <span className="text-xs text-blue-400 font-semibold mb-1">
                                      {(() => {
                                         try { return JSON.parse(ev.summary).title || 'Guidance'; } 
                                         catch(e) { return 'Guidance'; } 
                                      })()}
                                    </span>
                                    <span className="text-[10px] text-slate-400 leading-tight">
                                      {(() => {
                                         try { return JSON.parse(ev.summary).rationale || ''; } 
                                         catch(e) { return ''; } 
                                      })()}
                                    </span>
                                    <div className="mt-2 text-xs text-slate-300 italic border-l-2 border-slate-700 pl-2">
                                      {(() => {
                                         try { return JSON.parse(ev.summary).content_preview || ev.summary; } 
                                         catch(e) { return ev.summary; } 
                                      })()}
                                    </div>
                                    <span className="mt-2 text-[10px] inline-block bg-blue-900/30 text-blue-400 px-1 py-0.5 rounded w-max">
                                      General Guidance (Not Incident Evidence)
                                    </span>
                                  </div>
                               </div>
                             ) : (
                               <p className="text-slate-300 text-xs">{ev.summary}</p>
                             )}
                         </div>
                     </div>
                 ))
             )}
           </div>
        </div>
      </div>
    </div>
  )
}
