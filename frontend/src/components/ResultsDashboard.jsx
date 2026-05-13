import { useEffect, useMemo, useRef, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Download,
  FileDown,
  FileSearch,
  FileText,
  HelpCircle,
  Lightbulb,
  Loader2,
  Mail,
  MessageSquare,
  Save,
  Search,
  Send,
  ShieldAlert,
  Smartphone,
  Users,
  X,
  XCircle,
} from 'lucide-react';
import clsx from 'clsx';
import { chatAboutReport, downloadReportPdf, updateEvaluation } from '../api';
import {
  buildClarificationMessage,
  buildPublishMessage,
  buildTenderAmbiguities,
  extractContactsFromText,
  toSentenceCase,
  verdictToMatrixStatus,
} from '../workspace-utils';

const toneClasses = {
  green: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  blue: 'bg-blue-50 border-blue-200 text-blue-800',
  amber: 'bg-amber-50 border-amber-200 text-amber-800',
  red: 'bg-red-50 border-red-200 text-red-800',
  slate: 'bg-slate-50 border-slate-200 text-slate-800',
};

function sanitizeHtml(raw) {
  if (!raw) return '';
  let clean = raw.replace(/<\s*(script|iframe|object|embed|form|input|textarea|button)[^>]*>[\s\S]*?<\/\s*\1\s*>/gi, '');
  clean = clean.replace(/<\s*(script|iframe|object|embed|form|input|textarea|button)[^>]*\/?>/gi, '');
  clean = clean.replace(/\s+on\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]*)/gi, '');
  clean = clean.replace(/href\s*=\s*["']?\s*javascript\s*:/gi, 'href="');
  return clean;
}

export default function ResultsDashboard({
  tenderId,
  tenderData,
  criteria,
  evaluations,
  setEvaluations,
  cartelAlerts = [],
  dispatchLog = [],
  setDispatchLog,
}) {
  const [expandedBidder, setExpandedBidder] = useState(null);
  const [viewingSourceFor, setViewingSourceFor] = useState(null);
  const [savingBidder, setSavingBidder] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [officerNotes, setOfficerNotes] = useState({});
  const [actionDraft, setActionDraft] = useState(null);
  const [actionChannel, setActionChannel] = useState('EMAIL');
  const [actionRecipient, setActionRecipient] = useState('');
  const [actionMessage, setActionMessage] = useState('');
  const chatEndRef = useRef(null);

  const bidders = useMemo(() => Object.keys(evaluations || {}), [evaluations]);
  const eligibleCount = bidders.filter((bidder) => evaluations[bidder]?.overall_status === 'ELIGIBLE').length;
  const reviewCount = bidders.filter((bidder) => evaluations[bidder]?.overall_status === 'MANUAL_REVIEW').length;
  const rejectedCount = bidders.filter((bidder) => evaluations[bidder]?.overall_status === 'NOT_ELIGIBLE').length;

  const chartData = useMemo(
    () =>
      bidders.map((bidder) => {
        const evaluation = evaluations[bidder];
        return {
          name: bidder.length > 18 ? `${bidder.slice(0, 18)}...` : bidder,
          eligible: evaluation?.eligible_count || 0,
          review: evaluation?.manual_review_count || 0,
          rejected: evaluation?.not_eligible_count || 0,
        };
      }),
    [bidders, evaluations]
  );

  const contactDirectory = useMemo(
    () =>
      Object.fromEntries(
        bidders.map((bidder) => [
          bidder,
          extractContactsFromText(evaluations[bidder]?.bidder_text_snapshot || ''),
        ])
      ),
    [bidders, evaluations]
  );

  const ambiguities = useMemo(
    () => buildTenderAmbiguities(criteria, evaluations),
    [criteria, evaluations]
  );

  const recommendedBidder = useMemo(() => {
    const eligibleBidders = bidders
      .filter((bidder) => evaluations[bidder]?.overall_status === 'ELIGIBLE')
      .map((bidder) => {
        const verdicts = evaluations[bidder]?.verdicts || [];
        const averageConfidence =
          verdicts.reduce((sum, verdict) => sum + Number(verdict.confidence || 0), 0) /
          Math.max(verdicts.length, 1);
        return {
          bidder,
          averageConfidence,
          financialBid: Number(evaluations[bidder]?.financial_bid || Number.MAX_SAFE_INTEGER),
        };
      })
      .sort((left, right) => {
        if (right.averageConfidence !== left.averageConfidence) {
          return right.averageConfidence - left.averageConfidence;
        }
        return left.financialBid - right.financialBid;
      });

    return eligibleBidders[0] || null;
  }, [bidders, evaluations]);

  const publicationReadyBidders = useMemo(
    () => bidders.filter((bidder) => evaluations[bidder]?.overall_status !== 'MANUAL_REVIEW'),
    [bidders, evaluations]
  );

  const clarificationTargets = useMemo(
    () => bidders.filter((bidder) => evaluations[bidder]?.overall_status === 'MANUAL_REVIEW'),
    [bidders, evaluations]
  );

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  useEffect(() => {
    if (!actionDraft) return;
    const contacts = actionDraft.bidderName
      ? contactDirectory[actionDraft.bidderName] || { emails: [], phones: [] }
      : { emails: [], phones: [] };
    const nextChannel = contacts.emails[0] ? 'EMAIL' : contacts.phones[0] ? 'SMS' : 'EMAIL';
    const nextRecipient = nextChannel === 'EMAIL' ? contacts.emails[0] || '' : contacts.phones[0] || '';

    setActionChannel(nextChannel);
    setActionRecipient(nextRecipient);

    if (actionDraft.bidderName) {
      const evaluation = evaluations[actionDraft.bidderName];
      setActionMessage(
        actionDraft.type === 'clarification'
          ? buildClarificationMessage(actionDraft.bidderName, evaluation)
          : buildPublishMessage(actionDraft.bidderName, evaluation)
      );
    }
  }, [actionDraft, contactDirectory, evaluations]);

  const chatSuggestions = [
    reviewCount ? `Why do ${reviewCount} bidder(s) still require manual review?` : null,
    recommendedBidder ? `Why is ${recommendedBidder.bidder} the leading recommendation?` : null,
    bidders.length > 1 ? 'Compare all bidders and rank their overall compliance' : null,
  ].filter(Boolean);

  const getOfficerNote = (bidderName, criterionId) =>
    officerNotes[`${bidderName}:${criterionId}`] ||
    evaluations[bidderName]?.operator_notes?.[criterionId]?.note ||
    '';

  const setOfficerNote = (bidderName, criterionId, note) => {
    setOfficerNotes((current) => ({
      ...current,
      [`${bidderName}:${criterionId}`]: note,
    }));
  };

  const buildOperatorNotes = (bidderName) => {
    const nextNotes = { ...(evaluations[bidderName]?.operator_notes || {}) };

    for (const verdict of evaluations[bidderName]?.verdicts || []) {
      const note = getOfficerNote(bidderName, verdict.criterion_id).trim();
      if (!note) continue;
      nextNotes[verdict.criterion_id] = {
        note,
        criterion_text: verdict.criterion_text || verdict.criterion_id,
        updated_at: new Date().toISOString(),
      };
    }

    return nextNotes;
  };

  const handleOverrideVerdict = (bidderName, criterionId, nextStatus) => {
    setEvaluations((current) => {
      const next = { ...current };
      const bidderEvaluation = { ...next[bidderName] };
      const verdicts = (bidderEvaluation.verdicts || []).map((verdict) =>
        verdict.criterion_id === criterionId ? { ...verdict, status: nextStatus } : verdict
      );
      const statuses = verdicts.map((verdict) => verdict.status);

      bidderEvaluation.verdicts = verdicts;
      bidderEvaluation.eligible_count = statuses.filter((status) => status === 'ELIGIBLE').length;
      bidderEvaluation.not_eligible_count = statuses.filter((status) => status === 'NOT_ELIGIBLE').length;
      bidderEvaluation.manual_review_count = statuses.filter((status) => status === 'MANUAL_REVIEW').length;
      bidderEvaluation.overall_status = bidderEvaluation.not_eligible_count
        ? 'NOT_ELIGIBLE'
        : bidderEvaluation.manual_review_count
          ? 'MANUAL_REVIEW'
          : 'ELIGIBLE';

      next[bidderName] = bidderEvaluation;
      return next;
    });
  };

  const handleSaveOverrides = async (bidderName) => {
    const updatedEvaluation = {
      ...evaluations[bidderName],
      operator_notes: buildOperatorNotes(bidderName),
      last_operator_update: new Date().toISOString(),
    };
    const nextEvaluations = {
      ...evaluations,
      [bidderName]: updatedEvaluation,
    };

    setSavingBidder(bidderName);
    setEvaluations(nextEvaluations);

    try {
      await updateEvaluation(tenderId, bidderName, updatedEvaluation);
      window.alert(`Saved overrides and officer notes for ${bidderName}.`);
    } catch (error) {
      console.error('Failed to save overrides', error);
      window.alert('Failed to save overrides. Please check the backend connection.');
    } finally {
      setSavingBidder('');
    }
  };

  const queueDispatchRecords = (type, bidderNames) => {
    const createdAt = new Date().toLocaleString('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });

    const records = bidderNames.map((bidderName) => {
      const contacts = contactDirectory[bidderName] || { emails: [], phones: [] };
      const channel = contacts.emails[0] ? 'EMAIL' : contacts.phones[0] ? 'SMS' : 'MANUAL';
      const recipient = channel === 'EMAIL' ? contacts.emails[0] : channel === 'SMS' ? contacts.phones[0] : 'No contact detected';
      const evaluation = evaluations[bidderName];
      const message =
        type === 'clarification'
          ? buildClarificationMessage(bidderName, evaluation)
          : buildPublishMessage(bidderName, evaluation);

      return {
        id: `${type}-${bidderName}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        bidderName,
        channel,
        recipient,
        type,
        outcome: evaluation?.overall_status || 'MANUAL_REVIEW',
        status: recipient === 'No contact detected' ? 'Missing contact' : 'Sent (prototype)',
        timestamp: createdAt,
        message,
      };
    });

    setDispatchLog((current) => [...records, ...current]);
    return records;
  };

  const handleBulkPublish = () => {
    if (!publicationReadyBidders.length) {
      window.alert('No bidders are ready for final publication yet.');
      return;
    }

    const records = queueDispatchRecords('publish', publicationReadyBidders);
    const sentCount = records.filter((record) => record.status === 'Sent (prototype)').length;
    window.alert(`Queued ${sentCount} result notification(s) into the publish log.`);
  };

  const handleBulkClarifications = () => {
    if (!clarificationTargets.length) {
      window.alert('No manual-review bidders currently require clarification.');
      return;
    }

    const records = queueDispatchRecords('clarification', clarificationTargets);
    const sentCount = records.filter((record) => record.status === 'Sent (prototype)').length;
    window.alert(`Queued ${sentCount} clarification request(s) into the dispatch log.`);
  };

  const handleDispatchAction = () => {
    if (!actionDraft) return;
    if (!actionRecipient.trim()) {
      window.alert('Add a recipient email or phone number before dispatching.');
      return;
    }

    const createdAt = new Date().toLocaleString('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });

    setDispatchLog((current) => [
      {
        id: `${actionDraft.type}-${actionDraft.bidderName}-${Date.now()}`,
        bidderName: actionDraft.bidderName,
        channel: actionChannel,
        recipient: actionRecipient,
        type: actionDraft.type,
        outcome: evaluations[actionDraft.bidderName]?.overall_status || 'MANUAL_REVIEW',
        status: 'Sent (prototype)',
        timestamp: createdAt,
        message: actionMessage,
      },
      ...current,
    ]);

    setActionDraft(null);
    setActionMessage('');
    setActionRecipient('');
  };

  const handleChat = async (question) => {
    if (!question.trim() || chatLoading) return;

    const history = [...chatHistory, { role: 'user', content: question }];
    setChatHistory(history);
    setChatInput('');
    setChatLoading(true);

    try {
      const response = await chatAboutReport(tenderId, question);
      setChatHistory([...history, { role: 'assistant', content: response.answer }]);
    } catch (error) {
      setChatHistory([...history, { role: 'assistant', content: `Error: ${error.message}` }]);
    } finally {
      setChatLoading(false);
    }
  };

  const downloadJson = () => {
    const data = {
      tenderId,
      tenderData,
      criteria,
      evaluations,
      dispatchLog,
      exported_at: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `TenderSight_Workspace_${tenderId}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const downloadPdf = async () => {
    try {
      const pdfBlob = await downloadReportPdf(tenderId);
      const url = URL.createObjectURL(pdfBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `TenderSight_Report_${tenderId}.pdf`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      console.error('PDF generation failed', error);
      window.alert('Failed to download PDF. Please ensure the backend is running.');
    }
  };

  const renderHighlightedText = (fullText, highlightQuote) => {
    if (!highlightQuote || !fullText) {
      return <p className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-slate-700">{fullText}</p>;
    }

    const index = fullText.toLowerCase().indexOf(highlightQuote.toLowerCase());
    if (index === -1) {
      return <p className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-slate-700">{fullText}</p>;
    }

    const before = fullText.slice(0, index);
    const match = fullText.slice(index, index + highlightQuote.length);
    const after = fullText.slice(index + highlightQuote.length);

    return (
      <p className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-slate-700">
        {before}
        <mark className="rounded bg-yellow-200 px-1.5 py-0.5 font-bold text-yellow-900">{match}</mark>
        {after}
      </p>
    );
  };

  return (
    <div className="max-w-7xl mx-auto mt-6 space-y-8 pb-12">
      <section className="glass-panel rounded-[2rem] p-8 relative overflow-hidden">
        <div className="absolute inset-y-0 right-0 w-96 bg-gradient-to-l from-indigo-500/10 to-transparent" />
        <div className="relative z-10 flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-indigo-600">Publish and Results</p>
            <h2 className="mt-3 text-4xl font-black tracking-tight text-slate-900">Officer decision and communication workspace</h2>
            <p className="mt-3 text-slate-600 leading-relaxed">
              This is the final operator surface: validate the compliance matrix, resolve ambiguities,
              add officer notes, then publish results or request clarification using contacts extracted
              from bidder submissions.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button onClick={handleBulkPublish} className="btn-primary-wow px-5 py-3 flex items-center gap-2">
                <Send size={18} /> Publish Ready Outcomes
              </button>
              <button
                onClick={handleBulkClarifications}
                className="px-5 py-3 rounded-xl border border-amber-200 bg-amber-50 font-semibold text-amber-800 hover:bg-amber-100 transition-colors flex items-center gap-2"
              >
                <Mail size={18} /> Request Clarifications
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={downloadJson}
              className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-3 font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <Download size={18} /> Export JSON
            </button>
            <button onClick={downloadPdf} className="flex items-center gap-2 px-5 py-3 btn-primary-wow">
              <FileDown size={18} /> Generate PDF Report
            </button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-2 xl:grid-cols-4 gap-5">
        <MetricCard icon={Users} label="Bidders Evaluated" value={bidders.length} tone="blue" />
        <MetricCard icon={CheckCircle2} label="Publish Ready" value={eligibleCount} tone="green" />
        <MetricCard icon={HelpCircle} label="Manual Review" value={reviewCount} tone="amber" />
        <MetricCard icon={Send} label="Dispatch Log" value={dispatchLog.length} tone="slate" />
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-[1.25fr,1fr] gap-6">
        <div className="clean-card !mb-0">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">Recommendation Banner</p>
              <h3 className="mt-2 text-2xl font-black text-slate-900">
                {recommendedBidder ? `${recommendedBidder.bidder} is the current lead` : 'No bidder is fully clear yet'}
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-slate-600">
                {recommendedBidder
                  ? `TenderSight would currently surface ${recommendedBidder.bidder} as the leading eligible bidder based on full-criteria eligibility and stronger confidence across the extracted evidence trail.`
                  : 'At least one bidder still needs manual review or all bidders are currently failing mandatory requirements.'}
              </p>
            </div>
            <div className="rounded-2xl bg-slate-50 border border-slate-100 px-4 py-3 text-right">
              <div className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Bundle</div>
              <div className="mt-2 font-bold text-slate-900">{tenderData?.bundle_documents?.length || 0} source file(s)</div>
              <div className="mt-1 text-sm text-slate-500">{criteria.length} extracted criteria</div>
            </div>
          </div>

          <div className="mt-6 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={{ fill: 'rgba(99, 102, 241, 0.06)' }}
                  contentStyle={{
                    backgroundColor: 'rgba(255,255,255,0.96)',
                    borderRadius: '14px',
                    border: '1px solid #e2e8f0',
                    boxShadow: '0 10px 25px rgba(15, 23, 42, 0.08)',
                  }}
                />
                <Bar dataKey="eligible" stackId="status" fill="#10b981" radius={[8, 8, 0, 0]} />
                <Bar dataKey="review" stackId="status" fill="#f59e0b" radius={[8, 8, 0, 0]} />
                <Bar dataKey="rejected" stackId="status" fill="#ef4444" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="space-y-6">
          <div className="clean-card !mb-0">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">Dispatch Center</p>
            <div className="mt-4 space-y-3 text-sm text-slate-600">
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                <div className="font-bold text-slate-900">Eligible bidders</div>
                <div className="mt-2">{eligibleCount} ready for publish notification.</div>
              </div>
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                <div className="font-bold text-slate-900">Rejected bidders</div>
                <div className="mt-2">{rejectedCount} can receive a fail outcome or a clarification workflow.</div>
              </div>
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                <div className="font-bold text-slate-900">Manual-review bidders</div>
                <div className="mt-2">{reviewCount} should be routed to clarification before final publication.</div>
              </div>
            </div>
          </div>

          <div className="clean-card !mb-0">
            <div className="flex items-center gap-3">
              <FileText className="text-indigo-500" size={18} />
              <h3 className="text-lg font-bold text-slate-900">Communication log</h3>
            </div>

            {dispatchLog.length === 0 ? (
              <div className="mt-5 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
                No notifications queued yet. Use the publish or clarification actions to simulate bidder communications.
              </div>
            ) : (
              <div className="mt-5 space-y-3 max-h-[340px] overflow-y-auto pr-1">
                {dispatchLog.slice(0, 6).map((record) => (
                  <div key={record.id} className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="font-semibold text-slate-900">{record.bidderName}</div>
                        <div className="mt-1 text-xs uppercase tracking-[0.22em] text-slate-400">
                          {record.type === 'clarification' ? 'Clarification request' : 'Result published'}
                        </div>
                      </div>
                      <StatusPill
                        tone={record.status === 'Sent (prototype)' ? 'green' : 'amber'}
                        label={record.status}
                      />
                    </div>
                    <div className="mt-3 text-sm text-slate-600">
                      {record.channel} to {record.recipient}
                    </div>
                    <div className="mt-1 text-xs text-slate-400">{record.timestamp}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="clean-card !mb-0 overflow-hidden">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">Compliance Matrix</p>
            <h3 className="mt-2 text-2xl font-black text-slate-900">Source-linked row status across all bidders</h3>
          </div>
          <div className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-600">
            Verified / Partial / Missing / Ambiguous
          </div>
        </div>

        <div className="mt-6 overflow-x-auto">
          <table className="w-full min-w-[860px] text-left">
            <thead>
              <tr className="border-b border-slate-100 text-xs uppercase tracking-[0.25em] text-slate-400">
                <th className="px-4 py-3">Criterion</th>
                {bidders.map((bidder) => (
                  <th key={bidder} className="px-4 py-3">
                    {bidder}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {criteria.map((criterion) => (
                <tr key={criterion.id} className="border-b border-slate-100 align-top last:border-b-0">
                  <td className="px-4 py-4">
                    <div className="font-semibold text-slate-900">{criterion.id}</div>
                    <div className="mt-1 max-w-sm text-sm leading-relaxed text-slate-600">{criterion.text}</div>
                  </td>
                  {bidders.map((bidder) => {
                    const verdict = evaluations[bidder]?.verdicts?.find(
                      (item) => item.criterion_id === criterion.id
                    );
                    const matrixStatus = verdictToMatrixStatus(verdict);
                    return (
                      <td key={`${criterion.id}-${bidder}`} className="px-4 py-4">
                        <div className={clsx('inline-flex rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-[0.18em]', toneClasses[matrixStatus.tone])}>
                          {matrixStatus.label}
                        </div>
                        <div className="mt-2 text-sm font-semibold text-slate-700">
                          {toSentenceCase(verdict?.status || 'UNKNOWN')}
                        </div>
                        <div className="mt-1 text-xs text-slate-500">
                          {verdict?.evidence_used?.[0]?.source_document || 'No linked source'}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-[1.3fr,1fr] gap-6">
        <div className="clean-card !mb-0">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">Gaps and Clarifications</p>
          <h3 className="mt-2 text-2xl font-black text-slate-900">Officer notes for failed or ambiguous criteria</h3>

          <div className="mt-6 space-y-5">
            {bidders.map((bidder) => {
              const gaps = (evaluations[bidder]?.verdicts || []).filter((verdict) => verdict.status !== 'ELIGIBLE');
              if (!gaps.length) return null;

              return (
                <div key={bidder} className="rounded-[1.5rem] border border-slate-200 bg-white p-5">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <div className="text-lg font-bold text-slate-900">{bidder}</div>
                      <div className="mt-1 text-sm text-slate-500">
                        {gaps.length} criterion gap(s) need officer attention before publication.
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setExpandedBidder(bidder)}
                        className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
                      >
                        View report
                      </button>
                      <button
                        onClick={() => setActionDraft({ type: 'clarification', bidderName: bidder })}
                        className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-800 hover:bg-amber-100 transition-colors"
                      >
                        Request clarification
                      </button>
                    </div>
                  </div>

                  <div className="mt-5 space-y-4">
                    {gaps.slice(0, 4).map((verdict) => (
                      <div key={`${bidder}-${verdict.criterion_id}`} className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <div className="font-semibold text-slate-900">{verdict.criterion_id}</div>
                          <StatusPill
                            tone={verdict.status === 'MANUAL_REVIEW' ? 'amber' : 'red'}
                            label={toSentenceCase(verdict.status)}
                          />
                        </div>
                        <p className="mt-2 text-sm leading-relaxed text-slate-600">
                          {verdict.reasoning || 'No reasoning generated.'}
                        </p>
                        <textarea
                          className="mt-4 min-h-[88px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition-all focus:border-indigo-300 focus:ring-2 focus:ring-indigo-500/20"
                          placeholder="Officer note: what is missing, what should the bidder clarify, or why the override is justified..."
                          value={getOfficerNote(bidder, verdict.criterion_id)}
                          onChange={(event) => setOfficerNote(bidder, verdict.criterion_id, event.target.value)}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="clean-card !mb-0">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">Tender Ambiguities</p>
          <h3 className="mt-2 text-2xl font-black text-slate-900">Cross-bidder criteria that still look fuzzy</h3>

          {ambiguities.length === 0 ? (
            <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-sm text-emerald-800">
              No major cross-bidder ambiguities remain. The bundle appears consistent enough for publication.
            </div>
          ) : (
            <div className="mt-6 space-y-4">
              {ambiguities.map((ambiguity) => (
                <div key={ambiguity.criterionId} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="font-semibold text-slate-900">{ambiguity.criterionId}</div>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">{ambiguity.criterionText}</p>
                  <div className="mt-4 space-y-2">
                    {ambiguity.flagged.map((flag) => (
                      <div key={`${ambiguity.criterionId}-${flag.bidder}`} className="rounded-xl border border-slate-100 bg-white px-3 py-3">
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-semibold text-slate-800">{flag.bidder}</span>
                          <StatusPill
                            tone={flag.status === 'MANUAL_REVIEW' ? 'amber' : 'red'}
                            label={toSentenceCase(flag.status)}
                          />
                        </div>
                        <div className="mt-2 text-sm text-slate-600">{flag.reasoning}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {cartelAlerts.length > 0 && (
        <section className="rounded-[2rem] border-2 border-red-200 bg-gradient-to-br from-red-50 via-white to-orange-50 p-8 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="rounded-2xl bg-red-600 p-3 text-white shadow-lg shadow-red-600/20">
              <ShieldAlert size={26} />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-red-600">Fraud and cartel review</p>
              <h3 className="mt-2 text-2xl font-black text-red-900">Potential entity overlap detected</h3>
              <div className="mt-5 space-y-3">
                {cartelAlerts.map((alert, index) => (
                  <div key={`${alert.bidder1}-${alert.bidder2}-${index}`} className="rounded-2xl border border-red-200 bg-white p-4">
                    <div className="font-semibold text-slate-900">
                      {alert.bidder1} and {alert.bidder2}
                    </div>
                    <div className="mt-1 text-sm text-red-700">
                      Shared {alert.link_type}: {alert.shared_entity}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="clean-card !mb-0">
        <div className="flex items-center gap-3">
          <FileSearch className="text-indigo-500" size={18} />
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">Bidder reports</p>
            <h3 className="mt-2 text-2xl font-black text-slate-900">Detailed evaluation per bidder</h3>
          </div>
        </div>

        <div className="mt-6 space-y-4">
          {bidders.map((bidder) => {
            const evaluation = evaluations[bidder];
            const contacts = contactDirectory[bidder] || { emails: [], phones: [] };
            const totalCriteria =
              (evaluation?.eligible_count || 0) +
              (evaluation?.manual_review_count || 0) +
              (evaluation?.not_eligible_count || 0);
            const passRate = totalCriteria ? Math.round(((evaluation?.eligible_count || 0) / totalCriteria) * 100) : 0;

            return (
              <div
                key={bidder}
                className="rounded-[1.5rem] border border-slate-200 bg-white px-6 py-5 shadow-sm transition-all hover:shadow-md"
              >
                <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
                  <div className="flex items-start gap-4">
                    <div className="mt-1">
                      {evaluation.overall_status === 'ELIGIBLE' && <CheckCircle2 className="text-emerald-500" size={28} />}
                      {evaluation.overall_status === 'NOT_ELIGIBLE' && <XCircle className="text-red-500" size={28} />}
                      {evaluation.overall_status === 'MANUAL_REVIEW' && <AlertTriangle className="text-amber-500" size={28} />}
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <h4 className="text-xl font-bold text-slate-900">{bidder}</h4>
                        <StatusPill
                          tone={
                            evaluation.overall_status === 'ELIGIBLE'
                              ? 'green'
                              : evaluation.overall_status === 'MANUAL_REVIEW'
                                ? 'amber'
                                : 'red'
                          }
                          label={toSentenceCase(evaluation.overall_status)}
                        />
                        {evaluation.anomaly_flag && (
                          <span className="inline-flex items-center gap-1 rounded-full border border-red-200 bg-red-50 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-red-700">
                            <AlertTriangle size={12} /> Anomaly
                          </span>
                        )}
                      </div>
                      <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-slate-500">
                        <span>{evaluation.eligible_count || 0}/{totalCriteria} criteria passed</span>
                        <span>{contacts.emails.length} email(s) detected</span>
                        <span>{contacts.phones.length} phone number(s) detected</span>
                      </div>
                      <div className="mt-3 h-2.5 w-64 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500"
                          style={{ width: `${passRate}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => setExpandedBidder(bidder)}
                      className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
                    >
                      View report
                    </button>
                    <button
                      onClick={() =>
                        setActionDraft({
                          type: evaluation.overall_status === 'MANUAL_REVIEW' ? 'clarification' : 'publish',
                          bidderName: bidder,
                        })
                      }
                      className={clsx(
                        'rounded-xl px-4 py-2 text-sm font-semibold transition-colors',
                        evaluation.overall_status === 'MANUAL_REVIEW'
                          ? 'border border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100'
                          : 'btn-primary-wow'
                      )}
                    >
                      {evaluation.overall_status === 'MANUAL_REVIEW' ? 'Request clarification' : 'Publish result'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="clean-card flex flex-col h-[480px] !p-0 overflow-hidden">
        <div className="flex items-center gap-3 bg-gradient-to-r from-violet-500 to-indigo-600 px-6 py-4">
          <MessageSquare className="text-white/85" size={22} />
          <h3 className="text-base font-semibold text-white">Ask About This Report</h3>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {chatHistory.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-slate-400">
              <div className="mb-4 rounded-full bg-slate-50 p-4">
                <MessageSquare size={32} className="opacity-40" />
              </div>
              <p className="text-sm">Ask questions about the evaluation results and publication readiness.</p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {chatSuggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => handleChat(suggestion)}
                    className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 transition-all hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-600"
                  >
                    <Lightbulb size={12} className="text-amber-400" /> {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            chatHistory.map((message, index) => (
              <div key={`${message.role}-${index}`} className={clsx('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}>
                <div
                  className={clsx(
                    'max-w-[82%] rounded-2xl px-4 py-3 text-sm',
                    message.role === 'user'
                      ? 'rounded-tr-sm bg-indigo-600 text-white'
                      : 'rounded-tl-sm border border-slate-100 bg-white text-slate-800 shadow-sm'
                  )}
                >
                  <div
                    dangerouslySetInnerHTML={{
                      __html: sanitizeHtml(
                        message.content
                          .replace(/\n/g, '<br/>')
                          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                      ),
                    }}
                  />
                </div>
              </div>
            ))
          )}

          {chatLoading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm border border-slate-100 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">
                <Loader2 className="animate-spin" size={16} /> Thinking...
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="border-t border-slate-100 bg-slate-50/70 p-4">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              handleChat(chatInput);
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={chatInput}
              onChange={(event) => setChatInput(event.target.value)}
              placeholder="Ask a question about this evaluation..."
              className="flex-1 rounded-xl border border-slate-200 bg-white p-3 text-sm outline-none transition-all focus:border-indigo-300 focus:ring-2 focus:ring-indigo-500/20"
              disabled={chatLoading}
            />
            <button
              type="submit"
              disabled={!chatInput.trim() || chatLoading}
              className="rounded-xl bg-indigo-600 px-6 font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </div>
      </section>

      {expandedBidder && (
        <BidderDetailModal
          bidderName={expandedBidder}
          evaluation={evaluations[expandedBidder]}
          officerNotes={officerNotes}
          getOfficerNote={getOfficerNote}
          setOfficerNote={setOfficerNote}
          viewingSourceFor={viewingSourceFor}
          setViewingSourceFor={setViewingSourceFor}
          renderHighlightedText={renderHighlightedText}
          onOverride={handleOverrideVerdict}
          onClose={() => {
            setExpandedBidder(null);
            setViewingSourceFor(null);
          }}
          onPublish={() =>
            setActionDraft({
              type: evaluations[expandedBidder]?.overall_status === 'MANUAL_REVIEW' ? 'clarification' : 'publish',
              bidderName: expandedBidder,
            })
          }
          onSave={() => handleSaveOverrides(expandedBidder)}
          saving={savingBidder === expandedBidder}
        />
      )}

      {actionDraft && (
        <ActionModal
          actionDraft={actionDraft}
          evaluation={evaluations[actionDraft.bidderName]}
          contacts={contactDirectory[actionDraft.bidderName] || { emails: [], phones: [] }}
          actionChannel={actionChannel}
          setActionChannel={setActionChannel}
          actionRecipient={actionRecipient}
          setActionRecipient={setActionRecipient}
          actionMessage={actionMessage}
          setActionMessage={setActionMessage}
          onClose={() => setActionDraft(null)}
          onDispatch={handleDispatchAction}
        />
      )}
    </div>
  );
}

function MetricCard({ icon: Icon, label, value, tone }) {
  return (
    <div className={clsx('clean-card !mb-0 !p-5 border-l-4', toneClasses[tone])}>
      <div className="flex items-center gap-4">
        <div className="rounded-2xl bg-white/80 p-3">
          <Icon size={20} />
        </div>
        <div>
          <div className="text-xs font-bold uppercase tracking-[0.24em]">{label}</div>
          <div className="mt-2 text-3xl font-black">{value}</div>
        </div>
      </div>
    </div>
  );
}

function StatusPill({ tone, label }) {
  return (
    <span className={clsx('inline-flex rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-[0.18em]', toneClasses[tone])}>
      {label}
    </span>
  );
}

function BidderDetailModal({
  bidderName,
  evaluation,
  getOfficerNote,
  setOfficerNote,
  viewingSourceFor,
  setViewingSourceFor,
  renderHighlightedText,
  onOverride,
  onClose,
  onPublish,
  onSave,
  saving,
}) {
  const activeVerdict = evaluation?.verdicts?.find((verdict) => verdict.criterion_id === viewingSourceFor);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-[2rem] bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-8 py-6">
          <div>
            <div className="text-sm font-semibold text-slate-500">Detailed report</div>
            <h2 className="mt-1 text-2xl font-black text-slate-900">{bidderName}</h2>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onPublish}
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Open dispatch draft
            </button>
            <button
              onClick={onSave}
              disabled={saving}
              className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors disabled:opacity-60"
            >
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              Save overrides
            </button>
            <button onClick={onClose} className="rounded-full p-2 text-slate-400 hover:bg-white hover:text-slate-700 transition-colors">
              <X size={22} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto bg-slate-50/40 px-8 py-8">
          {evaluation?.anomaly_flag && (
            <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 text-red-600" size={18} />
                <div>
                  <div className="font-bold text-red-800">Financial anomaly detected</div>
                  <div className="mt-1 text-sm text-red-700">{evaluation.anomaly_reason}</div>
                </div>
              </div>
            </div>
          )}

          {viewingSourceFor && activeVerdict ? (
            <div className="space-y-4">
              <button
                onClick={() => setViewingSourceFor(null)}
                className="text-sm font-semibold text-indigo-600 hover:underline"
              >
                Back to bidder verdicts
              </button>
              <div className="rounded-[1.5rem] border border-slate-200 bg-white p-6">
                <div className="flex items-center gap-3">
                  <Search className="text-indigo-500" size={18} />
                  <div>
                    <div className="font-bold text-slate-900">{activeVerdict.criterion_id}</div>
                    <div className="text-sm text-slate-500">
                      {activeVerdict.evidence_used?.[0]?.source_document || 'Bidder submission'}
                    </div>
                  </div>
                </div>
                <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-5 max-h-[60vh] overflow-y-auto">
                  {renderHighlightedText(
                    evaluation.bidder_text_snapshot,
                    activeVerdict.evidence_used?.[0]?.exact_quote
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              {evaluation?.verdicts?.map((verdict) => (
                <div key={verdict.criterion_id} className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="pr-4">
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="text-lg font-bold text-slate-900">
                          {verdict.criterion_text || verdict.criterion_id}
                        </h3>
                        <StatusPill
                          tone={
                            verdict.status === 'ELIGIBLE'
                              ? 'green'
                              : verdict.status === 'MANUAL_REVIEW'
                                ? 'amber'
                                : 'red'
                          }
                          label={toSentenceCase(verdict.status)}
                        />
                      </div>
                      <div className="mt-2 text-xs font-bold uppercase tracking-[0.22em] text-indigo-600">
                        {verdict.criterion_type || 'Requirement'}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Confidence</div>
                      <div className="mt-2 text-2xl font-black text-slate-900">
                        {Math.round(Number(verdict.confidence || 0) * 100)}%
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 rounded-2xl border border-slate-100 bg-slate-50 p-5">
                    <div className="text-sm font-semibold text-slate-900">AI reasoning</div>
                    <div className="mt-2 text-sm leading-relaxed text-slate-600">{verdict.reasoning}</div>
                    <div className="mt-4 text-sm text-slate-600">
                      <span className="font-semibold text-slate-800">Evidence value:</span>{' '}
                      {verdict.evidence_used?.[0]?.value || 'Not found'}
                    </div>
                    <div className="mt-2 text-sm text-slate-600">
                      <span className="font-semibold text-slate-800">Evidence source:</span>{' '}
                      {verdict.evidence_used?.[0]?.source_document || 'Bidder submission'}
                    </div>
                  </div>

                  {verdict.status === 'MANUAL_REVIEW' && (
                    <div className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4">
                      <div className="flex-1 text-sm font-semibold text-amber-800">
                        This criterion needs an officer override before final publication.
                      </div>
                      <button
                        onClick={() => onOverride(bidderName, verdict.criterion_id, 'ELIGIBLE')}
                        className="flex items-center gap-1 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors"
                      >
                        <Check size={15} /> Accept
                      </button>
                      <button
                        onClick={() => onOverride(bidderName, verdict.criterion_id, 'NOT_ELIGIBLE')}
                        className="flex items-center gap-1 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 transition-colors"
                      >
                        <X size={15} /> Reject
                      </button>
                    </div>
                  )}

                  <textarea
                    className="mt-4 min-h-[88px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition-all focus:border-indigo-300 focus:ring-2 focus:ring-indigo-500/20"
                    placeholder="Officer note for this criterion..."
                    value={getOfficerNote(bidderName, verdict.criterion_id)}
                    onChange={(event) => setOfficerNote(bidderName, verdict.criterion_id, event.target.value)}
                  />

                  {verdict.evidence_used?.[0]?.exact_quote ? (
                    <button
                      onClick={() => setViewingSourceFor(verdict.criterion_id)}
                      className="mt-4 flex items-center gap-2 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors"
                    >
                      <Search size={16} /> View highlighted evidence
                    </button>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ActionModal({
  actionDraft,
  evaluation,
  contacts,
  actionChannel,
  setActionChannel,
  actionRecipient,
  setActionRecipient,
  actionMessage,
  setActionMessage,
  onClose,
  onDispatch,
}) {
  const isClarification = actionDraft.type === 'clarification';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-3xl rounded-[2rem] bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="border-b border-slate-100 px-8 py-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-xs font-bold uppercase tracking-[0.26em] text-slate-400">
                {isClarification ? 'Clarification request' : 'Publish result'}
              </div>
              <h3 className="mt-2 text-2xl font-black text-slate-900">{actionDraft.bidderName}</h3>
              <p className="mt-2 text-sm text-slate-600">
                Outcome: {toSentenceCase(evaluation?.overall_status || 'MANUAL_REVIEW')}
              </p>
            </div>
            <button onClick={onClose} className="rounded-full p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors">
              <X size={22} />
            </button>
          </div>
        </div>

        <div className="space-y-6 px-8 py-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                <Mail size={16} className="text-indigo-500" /> Email contacts
              </div>
              <div className="mt-3 text-sm text-slate-600">
                {contacts.emails.length ? contacts.emails.join(', ') : 'No email detected'}
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                <Smartphone size={16} className="text-indigo-500" /> Phone contacts
              </div>
              <div className="mt-3 text-sm text-slate-600">
                {contacts.phones.length ? contacts.phones.join(', ') : 'No phone number detected'}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-[180px,1fr] gap-4">
            <div>
              <label className="text-sm font-semibold text-slate-700">Channel</label>
              <select
                value={actionChannel}
                onChange={(event) => setActionChannel(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-500/20"
              >
                <option value="EMAIL">Email</option>
                <option value="SMS">SMS</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-semibold text-slate-700">Recipient</label>
              <input
                type="text"
                value={actionRecipient}
                onChange={(event) => setActionRecipient(event.target.value)}
                placeholder="Enter email or phone number"
                className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-500/20"
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-semibold text-slate-700">Draft message</label>
            <textarea
              value={actionMessage}
              onChange={(event) => setActionMessage(event.target.value)}
              className="mt-2 min-h-[220px] w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-700 outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-500/20"
            />
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-slate-100 px-8 py-5">
          <div className="text-sm text-slate-500">Prototype behavior: adds a delivery entry to the communication log.</div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button onClick={onDispatch} className="btn-primary-wow px-5 py-2.5 flex items-center gap-2">
              <Send size={16} /> Dispatch
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
