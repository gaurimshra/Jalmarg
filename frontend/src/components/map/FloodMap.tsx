'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import type { MapOverviewMarker } from '@/lib/types';

const RISK_COLORS: Record<string, string> = {
  CRITICAL: '#f43f5e',
  HIGH: '#fb923c',
  MODERATE: '#fbbf24',
  LOW: '#10b981',
};

interface FloodMapProps {
  onSelectHotspot?: (hotspotId: number) => void;
  refreshTrigger?: number; // whenever this number changes, re-fetch markers
}

export default function FloodMap({ onSelectHotspot, refreshTrigger = 0 }: FloodMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]); // To reliably clear markers
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');

  const fetchAndRenderMarkers = useCallback(async () => {
    if (!mapRef.current) return;
    try {
      const maplibregl = await import('maplibre-gl');
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const res = await fetch(`${API_BASE}/api/map/overview`);
      if (!res.ok) throw new Error('Failed to fetch map data');
      const json = await res.json();
      const markers: MapOverviewMarker[] = json.data || [];

      // Clear existing markers
      markersRef.current.forEach(m => m.remove());
      markersRef.current = [];

      markers.forEach((marker) => {
        const el = document.createElement('div');
        const color = RISK_COLORS[marker.risk_level] || RISK_COLORS.LOW;
        el.style.cssText = `
          width: 18px; height: 18px; border-radius: 50%;
          background: ${color}; border: 2px solid #0f172a;
          box-shadow: 0 0 0 3px ${color}33; cursor: pointer;
        `;

        if (onSelectHotspot) {
          el.addEventListener('click', (e) => {
               e.stopPropagation();
               onSelectHotspot(marker.id);
          });
        }

        const popupHTML = `
          <div style="min-width:200px;padding:8px;font-family:sans-serif;">
            <p style="font-weight:bold;margin:0 0 6px;font-size:14px;color:#333;">${marker.name}</p>
            <table style="width:100%;font-size:12px;border-collapse:collapse;">
              <tr><td style="color:#666;padding:2px 0;">Risk Level</td><td style="font-weight:600;color:${color};">${marker.risk_level}</td></tr>
              <tr><td style="color:#666;padding:2px 0;">Score</td><td style="color:#333;">${marker.current_risk.toFixed(0)}/100</td></tr>
              <tr><td style="color:#666;padding:2px 0;">Source</td><td style="color:#666;font-size:10px;background:#f0f9ff;padding:1px 4px;border-radius:3px;">${marker.is_simulated ? 'DEMO SCENARIO' : 'LIVE DATA'}</td></tr>
            </table>
            <p style="margin:8px 0 0;font-size:11px;color:#888;text-align:center;">Click marker to view details</p>
          </div>
        `;

        const popup = new maplibregl.Popup({ offset: 14, closeButton: true })
          .setHTML(popupHTML);

        const newMarker = new maplibregl.Marker({ element: el })
          .setLngLat(marker.coordinates)
          .setPopup(popup)
          .addTo(mapRef.current);
          
        markersRef.current.push(newMarker);
      });
    } catch (e) {
      console.error(e);
      setError('Map data unavailable — backend may be offline.');
    }
  }, [onSelectHotspot]);

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
          zoom: 10,
        });

        mapRef.current = map;

        map.on('load', async () => {
          setStatus('ready');
          await fetchAndRenderMarkers();
        });

        map.on('error', () => {
          setError('Map tiles failed to load. Check your internet connection.');
          setStatus('error');
        });
      } catch (e) {
        setError('Map could not be initialized.');
        setStatus('error');
      }
    };

    initMap();

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [fetchAndRenderMarkers]);

  // Handle external refresh trigger
  useEffect(() => {
    if (status === 'ready') {
      fetchAndRenderMarkers();
    }
  }, [refreshTrigger, status, fetchAndRenderMarkers]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="w-full h-full" />

      {status === 'loading' && !error && (
        <div className="absolute inset-0 bg-slate-950 flex items-center justify-center rounded-xl border border-slate-800">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-teal-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-slate-400">Loading map tiles…</p>
          </div>
        </div>
      )}

      {error && (
        <div className="absolute bottom-4 left-4 right-4 bg-slate-950/90 border border-rose-800 rounded-lg p-3 flex items-start gap-3">
          <div className="flex-1">
            <p className="text-xs font-semibold text-rose-400 mb-0.5">Map Notice</p>
            <p className="text-xs text-slate-300">{error}</p>
          </div>
          <button
            onClick={() => { setError(null); window.location.reload(); }}
            className="text-xs text-teal-400 underline whitespace-nowrap mt-0.5"
          >
            Retry
          </button>
        </div>
      )}

      {status === 'ready' && (
        <div className="absolute top-3 right-3 bg-slate-950/90 border border-slate-700 rounded-lg p-3 text-xs space-y-1.5 z-10 pointer-events-none">
          <p className="font-semibold text-slate-300 mb-2">Risk Level</p>
          {Object.entries(RISK_COLORS).map(([level, color]) => (
            <div key={level} className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full inline-block flex-shrink-0" style={{ background: color }} />
              <span className="text-slate-400">{level}</span>
            </div>
          ))}
          <div className="border-t border-slate-700 mt-2 pt-2 text-[10px] text-slate-500">OpenFreeMap · No API key</div>
        </div>
      )}
    </div>
  );
}
