import { useState, useRef, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Cell, ReferenceLine, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ScatterChart, Scatter, ZAxis, CartesianGrid } from 'recharts';
import { Download, MessageSquare, AlertCircle, ChevronDown, ChevronUp, FileText, FileDown, Scale, Sparkles, X, Search, Check, AlertTriangle, Save, Loader2, CheckCircle, XCircle, Moon, Sun, Users, TrendingUp, ShieldAlert, HelpCircle, Lightbulb, Trophy, Edit3 } from 'lucide-react';
import clsx from 'clsx';
import { chatAboutReport, downloadReportPdf, updateEvaluation } from '../api';

/**
 * Sanitize HTML from LLM responses to prevent XSS attacks.
 * Strips dangerous tags/attributes while keeping safe formatting.
 */
const sanitizeHtml = (raw) => {
  if (!raw) return '';
  // Strip script/iframe/object/embed tags and their contents
  let clean = raw.replace(/<\s*(script|iframe|object|embed|form|input|textarea|button)[^>]*>[\s\S]*?<\/\s*\1\s*>/gi, '');
  // Strip any remaining self-closing dangerous tags
  clean = clean.replace(/<\s*(script|iframe|object|embed|form|input|textarea|button)[^>]*\/?>/gi, '');
  // Strip event handler attributes (onclick, onerror, onload, etc.)
  clean = clean.replace(/\s+on\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]*)/gi, '');
  // Strip javascript: URLs
  clean = clean.replace(/href\s*=\s*["']?\s*javascript\s*:/gi, 'href="');
  return clean;
};

export default function ResultsDashboard({ tenderId, criteria, evaluations, setEvaluations, cartelAlerts = [] }) {
  const [expandedBidder, setExpandedBidder] = useState(null);
  const [viewingSourceFor, setViewingSourceFor] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [savingOverride, setSavingOverride] = useState(false);
  const [recommendation, setRecommendation] = useState(null);
  const [overriddenBidder, setOverriddenBidder] = useState('');
  const [overrideJustification, setOverrideJustification] = useState('');
  const chatEndRef = useRef(null);

  const bidders = Object.keys(evaluations);
  const eligible = bidders.filter(b => evaluations[b].overall_status === 'ELIGIBLE').length;
  const notEligible = bidders.filter(b => evaluations[b].overall_status === 'NOT_ELIGIBLE').length;
  const review = bidders.filter(b => evaluations[b].overall_status === 'MANUAL_REVIEW').length;

  // Compute AI recommendation on mount
  useEffect(() => {
    const eligibleBidders = bidders.filter(b => evaluations[b].overall_status === 'ELIGIBLE');
    const cartelBidders = new Set((cartelAlerts || []).flatMap(a => [a.bidder1, a.bidder2]));
    const cleanBidders = eligibleBidders.filter(b => !cartelBidders.has(b) && !evaluations[b].anomaly_flag);
    
    let recommended = null;
    let reason = '';
    
    if (cleanBidders.length > 0) {
      // L1 rule: lowest financial bid wins
      const withBids = cleanBidders.filter(b => evaluations[b].financial_bid_numeric || evaluations[b].financial_bid);
      if (withBids.length > 0) {
        withBids.sort((a, b) => (evaluations[a].financial_bid_numeric || evaluations[a].financial_bid || Infinity) - (evaluations[b].financial_bid_numeric || evaluations[b].financial_bid || Infinity));
        recommended = withBids[0];
        const bidAmount = evaluations[recommended].financial_bid_numeric || evaluations[recommended].financial_bid;
        reason = `L1 Bidder — Lowest qualified financial bid (Rs. ${Number(bidAmount).toLocaleString('en-IN')}). Meets all eligibility criteria with no fraud flags.`;
      } else {
        // No financial bids — rank by eligible count + confidence
        cleanBidders.sort((a, b) => {
          const aScore = (evaluations[a].eligible_count || 0) * 100 + (evaluations[a].verdicts?.reduce((s, v) => s + v.confidence, 0) || 0);
          const bScore = (evaluations[b].eligible_count || 0) * 100 + (evaluations[b].verdicts?.reduce((s, v) => s + v.confidence, 0) || 0);
          return bScore - aScore;
        });
        recommended = cleanBidders[0];
        reason = `Highest eligibility score (${evaluations[recommended].eligible_count}/${criteria.length} criteria met). No financial bid data available for L1 ranking.`;
      }
    } else if (eligibleBidders.length > 0) {
      recommended = eligibleBidders[0];
      reason = `Only eligible bidder without disqualification. Note: fraud alerts may apply — manual review recommended.`;
    }
    
    if (recommended) {
      setRecommendation({ bidder: recommended, reason, isAI: true });
    }
  }, []);

  const COLORS = ['#6366f1', '#14b8a6', '#f43f5e', '#f59e0b', '#8b5cf6', '#06b6d4']; // Clean, vibrant SaaS palette for white backgrounds

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

  // Chart 3: Value Quadrant Data (Risk vs Reward)
  const quadrantData = bidders.map((b, i) => {
    const ev = evaluations[b];
    const avgConf = ev.verdicts?.length ? (ev.verdicts.reduce((acc, v) => acc + parseFloat(v.confidence), 0) / ev.verdicts.length) : 0;
    return {
      name: b.length > 15 ? b.substring(0, 15) + '...' : b,
      fullName: b,
      confidence: parseFloat((avgConf * 100).toFixed(1)),
      eligibility: ev.eligible_count || 0,
      fill: COLORS[i % COLORS.length]
    };
  });

  const getStatusBadge = (status) => {
    if (status === 'ELIGIBLE') return <span className="badge-sm badge-eligible">ELIGIBLE</span>;
    if (status === 'NOT_ELIGIBLE') return <span className="badge-sm badge-not-eligible">NOT ELIGIBLE</span>;
    return <span className="badge-sm badge-review">REVIEW</span>;
  };

  const getStatusIcon = (status) => {
    if (status === 'ELIGIBLE') return <CheckCircle className="text-green-500" size={28} />;
    if (status === 'NOT_ELIGIBLE') return <XCircle className="text-red-500" size={28} />;
    return <AlertTriangle className="text-amber-500" size={28} />;
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
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const downloadPDF = async () => {
    try {
      const pdfBlob = await downloadReportPdf(tenderId);
      const url = URL.createObjectURL(pdfBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `TenderSight_Report_${tenderId}.pdf`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
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
    
    // 1. Try exact match first (case-insensitive)
    const exactIdx = fullText.toLowerCase().indexOf(highlightQuote.toLowerCase());
    if (exactIdx !== -1) {
      const before = fullText.substring(0, exactIdx);
      const match = fullText.substring(exactIdx, exactIdx + highlightQuote.length);
      const after = fullText.substring(exactIdx + highlightQuote.length);
      return (
        <p className="whitespace-pre-wrap font-mono text-sm text-slate-700 leading-relaxed">
          {before}
          <mark className="bg-yellow-300 text-yellow-900 rounded px-1 font-bold shadow-sm" id="highlighted-evidence">{match}</mark>
          {after}
        </p>
      );
    }

    // 2. Fuzzy match: find the best-overlapping window using key words
    const quoteWords = highlightQuote.toLowerCase().replace(/[^\w\s]/g, '').split(/\s+/).filter(w => w.length > 3);
    if (quoteWords.length === 0) return <p className="whitespace-pre-wrap font-mono text-sm text-slate-700">{fullText}</p>;
    
    const textLower = fullText.toLowerCase();
    let bestStart = -1, bestEnd = -1, bestScore = 0;
    
    // Sliding window: check every ~200 char window
    const windowSize = Math.max(highlightQuote.length, 150);
    for (let i = 0; i <= textLower.length - 50; i += 20) {
      const windowEnd = Math.min(i + windowSize, textLower.length);
      const window = textLower.substring(i, windowEnd);
      const score = quoteWords.filter(w => window.includes(w)).length;
      if (score > bestScore && score >= Math.ceil(quoteWords.length * 0.4)) {
        bestScore = score;
        bestStart = i;
        bestEnd = windowEnd;
      }
    }
    
    if (bestStart !== -1) {
      // Expand to line boundaries for cleaner highlighting
      while (bestStart > 0 && fullText[bestStart - 1] !== '\n') bestStart--;
      while (bestEnd < fullText.length && fullText[bestEnd] !== '\n') bestEnd++;
      
      const before = fullText.substring(0, bestStart);
      const match = fullText.substring(bestStart, bestEnd);
      const after = fullText.substring(bestEnd);
      return (
        <p className="whitespace-pre-wrap font-mono text-sm text-slate-700 leading-relaxed">
          {before}
          <mark className="bg-yellow-200/80 text-yellow-900 rounded px-0.5 border-l-4 border-yellow-500" id="highlighted-evidence">{match}</mark>
          {after}
        </p>
      );
    }
    
    // 3. Last resort: highlight individual key terms inline
    const keyTerms = quoteWords.filter(w => w.length > 4).slice(0, 8);
    if (keyTerms.length > 0) {
      const regex = new RegExp(`(${keyTerms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
      const parts = fullText.split(regex);
      return (
        <p className="whitespace-pre-wrap font-mono text-sm text-slate-700 leading-relaxed">
          {parts.map((part, i) => {
            const isMatch = keyTerms.some(t => part.toLowerCase() === t.toLowerCase());
            return isMatch 
              ? <mark key={i} className="bg-amber-200/70 text-amber-900 rounded px-0.5 font-semibold" id={i <= 2 ? "highlighted-evidence" : undefined}>{part}</mark>
              : <span key={i}>{part}</span>;
          })}
        </p>
      );
    }
    
    return <p className="whitespace-pre-wrap font-mono text-sm text-slate-700">{fullText}</p>;
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
    <div className="max-w-6xl mx-auto mt-8 space-y-10 pb-12" id="pdf-dashboard-content">
      
      {/* Top Banner */}
      <div className="flex justify-between items-center p-8 rounded-[2rem] glass-panel relative overflow-hidden group">
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3 group-hover:bg-indigo-500/20 transition-colors duration-700"></div>
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-violet-500/10 rounded-full blur-2xl translate-y-1/3 -translate-x-1/4 group-hover:bg-violet-500/20 transition-colors duration-700"></div>
        
        <div className="flex items-center gap-5 relative z-10">
          <div className="p-4 bg-white/60 shadow-sm border border-white rounded-2xl text-indigo-600 backdrop-blur-md">
            <Scale size={36} className="drop-shadow-sm" />
          </div>
          <div>
            <h2 className="text-4xl font-extrabold text-slate-800 tracking-tight bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">Evaluation Results</h2>
            <p className="text-sm text-slate-500 font-medium mt-1.5 flex items-center gap-1.5"><Sparkles size={14} className="text-violet-500"/> TenderSight Official Report</p>
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
      <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
        <div className="clean-card !mb-0 !p-5 flex items-center gap-4 border-l-4 border-l-blue-500">
          <div className="p-3 bg-blue-50 rounded-xl text-blue-600"><Users size={22} /></div>
          <div>
            <div className="text-3xl font-extrabold text-slate-800 tracking-tight">{bidders.length}</div>
            <div className="text-xs font-semibold text-slate-400 tracking-wide uppercase">Total Bidders</div>
          </div>
        </div>
        <div className="clean-card !mb-0 !p-5 flex items-center gap-4 border-l-4 border-l-green-500">
          <div className="p-3 bg-green-50 rounded-xl text-green-600"><CheckCircle size={22} /></div>
          <div>
            <div className="text-3xl font-extrabold text-green-600 tracking-tight">{eligible}</div>
            <div className="text-xs font-semibold text-slate-400 tracking-wide uppercase">Eligible</div>
          </div>
        </div>
        <div className="clean-card !mb-0 !p-5 flex items-center gap-4 border-l-4 border-l-red-500">
          <div className="p-3 bg-red-50 rounded-xl text-red-600"><XCircle size={22} /></div>
          <div>
            <div className="text-3xl font-extrabold text-red-600 tracking-tight">{notEligible}</div>
            <div className="text-xs font-semibold text-slate-400 tracking-wide uppercase">Not Eligible</div>
          </div>
        </div>
        <div className="clean-card !mb-0 !p-5 flex items-center gap-4 border-l-4 border-l-amber-500">
          <div className="p-3 bg-amber-50 rounded-xl text-amber-600"><HelpCircle size={22} /></div>
          <div>
            <div className="text-3xl font-extrabold text-amber-500 tracking-tight">{review}</div>
            <div className="text-xs font-semibold text-slate-400 tracking-wide uppercase">Needs Review</div>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      {criteria.length > 0 && bidders.length > 0 && (
        <div className="space-y-6">
          <h3 className="text-lg font-semibold text-slate-700 flex items-center gap-2"><TrendingUp className="text-indigo-500" size={20}/> Analytics Overview</h3>
          {/* Top Row: Verdict Distribution (Progress Bars) */}
          <div className="clean-card">
            <h3 className="text-sm font-bold text-slate-800 mb-6 text-center">Verdict Distribution</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-6 px-4">
              {distributionData.map((data, idx) => (
                <div key={idx} className="relative">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-sm font-bold text-slate-700">{data.name}</span>
                    <span className="text-xs font-semibold text-slate-500">
                      {Math.round(data.Eligible * 100)}% Eligible
                    </span>
                  </div>
                  <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden flex shadow-inner">
                    <div className="h-full bg-gradient-to-r from-green-400 to-green-500 transition-all duration-1000 ease-out" style={{ width: `${data.Eligible * 100}%` }} title={`Eligible: ${(data.Eligible * 100).toFixed(1)}%`}></div>
                    <div className="h-full bg-gradient-to-r from-amber-400 to-amber-500 transition-all duration-1000 ease-out" style={{ width: `${data.Review * 100}%` }} title={`Review: ${(data.Review * 100).toFixed(1)}%`}></div>
                    <div className="h-full bg-gradient-to-r from-red-400 to-red-500 transition-all duration-1000 ease-out" style={{ width: `${data.NotEligible * 100}%` }} title={`Not Eligible: ${(data.NotEligible * 100).toFixed(1)}%`}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Bottom Row: Full Width Confidence Chart */}
          <div className="clean-card group">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-xl"></div>
            <h3 className="text-sm font-bold text-slate-800 mb-6 text-center relative z-10">Confidence by Criterion</h3>
            <div className="h-72 relative z-10">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={confidenceData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{fontSize: 10, fill: '#64748b'}} interval={0} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 1]} tick={{fontSize: 10, fill: '#64748b'}} tickFormatter={(v) => `${(v*100).toFixed(0)}%`} axisLine={false} tickLine={false} />
                  <Tooltip 
                    formatter={(value) => `${(value * 100).toFixed(0)}%`} 
                    contentStyle={{ backgroundColor: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(8px)', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                    itemStyle={{ fontWeight: 'bold' }} 
                  />
                  <Legend wrapperStyle={{fontSize: '12px'}} />
                  {bidders.map((b, i) => (
                    <Bar key={b} dataKey={b} fill={COLORS[i % COLORS.length]} radius={[4, 4, 0, 0]} barSize={24} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
      {/* ═══ FRAUD DETECTION BOX (Separate from main results) ═══ */}
      {cartelAlerts && cartelAlerts.length > 0 && (
        <div className="relative overflow-hidden border-2 border-red-500/50 bg-gradient-to-br from-red-50 via-white to-orange-50 rounded-[2rem] p-8 shadow-xl shadow-red-500/10">
          <div className="absolute top-0 right-0 w-64 h-64 bg-red-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4 animate-pulse"></div>
          
          <div className="relative z-10">
            <div className="flex items-center gap-4 mb-6">
              <div className="p-3 bg-red-600 rounded-2xl text-white shadow-lg shadow-red-600/30">
                <AlertTriangle size={28} />
              </div>
              <div>
                <h3 className="text-2xl font-extrabold text-red-800 tracking-tight">Suspected Fraud — Cartel Network</h3>
                <p className="text-sm text-red-600 font-medium mt-1">Graph-based entity overlap analysis flagged the following connections</p>
              </div>
            </div>
            <div className="space-y-3">
              {cartelAlerts.map((alert, idx) => (
                <div key={idx} className="bg-white p-4 rounded-xl border border-red-200 shadow-sm flex items-start gap-4">
                  <div className="bg-red-100 p-2 rounded-lg text-red-600 mt-0.5">
                    <AlertTriangle size={18} />
                  </div>
                  <div>
                    <p className="font-bold text-slate-900">
                      {alert.bidder1} ↔ {alert.bidder2}
                    </p>
                    <p className="text-red-700 font-semibold text-sm mt-1">
                      Share the same <span className="underline">{alert.link_type}</span>: <span className="font-mono bg-red-50 px-2 py-0.5 rounded border border-red-100">{alert.shared_entity}</span>
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      High risk of collusive bidding or shell company involvement. Manual investigation recommended.
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ═══ ANOMALY DETECTION BOX ═══ */}
      {bidders.some(b => evaluations[b].anomaly_flag) && (
        <div className="relative overflow-hidden border-2 border-amber-500/50 bg-gradient-to-br from-amber-50 via-white to-yellow-50 rounded-[2rem] p-8 shadow-xl shadow-amber-500/10">
          <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4"></div>
          
          <div className="relative z-10">
            <div className="flex items-center gap-4 mb-6">
              <div className="p-3 bg-amber-600 rounded-2xl text-white shadow-lg shadow-amber-600/30">
                <TrendingUp size={28} />
              </div>
              <div>
                <h3 className="text-2xl font-extrabold text-amber-800 tracking-tight">Financial Anomaly Detected</h3>
                <p className="text-sm text-amber-600 font-medium mt-1">Statistical analysis flagged abnormal bid amounts</p>
              </div>
            </div>
            <div className="space-y-3">
              {bidders.filter(b => evaluations[b].anomaly_flag).map((name, idx) => (
                <div key={idx} className="bg-white p-4 rounded-xl border border-amber-200 shadow-sm flex items-start gap-4">
                  <div className="bg-amber-100 p-2 rounded-lg text-amber-600 mt-0.5">
                    <ShieldAlert size={18} />
                  </div>
                  <div>
                    <p className="font-bold text-slate-900">{name}</p>
                    <p className="text-amber-700 font-semibold text-sm mt-1">
                      {evaluations[name].anomaly_reason}
                    </p>
                    {(evaluations[name].financial_bid_numeric || evaluations[name].financial_bid) && (
                      <p className="text-xs text-slate-500 mt-1">
                        Bid Amount: <span className="font-mono font-bold">Rs. {Number(evaluations[name].financial_bid_numeric || evaluations[name].financial_bid).toLocaleString('en-IN')}</span>
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Detailed Results */}
      <div>
        <h3 className="text-lg font-semibold text-slate-700 mb-5 flex items-center gap-2"><FileText className="text-indigo-500" size={20}/> Detailed Bidder Evaluation</h3>
        <div className="space-y-3">
          {bidders.map((name) => {
            const ev = evaluations[name];
            const totalCrit = (ev.eligible_count || 0) + (ev.not_eligible_count || 0) + (ev.manual_review_count || 0);
            const pctEligible = totalCrit > 0 ? Math.round(((ev.eligible_count || 0) / totalCrit) * 100) : 0;
            const statusColor = ev.overall_status === 'ELIGIBLE' ? 'border-l-green-500' : ev.overall_status === 'NOT_ELIGIBLE' ? 'border-l-red-500' : 'border-l-amber-400';
            
            return (
              <div key={name} className={clsx("clean-card !mb-0 !p-0 overflow-hidden border-l-4 hover:ring-2 hover:ring-indigo-500/20 transition-all cursor-pointer", statusColor)} onClick={() => setExpandedBidder(name)}>
                <div className="w-full px-6 py-5 flex items-center justify-between text-left hover:bg-slate-50/50 transition-colors">
                  <div className="flex items-center gap-4">
                    {getStatusIcon(ev.overall_status)}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-800 text-lg">{name}</span>
                        {ev.anomaly_flag && (
                          <span className="text-xs font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded-md flex items-center gap-1 border border-red-100 animate-pulse">
                            <ShieldAlert size={12}/> ANOMALY
                          </span>
                        )}
                        {(ev.financial_bid_numeric || ev.financial_bid) != null && (
                          <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md flex items-center gap-1 border border-emerald-200 shadow-sm ml-2">
                            Financial Bid: Rs. {Number(ev.financial_bid_numeric || ev.financial_bid).toLocaleString('en-IN')}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-sm text-slate-500">
                          {ev.eligible_count}/{totalCrit} criteria met
                        </span>
                        <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-indigo-400 to-indigo-500 rounded-full transition-all duration-700" style={{ width: `${pctEligible}%` }}></div>
                        </div>
                        <span className="text-xs font-semibold text-indigo-600">{pctEligible}%</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {getStatusBadge(ev.overall_status)}
                    <button className="text-indigo-600 font-semibold text-sm bg-indigo-50 px-4 py-2 rounded-lg hover:bg-indigo-100 transition-colors flex items-center gap-1">
                      <Search size={14}/> View Report
                    </button>
                  </div>
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
                  <h2 className="text-2xl font-bold text-slate-900">{expandedBidder}</h2>
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
                  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-lg">
                    <div className="flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-slate-100 to-slate-50 border-b border-slate-200">
                      <FileText className="text-indigo-500" size={18}/>
                      <h3 className="font-bold text-slate-800 text-sm">Bidder Submission — Source Document</h3>
                      <span className="ml-auto text-xs font-mono text-slate-400 bg-white px-2 py-0.5 rounded border border-slate-200">
                        {expandedBidder}
                      </span>
                    </div>
                    <div className="bg-slate-100 p-6">
                      <div className="bg-white mx-auto max-w-3xl shadow-md rounded-sm border border-slate-200 p-8 md:p-12 min-h-[40vh] max-h-[60vh] overflow-y-auto" style={{ fontFamily: "'Times New Roman', 'Georgia', serif" }}>
                        {(() => {
                          const v = evaluations[expandedBidder].verdicts.find(v => v.criterion_id === viewingSourceFor);
                          const quote = v?.evidence_used?.[0]?.exact_quote;
                          const value = v?.evidence_used?.[0]?.value;
                          const reasoning = v?.reasoning;
                          // Use the best available search term
                          const searchTerm = (quote && quote !== 'null' && quote !== 'Not found' && quote.length > 5) 
                            ? quote 
                            : (value && value !== 'null' && value !== 'Not found' && value.length > 3) 
                              ? value 
                              : reasoning;
                          return renderHighlightedText(
                            evaluations[expandedBidder].bidder_text_snapshot,
                            searchTerm
                          );
                        })()}
                      </div>
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
                      
                      <div className="bg-slate-50 rounded-lg p-5 border border-slate-100 mb-4 space-y-3">
                        <p className="text-sm text-slate-700 font-medium leading-relaxed">
                          <span className="font-bold text-slate-900">AI Reasoning:</span> {v.reasoning}
                        </p>
                        <div className="flex flex-wrap items-center gap-4">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-600">Extracted Value:</span>
                            <span className="font-mono text-sm bg-white px-2 py-1 rounded border border-slate-200 text-indigo-700 font-semibold">{v.evidence_used?.[0]?.value || 'N/A'}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-600">Confidence:</span>
                            <div className="w-20 h-2 bg-slate-200 rounded-full overflow-hidden">
                              <div 
                                className={clsx("h-full rounded-full transition-all", v.confidence >= 0.85 ? "bg-green-500" : v.confidence >= 0.65 ? "bg-amber-500" : "bg-red-500")}
                                style={{ width: `${(v.confidence * 100)}%` }}
                              />
                            </div>
                            <span className={clsx("text-xs font-bold", v.confidence >= 0.85 ? "text-green-600" : v.confidence >= 0.65 ? "text-amber-600" : "text-red-600")}>
                              {(v.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                        {v.evidence_used?.[0]?.exact_quote && v.evidence_used[0].exact_quote !== 'null' && v.evidence_used[0].exact_quote !== 'Not found' && (
                          <div className="mt-2 text-xs text-slate-500 bg-white p-3 rounded border border-slate-200 italic leading-relaxed">
                            <span className="font-semibold not-italic text-slate-600">📄 Source Quote: </span>
                            "{v.evidence_used[0].exact_quote.substring(0, 200)}{v.evidence_used[0].exact_quote.length > 200 ? '...' : ''}"
                          </div>
                        )}
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

      {/* ═══ FINAL RECOMMENDATION ═══ */}
      {recommendation && (
        <div className="relative overflow-hidden border-2 border-emerald-500/50 bg-gradient-to-br from-emerald-50 via-white to-teal-50 rounded-[2rem] p-8 shadow-xl shadow-emerald-500/10">
          <div className="absolute top-0 right-0 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4"></div>
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-teal-500/10 rounded-full blur-2xl translate-y-1/3 -translate-x-1/4"></div>
          
          <div className="relative z-10">
            <div className="flex items-center gap-4 mb-6">
              <div className="p-3 bg-emerald-600 rounded-2xl text-white shadow-lg shadow-emerald-600/30">
                <Trophy size={28} />
              </div>
              <div>
                <h3 className="text-2xl font-extrabold text-emerald-800 tracking-tight">Final Recommendation</h3>
                <p className="text-sm text-emerald-600 font-medium mt-1">
                  {recommendation.isAI && !overriddenBidder ? 'AI-generated based on L1 procurement rules' : 'Manually selected by reviewer'}
                </p>
              </div>
            </div>

            {/* Recommended Bidder */}
            <div className="bg-white p-6 rounded-xl border border-emerald-200 shadow-sm mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center font-extrabold text-2xl">
                    🏆
                  </div>
                  <div>
                    <div className="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-1">Recommended Bidder</div>
                    <h4 className="text-xl font-extrabold text-slate-900">{overriddenBidder || recommendation.bidder}</h4>
                  </div>
                </div>
                {getStatusBadge(evaluations[overriddenBidder || recommendation.bidder]?.overall_status)}
              </div>
              <p className="mt-4 text-sm text-slate-600 leading-relaxed bg-emerald-50/50 p-3 rounded-lg border border-emerald-100">
                <span className="font-semibold text-emerald-800">Reasoning: </span>
                {overriddenBidder && overrideJustification ? overrideJustification : recommendation.reason}
              </p>
            </div>

            {/* Override */}
            <details className="group">
              <summary className="cursor-pointer flex items-center gap-2 text-sm font-semibold text-emerald-700 hover:text-emerald-900 transition-colors">
                <Edit3 size={16} /> Override Recommendation (Reviewer)
              </summary>
              <div className="mt-4 p-5 bg-white rounded-xl border border-emerald-200 space-y-3">
                <div>
                  <label className="text-sm font-semibold text-slate-700 mb-1 block">Select Bidder</label>
                  <select
                    className="w-full p-2.5 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
                    value={overriddenBidder}
                    onChange={(e) => setOverriddenBidder(e.target.value)}
                  >
                    <option value="">AI Recommendation: {recommendation.bidder}</option>
                    {bidders.map(b => (
                      <option key={b} value={b}>{b} ({evaluations[b].overall_status})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-semibold text-slate-700 mb-1 block">Justification</label>
                  <textarea
                    className="w-full p-3 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 outline-none resize-y"
                    rows={2}
                    placeholder="Provide reasoning for overriding the AI recommendation..."
                    value={overrideJustification}
                    onChange={(e) => setOverrideJustification(e.target.value)}
                  />
                </div>
              </div>
            </details>
          </div>
        </div>
      )}

      {/* Chatbot */}
      <div className="clean-card flex flex-col h-[500px] !p-0 overflow-hidden">
        <div className="px-6 py-4 bg-gradient-to-r from-violet-500 to-indigo-600 flex items-center gap-3">
          <MessageSquare className="text-white/80" size={22}/>
          <h3 className="text-base font-semibold text-white">Ask About This Report</h3>
        </div>
        
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {chatHistory.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-400">
              <div className="p-4 bg-slate-50 rounded-full mb-4">
                <MessageSquare size={32} className="opacity-30" />
              </div>
              <p className="text-sm">Ask questions about the evaluation results.</p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {chatSuggestions.map((s, i) => (
                  <button 
                    key={i} 
                    onClick={() => handleChat(s)}
                    className="px-3 py-1.5 bg-slate-50 hover:bg-indigo-50 hover:text-indigo-600 hover:border-indigo-200 text-slate-600 border border-slate-200 rounded-full text-xs font-medium transition-all flex items-center gap-1.5"
                  >
                    <Lightbulb size={12} className="text-amber-400" /> {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            chatHistory.map((msg, i) => (
              <div key={i} className={clsx("flex", msg.role === 'user' ? "justify-end" : "justify-start")}>
                <div className={clsx("max-w-[80%] rounded-2xl px-4 py-3 text-sm", 
                  msg.role === 'user' ? "bg-indigo-600 text-white rounded-tr-sm" : "bg-white text-slate-800 rounded-tl-sm border border-slate-100 shadow-sm"
                )}>
                  <div dangerouslySetInnerHTML={{ __html: sanitizeHtml(msg.content.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')) }} />
                </div>
              </div>
            ))
          )}
          {chatLoading && (
            <div className="flex justify-start">
              <div className="bg-white text-slate-500 rounded-2xl rounded-tl-sm px-4 py-3 text-sm flex items-center gap-2 border border-slate-100 shadow-sm">
                <Loader2 className="animate-spin" size={16} /> Thinking...
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="p-4 border-t border-slate-100 bg-slate-50/50">
          <form 
            onSubmit={(e) => { e.preventDefault(); handleChat(chatInput); }}
            className="flex gap-2"
          >
            <input 
              type="text" 
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask a question about this evaluation..." 
              className="flex-1 p-3 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-300 outline-none text-sm transition-all"
              disabled={chatLoading}
            />
            <button 
              type="submit" 
              disabled={!chatInput.trim() || chatLoading}
              className="px-6 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
