'use client';
import { useState, useRef, useEffect } from 'react';
import { api } from '@/lib/api';
import type { RouteCompareRequest, RouteCompareResponse, RouteCandidate } from '@/lib/types';

// Pre-defined coordinates for demo 
const LOCATIONS = [
  { name: 'Minto Bridge', lat: 28.6320, lng: 77.2250 },
  { name: 'ITO Intersection', lat: 28.6290, lng: 77.2430 },
  { name: 'Connaught Place', lat: 28.6304, lng: 77.2177 },
  { name: 'India Gate', lat: 28.6129, lng: 77.2295 }
];

export default function PlannerPage() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const [mapReady, setMapReady] = useState(false);

  const [origin, setOrigin] = useState(LOCATIONS[1].name); // Default ITO
  const [destination, setDestination] = useState(LOCATIONS[0].name); // Default Minto
  const [vehicle, setVehicle] = useState('Hatchback');
  const [strategy, setStrategy] = useState('fastest');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<RouteCandidate[]>([]);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);

  // Initialize Map
  useEffect(() => {
    let map: any = null;
    const initMap = async () => {
      if (!mapContainer.current || mapRef.current) return;
      try {
        const maplibregl = await import('maplibre-gl');
        await import('maplibre-gl/dist/maplibre-gl.css');
        maplibregl.setWorkerUrl('/maplibre-gl-worker.mjs');

        map = new maplibregl.Map({
          container: mapContainer.current!,
          style: 'https://tiles.openfreemap.org/styles/liberty',
          center: [77.209, 28.6139],
          zoom: 11,
        });

        map.on('load', () => setMapReady(true));
        mapRef.current = map;
      } catch (err) {
        console.error('Failed to init map', err);
      }
    };
    initMap();
    return () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } };
  }, []);

  const handleFetchRoutes = async () => {
    setLoading(true);
    setError(null);
    const originLoc = LOCATIONS.find(l => l.name === origin);
    const destLoc = LOCATIONS.find(l => l.name === destination);
    if (!originLoc || !destLoc) {
        setError("Invalid locations");
        setLoading(false);
        return;
    }

    try {
        const payload: RouteCompareRequest = {
            origin: { lat: originLoc.lat, lng: originLoc.lng },
            destination: { lat: destLoc.lat, lng: destLoc.lng },
            vehicle_type: vehicle,
            strategy: strategy
        };
        const res = await api.compareRoutes(payload);
        setCandidates(res.candidates);
        if (res.candidates.length > 0) {
           setSelectedRouteId(res.candidates[0].id);
           drawRoutes(res.candidates);
        } else {
           drawRoutes([]);
        }
    } catch (err: any) {
        setError(err.message || 'Failed to fetch routes');
    } finally {
        setLoading(false);
    }
  };

  const drawRoutes = (routes: RouteCandidate[]) => {
      if (!mapRef.current || !mapReady) return;
      const map = mapRef.current;
      
      // Remove previous route layers and sources
      const prevSourceIds = ['route_0', 'route_1', 'route_2'];
      for (const sid of prevSourceIds) {
          if (map.getLayer(sid + '_outline')) map.removeLayer(sid + '_outline');
          if (map.getLayer(sid)) map.removeLayer(sid);
          if (map.getSource(sid)) map.removeSource(sid);
      }
      
      if (!routes.length) return;

      const maplibregl = require('maplibre-gl');
      
      // Draw new routes (drawing safest / selected ones slightly differently if we wanted to, 
      // but for now let's draw them all, putting fastest/safest in different colors)
      
      // We will sort so that the safest/fastest is drawn on top
      routes.forEach((route, idx) => {
          const sid = `route_${idx}`;
          const isWarning = route.exposure_score > 10;
          const routeColor = route.ranking.includes('Safer') ? '#10b981' : (isWarning ? '#f43f5e' : '#3b82f6');
          
          map.addSource(sid, { type: 'geojson', data: route.geometry });
          
          // Outline
          map.addLayer({
              id: sid + '_outline', type: 'line', source: sid,
              layout: { 'line-join': 'round', 'line-cap': 'round' },
              paint: { 'line-color': '#0f172a', 'line-width': 8 }
          });
          
          // Inner line
          map.addLayer({
              id: sid, type: 'line', source: sid,
              layout: { 'line-join': 'round', 'line-cap': 'round' },
              paint: { 'line-color': routeColor, 'line-width': 5 }
          });
      });

      // Fit bounds roughly around first route
      try {
          const coords = routes[0].geometry.coordinates;
          const bounds = coords.reduce((bounds: any, coord: any) => bounds.extend(coord), new maplibregl.LngLatBounds(coords[0], coords[0]));
          map.fitBounds(bounds, { padding: 40 });
      } catch (e) {}
  };

  return (
    <div className="max-w-6xl mx-auto py-6 h-full flex flex-col">
      <div className="mb-4 border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold text-white mb-1">Vehicle-Aware Routing</h1>
        <p className="text-slate-400">Find routes dynamically evaluated against live urban waterlogging risks.</p>
      </div>
      
      <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-6 min-h-[500px]">
        <div className="md:col-span-1 flex flex-col space-y-4">
          
          {/* Controls */}
          <div className="bg-slate-950 rounded-xl border border-slate-800 p-4">
            <h3 className="font-medium text-white mb-3 text-sm border-b border-slate-800 pb-2">Route Parameters</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Origin</label>
                <select className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-slate-200 focus:outline-none focus:border-teal-500" value={origin} onChange={e => setOrigin(e.target.value)}>
                   {LOCATIONS.map(l => <option key={l.name} value={l.name}>{l.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Destination</label>
                <select className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-slate-200 focus:outline-none focus:border-teal-500" value={destination} onChange={e => setDestination(e.target.value)}>
                   {LOCATIONS.map(l => <option key={l.name} value={l.name}>{l.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Vehicle Type</label>
                <select className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-slate-200 focus:outline-none focus:border-teal-500" value={vehicle} onChange={e => setVehicle(e.target.value)}>
                   <option value="Bike">Bike (High Vulnerability)</option>
                   <option value="Hatchback">Hatchback (High Vulnerability)</option>
                   <option value="Sedan">Sedan (Medium Vulnerability)</option>
                   <option value="SUV">SUV (Low Vulnerability)</option>
                </select>
              </div>
              <button 
                  onClick={handleFetchRoutes} 
                  disabled={loading}
                  className="w-full bg-teal-600 hover:bg-teal-700 text-white rounded py-2 font-medium mt-1 text-sm transition-colors disabled:opacity-50">
                {loading ? 'Evaluating Routes...' : 'Calculate Safe Route'}
              </button>
            </div>
          </div>

          {/* Error */}
          {error && (
             <div className="bg-rose-950/40 border border-rose-900/50 text-rose-400 p-3 rounded text-sm">
                 {error}
             </div>
          )}

          {/* Results */}
          <div className="bg-slate-950 rounded-xl border border-slate-800 p-4 flex-1 overflow-y-auto">
             <h3 className="font-medium text-white mb-3 text-sm border-b border-slate-800 pb-2">Route Candidates</h3>
             <div className="space-y-3">
                 {candidates.length === 0 && !loading && (
                    <p className="text-xs text-slate-500 text-center py-4">No candidates. Try clicking Calculate Route.</p>
                 )}
                 {candidates.map((c, i) => (
                    <div 
                         key={c.id} 
                         onClick={() => setSelectedRouteId(c.id)}
                         className={`p-3 rounded border text-sm cursor-pointer transition-colors ${selectedRouteId === c.id ? 'bg-slate-900 border-teal-500/50' : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'}`}>
                         
                         <div className="flex justify-between items-start mb-1">
                             <span className="font-medium text-slate-200">{c.ranking}</span>
                             <span className="text-slate-400 text-xs">{Math.ceil(c.duration_sec / 60)} min</span>
                         </div>
                         <p className="text-xs text-slate-400 mb-2">{c.explanation}</p>
                         
                         {c.source === 'DEMO Fallback' && (
                             <span className="inline-block px-1.5 py-0.5 rounded bg-amber-900/40 text-amber-500 text-[10px] uppercase font-bold mb-2">Simulated Demo</span>
                         )}

                         <div className="flex justify-between items-center bg-slate-950 p-2 rounded border border-slate-800">
                             <span className="text-xs text-slate-500">Flood Exposure Score</span>
                             <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${c.exposure_score > 30 ? 'bg-rose-950 text-rose-400' : c.exposure_score > 10 ? 'bg-orange-950 text-orange-400' : 'bg-emerald-950 text-emerald-400'}`}>
                                {c.exposure_score.toFixed(1)} / 100
                             </span>
                         </div>

                         {c.hazards.length > 0 && (
                            <div className="mt-2 text-xs text-rose-400 bg-rose-950/20 p-2 rounded">
                                <span className="font-bold">Hazards along route: </span>
                                {c.hazards.map(h => `${h.name} (Risk ${h.risk.toFixed(0)})`).join(', ')}
                            </div>
                         )}
                    </div>
                 ))}
             </div>
          </div>
        </div>
        
        {/* Map */}
        <div className="md:col-span-2 bg-slate-950 rounded-xl border border-slate-800 relative overflow-hidden">
           <div ref={mapContainer} className="w-full h-full" />
           {!mapReady && (
              <div className="absolute inset-0 bg-slate-950 flex flex-col items-center justify-center">
                 <div className="w-8 h-8 border-2 border-teal-400 border-t-transparent rounded-full animate-spin mb-3"></div>
                 <p className="text-sm text-slate-400">Loading MapLibre...</p>
              </div>
           )}
        </div>
      </div>
    </div>
  )
}
