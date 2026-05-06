import { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle2, Loader2, Sparkles } from 'lucide-react';
import clsx from 'clsx';
import { uploadTender } from '../api';

const PROGRESS_STEPS = [
  "Initializing smart ingestion pipeline...",
  "Running PyPDF parser...",
  "Applying Vision OCR fallback logic...",
  "Extracting unstructured raw text...",
  "Analyzing context for eligibility criteria...",
  "Finalizing tender document parsing..."
];

export default function TenderUpload({ onTenderProcessed }) {
  const [activeTab, setActiveTab] = useState('upload');
  const [file, setFile] = useState(null);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [progressIndex, setProgressIndex] = useState(0);
  const [error, setError] = useState('');

  useEffect(() => {
    let interval;
    if (loading) {
      interval = setInterval(() => {
        setProgressIndex((prev) => (prev < PROGRESS_STEPS.length - 1 ? prev + 1 : prev));
      }, 2500); // cycle through steps every 2.5s
    } else {
      setProgressIndex(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const handleUploadSubmit = async () => {
    if (!file) {
      setError('Please select a file first.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const data = await uploadTender(file);
      onTenderProcessed(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to process tender');
      setLoading(false);
    }
  };

  const handleTextSubmit = async () => {
    if (!text.trim()) {
      setError('Please paste the tender text first.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const blob = new Blob([text], { type: 'text/plain' });
      const textFile = new File([blob], 'tender.txt', { type: 'text/plain' });
      const data = await uploadTender(textFile);
      onTenderProcessed(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to process tender text');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto mt-8">
      <h2 className="text-2xl font-bold text-slate-800 mb-6 flex items-center gap-2">
        <Sparkles className="text-indigo-500" />
        Step 1: Upload Tender Document
      </h2>

      <div className="clean-card">
        {/* Tabs */}
        <div className="flex border-b border-slate-200 mb-6 relative z-10">
          <button
            className={clsx("px-4 py-3 font-semibold text-sm transition-colors", activeTab === 'upload' ? "text-indigo-600 border-b-2 border-indigo-600" : "text-slate-500 hover:text-slate-700")}
            onClick={() => setActiveTab('upload')}
          >
            <div className="flex items-center gap-2">
              <Upload size={16} /> Upload File
            </div>
          </button>
          <button
            className={clsx("px-4 py-3 font-semibold text-sm transition-colors", activeTab === 'paste' ? "text-indigo-600 border-b-2 border-indigo-600" : "text-slate-500 hover:text-slate-700")}
            onClick={() => setActiveTab('paste')}
          >
            <div className="flex items-center gap-2">
              <FileText size={16} /> Paste Text
            </div>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm relative z-10">
            {error}
          </div>
        )}

        {/* Tab Content */}
        <div className="relative z-10">
          {activeTab === 'upload' ? (
            <div className="space-y-4">
              <div className="border border-dashed border-slate-300 rounded-xl p-8 text-center hover:bg-slate-50/50 transition-colors bg-white/50">
                <input 
                  type="file" 
                  id="tender-file" 
                  className="hidden" 
                  accept=".txt,.pdf"
                  onChange={(e) => setFile(e.target.files[0])}
                />
                <label htmlFor="tender-file" className="cursor-pointer flex flex-col items-center">
                  <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mb-3">
                    <Upload size={24} />
                  </div>
                  <span className="text-slate-700 font-bold">Click to upload a document</span>
                  <span className="text-slate-500 text-sm mt-1">PDF or TXT files only</span>
                </label>
                {file && (
                  <div className="mt-4 inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-full text-sm font-bold border border-indigo-100">
                    <CheckCircle2 size={16} /> {file.name}
                  </div>
                )}
              </div>
              
              <button 
                onClick={handleUploadSubmit}
                disabled={loading || !file}
                className="w-full py-3.5 px-4 btn-primary-wow disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-3"
              >
                {loading ? (
                  <div className="flex flex-col items-center gap-1">
                    <div className="flex items-center gap-2"><Loader2 className="animate-spin" size={18}/> Processing Document...</div>
                    <div className="text-xs font-normal opacity-80 animate-pulse-fast">{PROGRESS_STEPS[progressIndex]}</div>
                  </div>
                ) : (
                  <><Upload size={18}/> Submit Tender Document</>
                )}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <textarea
                className="w-full h-48 p-4 border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-y text-slate-700 bg-white/50"
                placeholder="Paste the full tender document text here..."
                value={text}
                onChange={(e) => setText(e.target.value)}
              ></textarea>
              
              <button 
                onClick={handleTextSubmit}
                disabled={loading || !text.trim()}
                className="w-full py-3.5 px-4 btn-primary-wow disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-3"
              >
                {loading ? (
                  <div className="flex flex-col items-center gap-1">
                    <div className="flex items-center gap-2"><Loader2 className="animate-spin" size={18}/> Processing Text...</div>
                    <div className="text-xs font-normal opacity-80 animate-pulse-fast">{PROGRESS_STEPS[progressIndex]}</div>
                  </div>
                ) : (
                  <><FileText size={18}/> Submit Text</>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
