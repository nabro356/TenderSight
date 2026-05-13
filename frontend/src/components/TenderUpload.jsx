import { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle2, Loader2, Sparkles, FileStack } from 'lucide-react';
import clsx from 'clsx';
import { uploadTender } from '../api';

const PROGRESS_STEPS = [
  "Initializing smart ingestion pipeline...",
  "Running document parsers across the bundle...",
  "Applying OCR fallback where needed...",
  "Building the combined tender workspace...",
  "Analyzing context for eligibility criteria...",
  "Finalizing briefing metadata and source trail..."
];

export default function TenderUpload({ onTenderProcessed }) {
  const [activeTab, setActiveTab] = useState('upload');
  const [files, setFiles] = useState([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [progressIndex, setProgressIndex] = useState(0);
  const [error, setError] = useState('');

  useEffect(() => {
    let interval;
    if (loading) {
      interval = setInterval(() => {
        setProgressIndex((prev) => (prev < PROGRESS_STEPS.length - 1 ? prev + 1 : prev));
      }, 2500);
    } else {
      setProgressIndex(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const handleUploadSubmit = async () => {
    if (!files.length) {
      setError('Please select at least one tender document.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const data = await uploadTender(files);
      onTenderProcessed(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to process tender bundle');
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
      const textFile = new File([blob], 'tender_bundle.txt', { type: 'text/plain' });
      const data = await uploadTender(textFile);
      onTenderProcessed(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to process tender text');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto mt-6 space-y-6">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-indigo-600">Bundle Intake</p>
        <h2 className="mt-3 text-4xl font-black text-slate-900 tracking-tight flex items-center gap-3">
          <Sparkles className="text-indigo-500" />
          Upload Tender Bundle
        </h2>
        <p className="mt-3 text-slate-600 max-w-3xl leading-relaxed">
          TenderSight now treats the tender as a bundle, not just a single PDF. Attach the RFP, BOQ,
          corrigendum, annexures, or support files together and generate a briefing-ready workspace.
        </p>
      </div>

      <div className="clean-card">
        <div className="mb-6 rounded-2xl border border-indigo-100 bg-indigo-50/60 p-4 text-sm text-indigo-900">
          Bundle → Extract → Evaluate → Publish. This upload stage creates the shared tender workspace,
          source metadata, and document trail used across the rest of the platform.
        </div>

        <div className="flex border-b border-slate-200 mb-6 relative z-10">
          <button
            className={clsx("px-4 py-3 font-semibold text-sm transition-colors", activeTab === 'upload' ? "text-indigo-600 border-b-2 border-indigo-600" : "text-slate-500 hover:text-slate-700")}
            onClick={() => setActiveTab('upload')}
          >
            <div className="flex items-center gap-2">
              <FileStack size={16} /> Upload Bundle
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

        <div className="relative z-10">
          {activeTab === 'upload' ? (
            <div className="space-y-4">
              <div className="border border-dashed border-slate-300 rounded-xl p-8 text-center hover:bg-slate-50/50 transition-colors bg-white/50">
                <input
                  type="file"
                  id="tender-file"
                  className="hidden"
                  multiple
                  accept=".txt,.pdf,.png,.jpg,.jpeg"
                  onChange={(e) => setFiles(Array.from(e.target.files || []))}
                />
                <label htmlFor="tender-file" className="cursor-pointer flex flex-col items-center">
                  <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mb-3">
                    <FileStack size={24} />
                  </div>
                  <span className="text-slate-700 font-bold">Click to upload one or more tender files</span>
                  <span className="text-slate-500 text-sm mt-1">PDF, TXT, or image files (PNG, JPG)</span>
                </label>
                {files.length > 0 && (
                  <div className="mt-5 space-y-3">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-full text-sm font-bold border border-indigo-100">
                      <CheckCircle2 size={16} /> {files.length} source document(s) selected
                    </div>
                    <div className="flex flex-wrap justify-center gap-2">
                      {files.map((file) => (
                        <span key={`${file.name}-${file.size}`} className="text-xs font-semibold bg-white border border-slate-200 rounded-full px-3 py-1 text-slate-600">
                          {file.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <button
                onClick={handleUploadSubmit}
                disabled={loading || !files.length}
                className="w-full py-3.5 px-4 btn-primary-wow disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-3"
              >
                {loading ? (
                  <div className="flex flex-col items-center gap-1">
                    <div className="flex items-center gap-2"><Loader2 className="animate-spin" size={18}/> Processing Bundle...</div>
                    <div className="text-xs font-normal opacity-80 animate-pulse-fast">{PROGRESS_STEPS[progressIndex]}</div>
                  </div>
                ) : (
                  <><Upload size={18}/> Create Tender Workspace</>
                )}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <textarea
                className="w-full h-56 p-4 border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-y text-slate-700 bg-white/50"
                placeholder="Paste the full tender text or merged bundle text here..."
                value={text}
                onChange={(e) => setText(e.target.value)}
              />

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
                  <><FileText size={18}/> Create Text-Based Workspace</>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
