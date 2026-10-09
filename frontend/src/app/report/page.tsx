'use client';
import { useState } from 'react';
import { Camera, MapPin, Upload } from 'lucide-react';

export default function ReportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [description, setDescription] = useState('');
  const [lat, setLat] = useState('');
  const [lng, setLng] = useState('');
  const [status, setStatus] = useState<'idle' | 'locating' | 'uploading' | 'success' | 'error'>('idle');
  const [reportResult, setReportResult] = useState<any>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
    }
  };

  const getLocation = () => {
    setStatus('locating');
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLat(pos.coords.latitude.toString());
          setLng(pos.coords.longitude.toString());
          setStatus('idle');
        },
        (err) => {
          console.error(err);
          setStatus('error');
        }
      );
    } else {
      setStatus('error');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !lat || !lng) return;
    setStatus('uploading');

    const formData = new FormData();
    formData.append('image', file);
    formData.append('latitude', lat);
    formData.append('longitude', lng);
    if (description) formData.append('description', description);

    try {
      const API_URl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URl}/api/reports/`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Upload failed');
      const data = await response.json();
      setReportResult(data);
      setStatus('success');
    } catch (err) {
      console.error(err);
      setStatus('error');
    }
  };

  if (status === 'success' && reportResult) {
    return (
      <div className="max-w-2xl mx-auto py-6">
        <div className="bg-slate-950 rounded-xl border border-teal-800 p-6">
           <h2 className="text-2xl font-bold text-teal-400 mb-4">Report Submitted Successfully</h2>
           
           <div className="space-y-4 text-slate-300">
             <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
                   <p className="text-sm font-semibold text-slate-400 mb-1">Verification Status</p>
                   <p className="font-bold">{reportResult.verification_status}</p>
                   <p className="text-xs text-slate-500 mt-2">Trust Score: {(reportResult.trust_score * 100).toFixed(0)}%</p>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
                   <p className="text-sm font-semibold text-slate-400 mb-1">Vision Analysis</p>
                   {reportResult.water_detected ? (
                      <p className="font-bold text-teal-300">Water Detected ({reportResult.severity})</p>
                   ) : (
                      <p className="font-bold text-slate-400">Analysis Inconclusive</p>
                   )}
                </div>
             </div>
             
             <div className="mt-4 border-t border-slate-800 pt-4">
               <button onClick={() => window.location.reload()} className="bg-teal-600 hover:bg-teal-700 font-medium px-4 py-2 rounded">Submit Another</button>
             </div>
           </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-6">
      <div className="mb-6 border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold text-white mb-1">Report Waterlogging</h1>
        <p className="text-slate-400 text-sm">Upload evidence securely to update real-time city routing patterns.</p>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-6 bg-slate-950 p-6 rounded-xl border border-slate-800">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Evidence Photo</label>
          <div className="flex items-center justify-center w-full">
            <label className="flex flex-col items-center justify-center w-full h-48 border-2 border-slate-700 border-dashed rounded-lg cursor-pointer bg-slate-900 hover:bg-slate-800 transition-colors relative overflow-hidden">
              {preview ? (
                <img src={preview} className="absolute inset-0 w-full h-full object-cover opacity-60" alt="Preview" />
              ) : (
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  <Upload className="w-8 h-8 mb-3 text-slate-400" />
                  <p className="mb-2 text-sm text-slate-400"><span className="font-semibold">Click to upload</span> or drag and drop</p>
                  <p className="text-xs text-slate-500">PNG, JPG or JPEG (MAX. 10MB)</p>
                </div>
              )}
              <input type="file" className="hidden" accept="image/jpeg,image/png" onChange={handleFileChange} />
            </label>
          </div>
        </div>

        <div>
           <label className="block text-sm font-medium text-slate-300 mb-2">Location Coordinates</label>
           <div className="flex space-x-3 mb-3">
             <button type="button" onClick={getLocation} className="flex-1 flex items-center justify-center px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-sm transition-colors text-slate-200">
                <MapPin className="w-4 h-4 mr-2" />
                {status === 'locating' ? 'Locating...' : 'Use Current Location'}
             </button>
           </div>
           <div className="grid grid-cols-2 gap-3">
             <input type="text" placeholder="Latitude" required value={lat} onChange={(e) => setLat(e.target.value)} className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-teal-500 outline-none" />
             <input type="text" placeholder="Longitude" required value={lng} onChange={(e) => setLng(e.target.value)} className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-teal-500 outline-none" />
           </div>
        </div>

        <div>
           <label className="block text-sm font-medium text-slate-300 mb-2">Description (Optional)</label>
           <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Provide any additional details..." className="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 text-sm text-slate-100 placeholder-slate-500 focus:border-teal-500 outline-none resize-none"></textarea>
        </div>

        <button type="submit" disabled={!file || !lat || !lng || status === 'uploading'} className="w-full bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-lg text-sm px-5 py-3 text-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center">
           {status === 'uploading' ? 'Analyzing and Verifying Source...' : 'Submit Report Verification'}
        </button>
      </form>
    </div>
  )
}
