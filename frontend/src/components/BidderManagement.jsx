import { useState, useEffect, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Plus, Users, Trash2, ArrowRight, Loader2, FileCheck, ClipboardList, PlusCircle, BookOpen, Hash, Tag } from 'lucide-react';
import clsx from 'clsx';
import { evaluateAllBidders, connectEvalStream } from '../api';

export default function BidderManagement({ tenderId, criteria, setCriteria, bidders, setBidders, onEvaluationComplete }) {
  const [activeTab, setActiveTab] = useState('upload');
  const [bidderName, setBidderName] = useState('');
  const [files, setFiles] = useState([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState('');
  const [evalProgress, setEvalProgress] = useState('');
  const [progressIndex, setProgressIndex] = useState(0);
  const [selectedCriterion, setSelectedCriterion] = useState(null);
  const [showAddCriteria, setShowAddCriteria] = useState(false);
  const [newCriterion, setNewCriterion] = useState({ text: '', type: 'Technical', mandatory: true });
  // Track which bidders have completed evaluation (SSE-driven)
  const [completedBidders, setCompletedBidders] = useState(new Set());
  const eventSourceRef = useRef(null);

  const PROGRESS_STEPS = [
    "Parsing bidder document structures...",
    "Extracting quantitative entities...",
    "Cross-referencing against mandatory criteria...",
    "Validating evidence passages...",
    "Generating compliance verdicts...",
    "Finalizing bidder evaluation profiles..."
  ];

  useEffect(() => {
    let interval;
    if (evaluating) {
      interval = setInterval(() => {
        setProgressIndex((prev) => (prev < PROGRESS_STEPS.length - 1 ? prev + 1 : prev));
      }, 3000);
    } else {
      setProgressIndex(0);
    }
    return () => clearInterval(interval);
  }, [evaluating]);

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const typeColors = {
    "Financial": "border-blue-500 bg-blue-50 text-blue-700",
    "Experience": "border-emerald-500 bg-emerald-50 text-emerald-700",
    "Compliance": "border-amber-500 bg-amber-50 text-amber-700",
    "Technical": "border-purple-500 bg-purple-50 text-purple-700"
  };

  const handleAddBidder = async () => {
    if (!bidderName.trim()) {
      setError('Please enter a bidder name');
      return;
    }
    
    if (activeTab === 'upload' && files.length === 0) {
      setError('Please upload at least one file');
      return;
    }
    if (activeTab === 'paste' && !text.trim()) {
      setError('Please paste text');
      return;
    }
    
    const newContents = [];
    if (activeTab === 'upload') {
      for (const f of files) {
        newContents.push({ type: 'upload', data: f, label: f.name });
      }
    } else {
      newContents.push({ type: 'paste', data: text, label: 'Pasted Text Document' });
    }
    
    const existingIndex = bidders.findIndex(b => b.name === bidderName.trim());
    
    if (existingIndex >= 0) {
      const updatedBidders = [...bidders];
      updatedBidders[existingIndex].contents.push(...newContents);
      setBidders(updatedBidders);
    } else {
      setBidders(prev => [...prev, {
        name: bidderName.trim(),
        contents: newContents
      }]);
    }
    
    // Clear file inputs but KEEP bidder name for adding more docs
    // setBidderName('');  -- intentionally kept so user can add more files to same bidder
    setFiles([]);
    if (activeTab === 'upload') {
      const fileInput = document.getElementById('bidder-file');
      if (fileInput) fileInput.value = '';
    }
    setText('');
    setError('');
  };

  const handleRemoveBidder = (index) => {
    setBidders(prev => prev.filter((_, i) => i !== index));
  };

  const handleEvaluate = async () => {
    if (bidders.length === 0) return;
    setEvaluating(true);
    setError('');
    setCompletedBidders(new Set());
    
    try {
      // 1. Connect SSE stream FIRST so we get live per-bidder updates
      setEvalProgress(`Evaluating all ${bidders.length} bidders concurrently...`);
      const es = connectEvalStream(tenderId, (data) => {
        // SSE fires as each bidder completes on the backend
        setCompletedBidders(prev => new Set([...prev, data.bidder]));
        setEvalProgress(`✅ ${data.bidder} — ${data.status.replace('_', ' ')}`);
      });
      eventSourceRef.current = es;

      // 2. Fire the single bulk evaluation request (all bidders evaluated concurrently)
      const result = await evaluateAllBidders(tenderId, bidders);

      // 3. Clean up SSE
      es.close();
      eventSourceRef.current = null;

      // 4. Pass results to the parent
      onEvaluationComplete(
        result.evaluations || {},
        result.cartel_alerts || [],
      );
    } catch (err) {
      setError(`Evaluation failed: ${err.message}`);
      setEvaluating(false);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    }
  };

  return (
    <div className="max-w-5xl mx-auto mt-8 space-y-8">
      {/* Criteria Section */}
      <div>
        <h2 className="text-2xl font-bold text-slate-800 mb-6 flex items-center gap-2">
          <FileCheck className="text-emerald-500" />
          Step 2: Review Criteria & Add Bidders
        </h2>
        
        <div className="clean-card bg-slate-50/30 border-dashed">
          <h3 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <ClipboardList className="text-slate-500" size={20} /> {criteria.length} Eligibility Criteria Extracted
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {criteria.map((c, idx) => (
              <div 
                key={idx} 
                onClick={() => setSelectedCriterion(c)}
                className={clsx("p-4 rounded-xl border-l-4 bg-white shadow-sm cursor-pointer hover:shadow-md transition-all hover:scale-[1.01]", typeColors[c.type] || "border-slate-400")}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="font-bold text-slate-800">{c.id}</div>
                  <span className={clsx("text-xs font-bold px-2 py-1 rounded-md bg-opacity-20", typeColors[c.type])}>
                    {c.type}
                  </span>
                </div>
                <p className="text-sm text-slate-600 line-clamp-3" title={c.text}>{c.text}</p>
                {c.mandatory && <div className="mt-2 text-xs font-semibold text-emerald-600 flex items-center gap-1"><CheckCircle2 size={14}/> Mandatory</div>}
                {c.source_section && <div className="mt-1 text-xs text-slate-400 flex items-center gap-1"><BookOpen size={12}/> Section {c.source_section}</div>}
              </div>
            ))}
          </div>

          {/* Add Custom Criterion */}
          {showAddCriteria ? (
            <div className="mt-6 p-5 bg-white rounded-xl border-2 border-indigo-200 shadow-sm">
              <h4 className="font-bold text-slate-800 mb-3 flex items-center gap-2"><PlusCircle size={16} className="text-indigo-500"/> Add Custom Criterion</h4>
              <div className="space-y-3">
                <textarea
                  className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none resize-y text-sm"
                  placeholder="Describe the eligibility criterion..."
                  rows={2}
                  value={newCriterion.text}
                  onChange={(e) => setNewCriterion(prev => ({...prev, text: e.target.value}))}
                />
                <div className="flex items-center gap-3">
                  <select
                    className="p-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                    value={newCriterion.type}
                    onChange={(e) => setNewCriterion(prev => ({...prev, type: e.target.value}))}
                  >
                    <option value="Financial">Financial</option>
                    <option value="Experience">Experience</option>
                    <option value="Compliance">Compliance</option>
                    <option value="Technical">Technical</option>
                  </select>
                  <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={newCriterion.mandatory}
                      onChange={(e) => setNewCriterion(prev => ({...prev, mandatory: e.target.checked}))}
                      className="rounded"
                    />
                    Mandatory
                  </label>
                  <div className="ml-auto flex gap-2">
                    <button
                      onClick={() => { setShowAddCriteria(false); setNewCriterion({ text: '', type: 'Technical', mandatory: true }); }}
                      className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                    >Cancel</button>
                    <button
                      disabled={!newCriterion.text.trim()}
                      onClick={() => {
                        const customId = `CUSTOM-${criteria.filter(c => c.id?.startsWith('CUSTOM')).length + 1}`;
                        setCriteria([...criteria, { id: customId, text: newCriterion.text.trim(), type: newCriterion.type, mandatory: newCriterion.mandatory, source_section: 'Manual', sub_conditions: [] }]);
                        setNewCriterion({ text: '', type: 'Technical', mandatory: true });
                        setShowAddCriteria(false);
                      }}
                      className="px-4 py-1.5 text-sm font-bold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
                    >Add Criterion</button>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowAddCriteria(true)}
              className="mt-4 flex items-center gap-2 text-sm font-semibold text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 px-4 py-2 rounded-lg transition-colors"
            >
              <PlusCircle size={16} /> Add Custom Criterion
            </button>
          )}
        </div>
      </div>

      {/* Criterion Modal */}
      {selectedCriterion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm" onClick={() => setSelectedCriterion(null)}>
          <div 
            className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200"
            onClick={e => e.stopPropagation()}
          >
            <div className={clsx("p-6 border-b border-slate-100 flex items-center justify-between", typeColors[selectedCriterion.type]?.replace('border-', 'bg-').replace('-500', '-50') || "bg-slate-50")}>
              <div>
                <span className={clsx("text-xs font-bold px-2 py-1 rounded-md bg-white mb-2 inline-block", typeColors[selectedCriterion.type] || "text-slate-600")}>
                  {selectedCriterion.type || "Requirement"}
                </span>
                <h2 className="text-xl font-extrabold text-slate-900">{selectedCriterion.id}</h2>
              </div>
              <button onClick={() => setSelectedCriterion(null)} className="p-2 text-slate-400 hover:bg-white rounded-full transition-colors">
                ✕
              </button>
            </div>
            <div className="p-8 overflow-y-auto space-y-5">
              <div>
                <h3 className="font-bold text-slate-700 mb-2">Full Requirement Text:</h3>
                <p className="text-slate-600 leading-relaxed whitespace-pre-wrap bg-slate-50 p-4 rounded-lg border border-slate-200">{selectedCriterion.text}</p>
              </div>
              
              {selectedCriterion.source_section && (
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <BookOpen size={16} className="text-indigo-500"/> <span className="font-semibold">Source:</span> Section {selectedCriterion.source_section} of tender document
                </div>
              )}

              {selectedCriterion.sub_conditions && selectedCriterion.sub_conditions.length > 0 && (
                <div>
                  <h4 className="font-bold text-slate-700 mb-3 flex items-center gap-2"><Hash size={16} className="text-indigo-500"/> Measurable Sub-Conditions</h4>
                  <div className="space-y-2">
                    {selectedCriterion.sub_conditions.map((sc, i) => (
                      <div key={i} className="flex items-center gap-3 p-3 bg-white border border-slate-200 rounded-lg">
                        <Tag size={14} className="text-slate-400 shrink-0"/>
                        <span className="text-sm font-semibold text-slate-700">{sc.parameter}</span>
                        <span className="text-xs font-mono bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded border border-indigo-100">{sc.operator} {sc.threshold} {sc.unit || ''}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedCriterion.mandatory && (
                <div className="inline-flex items-center gap-2 px-3 py-2 bg-emerald-50 text-emerald-700 rounded-lg font-bold border border-emerald-200">
                  <CheckCircle2 size={18} /> This is a mandatory requirement
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Add Bidder Section */}
      <div className="clean-card">
        <h3 className="text-lg font-bold text-slate-800 mb-2 flex items-center gap-2 relative z-10">
          <Users className="text-indigo-500" />
          Add Bidders
        </h3>
        <p className="text-sm text-slate-500 mb-6 relative z-10">Enter a bidder name. Add multiple documents by keeping the same name.</p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex items-center gap-2 relative z-10">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        <div className="bg-white/60 p-4 rounded-xl border border-slate-200 relative z-10 shadow-sm">
          <div className="mb-4">
            <label className="block text-sm font-semibold text-slate-700 mb-1">Bidder Name</label>
            <input 
              type="text" 
              placeholder="e.g. Bharat Constructions" 
              className="w-full p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              value={bidderName}
              onChange={(e) => setBidderName(e.target.value)}
            />
          </div>

          <div className="flex border-b border-slate-200 mb-4">
            <button
              className={clsx("px-4 py-2 font-semibold text-sm transition-colors flex items-center gap-2", activeTab === 'upload' ? "text-indigo-600 border-b-2 border-indigo-600" : "text-slate-500 hover:text-slate-700")}
              onClick={() => setActiveTab('upload')}
            >
              <Upload size={16} /> Upload File
            </button>
            <button
              className={clsx("px-4 py-2 font-semibold text-sm transition-colors flex items-center gap-2", activeTab === 'paste' ? "text-indigo-600 border-b-2 border-indigo-600" : "text-slate-500 hover:text-slate-700")}
              onClick={() => setActiveTab('paste')}
            >
              <FileText size={16} /> Paste Text
            </button>
          </div>

          {activeTab === 'upload' ? (
            <div className="mb-4">
              <div className="border border-dashed border-slate-300 rounded-xl p-6 text-center hover:bg-slate-50/50 transition-colors bg-white/50">
                <input 
                  type="file" 
                  id="bidder-file" 
                  className="hidden" 
                  accept=".txt,.pdf,.png,.jpg,.jpeg,.zip"
                  multiple
                  onChange={(e) => setFiles(Array.from(e.target.files))}
                />
                <label htmlFor="bidder-file" className="cursor-pointer flex flex-col items-center">
                  <div className="w-10 h-10 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mb-2">
                    <Upload size={20} />
                  </div>
                  <span className="text-slate-700 font-bold text-sm">Click to upload bidder documents</span>
                  <span className="text-slate-500 text-xs mt-1">PDF, TXT, Images, or ZIP bundle • Select multiple files</span>
                </label>
                {files.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2 justify-center">
                    {files.map((f, i) => (
                      <span key={i} className="inline-flex items-center gap-1 px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-full text-xs font-bold border border-indigo-100">
                        <FileText size={12} /> {f.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="mb-4">
              <textarea
                className="w-full h-32 p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-y text-sm"
                placeholder="Paste the bidder's submission text here..."
                value={text}
                onChange={(e) => setText(e.target.value)}
              ></textarea>
            </div>
          )}

          <button 
            onClick={handleAddBidder}
            className="w-full py-2.5 px-4 bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-lg font-semibold transition-colors flex justify-center items-center gap-2 shadow-sm"
          >
            <Plus size={16} /> Add Bidder
          </button>
        </div>

        {/* Bidder List */}
        {bidders.length > 0 && (
          <div className="mt-8">
            <h4 className="font-semibold text-slate-800 mb-4">{bidders.length} Bidders Added</h4>
            <div className="space-y-2 mb-6">
              {bidders.map((bidder, i) => (
            <div key={i} className="flex items-center justify-between p-4 bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md transition-shadow relative z-10">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center font-bold">
                  {bidder.name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <h4 className="font-bold text-slate-800">{bidder.name}</h4>
                  <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                    <FileText size={12}/> {bidder.contents.length} {bidder.contents.length === 1 ? 'document' : 'documents'} attached
                  </p>
                </div>
              </div>
              <button 
                onClick={() => handleRemoveBidder(i)}
                className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
              >
                <Trash2 size={18} />
              </button>
            </div>
          ))}
            </div>

            <button 
              onClick={handleEvaluate}
              disabled={evaluating}
              className="w-full py-4 px-4 btn-primary-wow disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2 mt-6 relative z-10"
            >
              {evaluating ? (
                <div className="flex flex-col items-center gap-1">
                  <div className="flex items-center gap-2"><Loader2 className="animate-spin" size={20}/> {evalProgress || 'Evaluating...'}</div>
                  <div className="text-xs font-normal opacity-80 animate-pulse-fast">{PROGRESS_STEPS[progressIndex]}</div>
                </div>
              ) : (
                <>Evaluate All Bidders <ArrowRight size={20}/></>
              )}
            </button>

            {/* Live per-bidder completion tracker (SSE-driven) */}
            {evaluating && bidders.length > 0 && (
              <div className="mt-4 space-y-2 relative z-10">
                {bidders.map((bidder) => {
                  const done = completedBidders.has(bidder.name);
                  return (
                    <div key={bidder.name} className={clsx(
                      "flex items-center gap-3 p-3 rounded-lg border transition-all duration-500",
                      done 
                        ? "bg-emerald-50 border-emerald-200" 
                        : "bg-slate-50 border-slate-200 animate-pulse"
                    )}>
                      {done ? (
                        <CheckCircle2 size={18} className="text-emerald-500 flex-shrink-0" />
                      ) : (
                        <Loader2 size={18} className="text-slate-400 animate-spin flex-shrink-0" />
                      )}
                      <span className={clsx(
                        "text-sm font-semibold",
                        done ? "text-emerald-700" : "text-slate-500"
                      )}>
                        {bidder.name}
                      </span>
                      <span className="text-xs text-slate-400 ml-auto">
                        {done ? "Complete" : "Processing..."}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
