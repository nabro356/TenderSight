import { useState, useRef, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { Download, MessageSquare, AlertCircle, ChevronDown, ChevronUp, FileText, FileDown, Scale, Sparkles, X, Search, Check, AlertTriangle, Save, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import { chatAboutReport, downloadReportPdf, updateEvaluation } from '../api';

export default function ResultsDashboard({ tenderId, criteria, evaluations, setEvaluations }) {
  const [expandedBidder, setExpandedBidder] = useState(null);
  const [viewingSourceFor, setViewingSourceFor] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [savingOverride, setSavingOverride] = useState(false);
  const chatEndRef = useRef(null);

  const bidders = Object.keys(evaluations);
  const eligible = bidders.filter(b => evaluations[b].overall_status === 'ELIGIBLE').length;
  const notEligible = bidders.filter(b => evaluations[b].overall_status === 'NOT_ELIGIBLE').length;
  const review = bidders.filter(b => evaluations[b].overall_status === 'MANUAL_REVIEW').length;

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  // Chart 1: Confidence by Criterion Data
  const confidenceData = criteria.map(c => {
    const dataPoint = { name: c.id };
    bidders.forEach(b => {
      const verdict = evaluations[b].verdicts?.find(v => v.criterion_id === c.id);
      dataPoint[b] = verdict ? parseFloat(verdict.confidence) : 0;
    });
    return dataPoint;
  });

  // Chart 2: Verdict Distribution Data
  const distributionData = bidders.map(b => {
    const ev = evaluations[b];
    const total = Math.max((ev.eligible_count || 0) + (ev.not_eligible_count || 0) + (ev.manual_review_count || 0), 1);
    return {
      name: b.length > 15 ? b.substring(0, 15) + '...' : b,
      Eligible: (ev.eligible_count || 0) / total,
      Review: (ev.manual_review_count || 0) / total,
      NotEligible: (ev.not_eligible_count || 0) / total,
    };
  });

  const getStatusBadge = (status) => {
    if (status === 'ELIGIBLE') return <span className="badge-sm badge-eligible">ELIGIBLE</span>;
    if (status === 'NOT_ELIGIBLE') return <span className="badge-sm badge-not-eligible">NOT ELIGIBLE</span>;
    return <span className="badge-sm badge-review">REVIEW</span>;
  };

  const getStatusIcon = (status) => {
    if (status === 'ELIGIBLE') return '✅';
    if (status === 'NOT_ELIGIBLE') return '❌';
    return '⚠️';
  };

  const getConfidenceColor = (conf) => {
    if (conf >= 0.85) return 'text-green-600';
    if (conf >= 0.65) return 'text-amber-600';
    return 'text-red-600';
  };

  const downloadJSON = () => {
    const data = { criteria, evaluations, timestamp: new Date().toISOString() };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'tendersight_report.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadPDF = async () => {
    try {
      const pdfBlob = await downloadReportPdf(tenderId);
      const url = URL.createObjectURL(pdfBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `TenderSight_Report_${tenderId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF generation failed", err);
      alert("Failed to download PDF. Please ensure the backend is running.");
    }
  };

  const handleChat = async (question) => {
    if (!question.trim() || chatLoading) return;
    
    const newHistory = [...chatHistory, { role: 'user', content: question }];
    setChatHistory(newHistory);
    setChatInput('');
    setChatLoading(true);

    try {
      const response = await chatAboutReport(tenderId, question);
      setChatHistory([...newHistory, { role: 'assistant', content: response.answer }]);
    } catch (err) {
      setChatHistory([...newHistory, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setChatLoading(false);
    }
  };

  const chatSuggestions = [
    bidders.find(b => evaluations[b].overall_status === 'MANUAL_REVIEW') ? `Why was ${bidders.find(b => evaluations[b].overall_status === 'MANUAL_REVIEW')} flagged for review?` : null,
    bidders.find(b => evaluations[b].overall_status === 'NOT_ELIGIBLE') ? `Why was ${bidders.find(b => evaluations[b].overall_status === 'NOT_ELIGIBLE')} not eligible?` : null,
    bidders.length > 1 ? "Compare all bidders and rank them" : null
  ].filter(Boolean);

  const handleOverrideVerdict = (bidderName, criterionId, newStatus) => {
    const newEvals = { ...evaluations };
    const bidderEval = { ...newEvals[bidderName] };
    const verdicts = [...bidderEval.verdicts];
    
    const vIndex = verdicts.findIndex(v => v.criterion_id === criterionId);
    if (vIndex === -1) return;
    
    verdicts[vIndex] = { ...verdicts[vIndex], status: newStatus };
    bidderEval.verdicts = verdicts;
    
    // Recalculate stats
    bidderEval.eligible_count = verdicts.filter(v => v.status === 'ELIGIBLE').length;
    bidderEval.not_eligible_count = verdicts.filter(v => v.status === 'NOT_ELIGIBLE').length;
    bidderEval.manual_review_count = verdicts.filter(v => v.status === 'MANUAL_REVIEW').length;
    
    if (bidderEval.not_eligible_count > 0) bidderEval.overall_status = 'NOT_ELIGIBLE';
    else if (bidderEval.manual_review_count > 0) bidderEval.overall_status = 'MANUAL_REVIEW';
    else bidderEval.overall_status = 'ELIGIBLE';
    
    newEvals[bidderName] = bidderEval;
    setEvaluations(newEvals);
  };

  const handleSaveOverrides = async (bidderName) => {
    setSavingOverride(true);
    try {
      await updateEvaluation(tenderId, bidderName, evaluations[bidderName]);
      alert(`Changes saved successfully for ${bidderName}. Future PDF generation will use these updated results.`);
    } catch (err) {
      console.error("Failed to save overrides", err);
      alert("Failed to save overrides. Please check backend connection.");
    } finally {
      setSavingOverride(false);
    }
  };

  const renderHighlightedText = (fullText, highlightQuote) => {
    if (!highlightQuote || !fullText) return <p className="whitespace-pre-wrap font-mono text-sm text-slate-700">{fullText}</p>;
    
    // Simple string search and replace
    const index = fullText.toLowerCase().indexOf(highlightQuote.toLowerCase());
    if (index === -1) return <p className="whitespace-pre-wrap font-mono text-sm text-slate-700">{fullText}</p>;
    
    const before = fullText.substring(0, index);
    const match = fullText.substring(index, index + highlightQuote.length);
    const after = fullText.substring(index + highlightQuote.length);
    
    return (
      <p className="whitespace-pre-wrap font-mono text-sm text-slate-700 leading-relaxed">
        {before}
        <mark className="bg-yellow-300 text-yellow-900 rounded px-1 font-bold shadow-sm" id="highlighted-evidence">{match}</mark>
        {after}
      </p>
    );
  };

  // Scroll to highlight when source viewer opens
  useEffect(() => {
    if (viewingSourceFor) {
      setTimeout(() => {
        const el = document.getElementById('highlighted-evidence');
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    }
  }, [viewingSourceFor]);

  return (
    <div className="max-w-6xl mx-auto mt-8 space-y-8" id="pdf-dashboard-content">
      <div className="flex justify-between items-center bg-white/70 p-6 rounded-2xl border border-slate-200/60 shadow-sm backdrop-blur-md">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-indigo-50 rounded-xl text-indigo-600">
            <Scale size={32} />
          </div>
          <div>
            <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Evaluation Results</h2>
            <p className="text-sm text-slate-500 font-medium mt-1 flex items-center gap-1"><Sparkles size={14} className="text-violet-400"/> TenderSight Official Report</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={downloadJSON}
            className="flex items-center gap-2 px-5 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-xl hover:bg-slate-50 hover:border-slate-300 font-bold transition-all shadow-sm"
          >
            <Download size={18} /> JSON
          </button>
          <button 
            onClick={downloadPDF}
            className="flex items-center gap-2 px-6 py-2.5 btn-primary-wow"
          >
            <FileDown size={18} /> Generate PDF Report
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="clean-card !mb-0 text-center !p-4">
          <div className="text-3xl font-extrabold text-blue-800">{bidders.length}</div>
          <div className="text-xs uppercase font-bold text-slate-500 mt-1">Total</div>
        </div>
        <div className="clean-card !mb-0 text-center !p-4">
          <div className="text-3xl font-extrabold text-green-600">{eligible}</div>
          <div className="text-xs uppercase font-bold text-slate-500 mt-1">Eligible</div>
        </div>
        <div className="clean-card !mb-0 text-center !p-4">
          <div className="text-3xl font-extrabold text-red-600">{notEligible}</div>
          <div className="text-xs uppercase font-bold text-slate-500 mt-1">Not Eligible</div>
        </div>
        <div className="clean-card !mb-0 text-center !p-4">
          <div className="text-3xl font-extrabold text-amber-600">{review}</div>
          <div className="text-xs uppercase font-bold text-slate-500 mt-1">Review</div>
        </div>
      </div>

      {/* Charts */}
      {criteria.length > 0 && bidders.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="clean-card">
            <h3 className="text-sm font-bold text-slate-800 mb-6 text-center">Confidence by Criterion</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={confidenceData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="name" tick={{fontSize: 10}} interval={0} />
                  <YAxis domain={[0, 1]} tick={{fontSize: 10}} tickFormatter={(v) => `${(v*100).toFixed(0)}%`} />
                  <Tooltip formatter={(value) => `${(value * 100).toFixed(0)}%`} labelStyle={{color: '#1e293b', fontWeight: 'bold'}} />
                  <Legend wrapperStyle={{fontSize: '12px'}} />
                  {bidders.map((b, i) => (
                    <Bar key={b} dataKey={b} fill={COLORS[i % COLORS.length]} radius={[2, 2, 0, 0]} barSize={20} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="clean-card">
            <h3 className="text-sm font-bold text-slate-800 mb-6 text-center">Verdict Distribution</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart layout="vertical" data={distributionData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                  <XAxis type="number" domain={[0, 1]} tick={{fontSize: 10}} tickFormatter={(v) => `${(v*100).toFixed(0)}%`} />
                  <YAxis dataKey="name" type="category" tick={{fontSize: 10}} width={80} />
                  <Tooltip formatter={(value) => `${(value * 100).toFixed(0)}%`} labelStyle={{color: '#1e293b', fontWeight: 'bold'}} />
                  <Legend wrapperStyle={{fontSize: '12px'}} />
                  <Bar dataKey="Eligible" stackId="a" fill="#16a34a" barSize={20} />
                  <Bar dataKey="Review" stackId="a" fill="#f59e0b" />
                  <Bar dataKey="NotEligible" stackId="a" fill="#dc2626" radius={[0, 2, 2, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Detailed Results Modal Launcher */}
      <div>
        <h3 className="text-xl font-extrabold text-slate-900 mb-6 flex items-center gap-2"><FileText className="text-indigo-500" size={24}/> Detailed Bidder Evaluation</h3>
        <div className="space-y-4">
          {bidders.map((name) => {
            const ev = evaluations[name];
            
            return (
              <div key={name} className="clean-card !mb-0 !p-0 overflow-hidden hover:ring-2 hover:ring-indigo-500/20 transition-all cursor-pointer" onClick={() => setExpandedBidder(name)}>
                <div className="w-full px-8 py-5 flex items-center justify-between text-left hover:bg-slate-50/50 transition-colors">
                  <div className="flex items-center gap-4">
                    <span className="text-2xl drop-shadow-sm">{getStatusIcon(ev.overall_status)}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-extrabold text-slate-900 text-xl tracking-tight block">{name}</span>
                        {ev.anomaly_flag && (
                          <span className="text-xs font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded-md flex items-center gap-1 border border-red-100 animate-pulse">
                            <AlertTriangle size={12}/> ANOMALY
                          </span>
                        )}
                      </div>
                      <span className="text-sm font-semibold text-slate-500 mt-1 block">
                        ✅ {ev.eligible_count} / {(ev.eligible_count || 0) + (ev.not_eligible_count || 0) + (ev.manual_review_count || 0)} Criteria Satisfied
                      </span>
                    </div>
                    <span className="text-sm text-slate-500 capitalize font-medium px-3 py-1 bg-slate-100 rounded-full ml-2">— {ev.overall_status.replace('_', ' ').toLowerCase()}</span>
                  </div>
                  <button className="text-indigo-600 font-bold text-sm bg-indigo-50 px-4 py-2 rounded-lg hover:bg-indigo-100 transition-colors">
                    View Full Report
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bidder Detail Modal */}
      {expandedBidder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm" onClick={() => { setExpandedBidder(null); setViewingSourceFor(null); }}>
          <div 
            className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200"
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="px-8 py-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-4">
                <span className="text-3xl">{getStatusIcon(evaluations[expandedBidder].overall_status)}</span>
                <div>
                  <h2 className="text-2xl font-extrabold text-slate-900">{expandedBidder}</h2>
                  <p className="text-sm text-slate-500 font-medium">Evaluation Detail Report</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button 
                  onClick={() => handleSaveOverrides(expandedBidder)}
                  disabled={savingOverride}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold shadow-sm transition-colors disabled:opacity-50"
                >
                  {savingOverride ? <Loader2 size={16} className="animate-spin"/> : <Save size={16} />} 
                  Save Overrides
                </button>
                <button 
                  onClick={() => { setExpandedBidder(null); setViewingSourceFor(null); }}
                  className="p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 rounded-full transition-colors"
                >
                  <X size={24} />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-8 bg-slate-50/30">
              
              {evaluations[expandedBidder].anomaly_flag && (
                <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4 flex gap-3 shadow-sm">
                  <AlertTriangle className="text-red-600 shrink-0 mt-0.5" size={20} />
                  <div>
                    <h4 className="font-bold text-red-800 text-sm">Financial Anomaly Detected</h4>
                    <p className="text-sm text-red-700 mt-1">{evaluations[expandedBidder].anomaly_reason}</p>
                  </div>
                </div>
              )}

              {viewingSourceFor ? (
                <div className="space-y-4">
                  <button 
                    onClick={() => setViewingSourceFor(null)}
                    className="flex items-center gap-2 text-indigo-600 font-bold text-sm hover:underline"
                  >
                    ← Back to Evaluation Summary
                  </button>
                  <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-inner">
                    <div className="flex items-center gap-2 mb-4 pb-4 border-b border-slate-100">
                      <Search className="text-indigo-500" size={20}/>
                      <h3 className="font-bold text-slate-800">Source Document Viewer</h3>
                    </div>
                    <div className="bg-slate-50 p-6 rounded-lg border border-slate-200 max-h-[60vh] overflow-y-auto">
                      {renderHighlightedText(
                        evaluations[expandedBidder].bidder_text_snapshot, 
                        evaluations[expandedBidder].verdicts.find(v => v.criterion_id === viewingSourceFor)?.evidence_used[0]?.exact_quote
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  {evaluations[expandedBidder].verdicts.map((v, i) => (
                    <div key={i} className={clsx("bg-white border rounded-xl p-6 shadow-sm transition-shadow", v.status === 'MANUAL_REVIEW' ? 'border-amber-300 shadow-amber-100' : 'border-slate-200 hover:shadow-md')}>
                      <div className="flex justify-between items-start mb-4">
                        <div className="pr-8">
                          <div className="flex items-center gap-3 mb-1">
                            <h4 className="font-bold text-slate-900 text-lg">{v.criterion_text || v.criterion_id}</h4>
                            {v.status === 'MANUAL_REVIEW' && (
                              <span className="flex items-center gap-1 text-xs font-bold text-amber-700 bg-amber-100 px-2 py-1 rounded animate-pulse">
                                <AlertTriangle size={14} /> !NEED REVIEW
                              </span>
                            )}
                          </div>
                          <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-md uppercase tracking-wider border border-indigo-100">
                            {v.criterion_type || 'Requirement'}
                          </span>
                        </div>
                        {getStatusBadge(v.status)}
                      </div>
                      
                      <div className="bg-slate-50 rounded-lg p-5 border border-slate-100 mb-4">
                        <p className="text-sm text-slate-700 font-medium leading-relaxed mb-3">
                          <span className="font-bold text-slate-900">AI Reasoning:</span> {v.reasoning}
                        </p>
                        <p className="text-sm text-slate-600">
                          <span className="font-bold text-slate-800">Extracted Value:</span> <span className="font-mono bg-white px-2 py-1 rounded border border-slate-200">{v.evidence_used?.[0]?.value || 'N/A'}</span>
                        </p>
                      </div>

                      {v.status === 'MANUAL_REVIEW' && (
                        <div className="flex items-center gap-3 bg-amber-50 p-4 rounded-lg border border-amber-200 mb-4">
                          <p className="text-sm text-amber-800 font-semibold flex-1">
                            The AI flagged this for human review. Please accept or reject this criterion based on the evidence:
                          </p>
                          <div className="flex gap-2">
                            <button 
                              onClick={() => handleOverrideVerdict(expandedBidder, v.criterion_id, 'ELIGIBLE')}
                              className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded font-bold text-sm transition-colors flex items-center gap-1 shadow-sm"
                            >
                              <Check size={16}/> Accept
                            </button>
                            <button 
                              onClick={() => handleOverrideVerdict(expandedBidder, v.criterion_id, 'NOT_ELIGIBLE')}
                              className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded font-bold text-sm transition-colors flex items-center gap-1 shadow-sm"
                            >
                              <X size={16}/> Reject
                            </button>
                          </div>
                        </div>
                      )}

                      {v.evidence_used?.[0]?.exact_quote && v.evidence_used[0].exact_quote !== "null" && (
                        <button 
                          onClick={() => setViewingSourceFor(v.criterion_id)}
                          className="flex items-center gap-2 text-sm font-bold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 px-4 py-2 rounded-lg transition-colors w-full justify-center border border-indigo-100"
                        >
                          <Search size={16} /> View Highlighted Evidence in Source Document
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Chatbot */}
      <div className="clean-card flex flex-col h-[500px]">
        <h3 className="text-xl font-extrabold text-slate-900 mb-6 flex items-center gap-2 border-b border-slate-100 pb-4">
          <MessageSquare className="text-violet-500" size={24}/>
          Ask About This Report
        </h3>
        
        <div className="flex-1 overflow-y-auto mb-4 space-y-4 pr-2">
          {chatHistory.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-400">
              <MessageSquare size={48} className="mb-4 opacity-20" />
              <p>Ask questions about the evaluation results.</p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {chatSuggestions.map((s, i) => (
                  <button 
                    key={i} 
                    onClick={() => handleChat(s)}
                    className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 rounded-full text-xs font-medium transition-colors"
                  >
                    💡 {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            chatHistory.map((msg, i) => (
              <div key={i} className={clsx("flex", msg.role === 'user' ? "justify-end" : "justify-start")}>
                <div className={clsx("max-w-[80%] rounded-2xl px-4 py-3 text-sm", 
                  msg.role === 'user' ? "bg-blue-600 text-white rounded-tr-sm" : "bg-slate-100 text-slate-800 rounded-tl-sm"
                )}>
                  {/* Basic markdown rendering for the chat response */}
                  <div dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
                </div>
              </div>
            ))
          )}
          {chatLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-100 text-slate-500 rounded-2xl rounded-tl-sm px-4 py-3 text-sm flex items-center gap-2">
                <Loader2 className="animate-spin" size={16} /> Thinking...
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="pt-4 border-t border-slate-100">
          <form 
            onSubmit={(e) => { e.preventDefault(); handleChat(chatInput); }}
            className="flex gap-2"
          >
            <input 
              type="text" 
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask a question..." 
              className="flex-1 p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-sm"
              disabled={chatLoading}
            />
            <button 
              type="submit" 
              disabled={!chatInput.trim() || chatLoading}
              className="px-6 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50 flex items-center justify-center"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
