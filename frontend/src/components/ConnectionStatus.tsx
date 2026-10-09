'use client';

import { useState, useEffect } from 'react';
import { Activity, WifiOff } from 'lucide-react';

export default function ConnectionStatus() {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');

  useEffect(() => {
    // In Phase 1, we just check if backend is reachable
    const checkHealth = async () => {
      try {
        const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${url}/api/health`, { signal: AbortSignal.timeout(3000) });
        if (res.ok) {
          setStatus('connected');
        } else {
          setStatus('disconnected');
        }
      } catch (err) {
        setStatus('disconnected');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000); // Check every 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center text-sm font-medium">
      {status === 'connected' ? (
        <div className="flex items-center text-teal-400 bg-teal-400/10 px-3 py-1.5 rounded-full border border-teal-400/20">
          <Activity className="w-4 h-4 mr-2" />
          API Connected
        </div>
      ) : status === 'connecting' ? (
        <div className="flex items-center text-yellow-400 bg-yellow-400/10 px-3 py-1.5 rounded-full border border-yellow-400/20">
          <Activity className="w-4 h-4 mr-2 animate-pulse" />
          Connecting...
        </div>
      ) : (
        <div className="flex items-center text-rose-400 bg-rose-400/10 px-3 py-1.5 rounded-full border border-rose-400/20">
          <WifiOff className="w-4 h-4 mr-2" />
          Backend Offline
        </div>
      )}
    </div>
  );
}
