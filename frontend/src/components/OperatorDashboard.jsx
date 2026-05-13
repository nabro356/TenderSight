import { ArrowRight, Clock3, FileStack, ListTodo, ShieldCheck, UploadCloud } from 'lucide-react';
import { buildQueueItems, deriveRecommendation } from '../workspace-utils';

const laneStyles = {
  Action: 'border-blue-500 bg-blue-50 text-blue-700',
  Ready: 'border-emerald-500 bg-emerald-50 text-emerald-700',
  Waiting: 'border-amber-500 bg-amber-50 text-amber-700',
  Blocked: 'border-red-500 bg-red-50 text-red-700',
};

export default function OperatorDashboard({
  tenderData,
  evaluations,
  onOpenBundle,
  onOpenSources,
  onOpenResults,
}) {
  const recommendation = deriveRecommendation(tenderData, evaluations);
  const queue = buildQueueItems(tenderData, evaluations);

  const laneCounts = {
    Action: queue.filter((item) => item.state.includes('ACTION')).length,
    Ready: queue.filter((item) => item.state.includes('READY') || item.state.includes('PUBLISH')).length,
    Waiting: queue.filter((item) => item.state.includes('WAIT') || item.state.includes('REVIEW')).length,
    Blocked: queue.filter((item) => item.state.includes('BLOCK') || item.state.includes('DECISION')).length,
  };

  return (
    <div className="max-w-7xl mx-auto mt-6 space-y-8 pb-10">
      <div className="glass-panel rounded-[2rem] p-8 relative overflow-hidden">
        <div className="absolute inset-y-0 right-0 w-96 bg-gradient-to-l from-indigo-500/10 to-transparent" />
        <div className="relative z-10 flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-indigo-600">Operator Control Surface</p>
            <h2 className="mt-3 text-4xl font-black tracking-tight text-slate-900">What needs action now</h2>
            <p className="mt-3 text-slate-600 leading-relaxed">
              TenderSight now works like an operator platform: queue the bundle, inspect sources,
              generate the briefing, evaluate bidders, then publish or seek clarification with an audit trail.
            </p>
            <div className="mt-6 inline-flex items-center gap-3 rounded-full bg-white/80 px-4 py-2 border border-white shadow-sm">
              <ShieldCheck size={18} className="text-indigo-600" />
              <span className="text-sm font-semibold text-slate-700">{recommendation.label}</span>
              <span className="text-sm text-slate-500">{recommendation.summary}</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={onOpenBundle}
              className="btn-primary-wow px-5 py-3 flex items-center gap-2"
            >
              <UploadCloud size={18} /> Start Tender Bundle
            </button>
            <button
              onClick={onOpenSources}
              className="px-5 py-3 rounded-xl bg-white/90 border border-slate-200 font-semibold text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-2"
            >
              <FileStack size={18} /> Open Sources
            </button>
            <button
              onClick={onOpenResults}
              className="px-5 py-3 rounded-xl bg-white/90 border border-slate-200 font-semibold text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-2"
            >
              <ArrowRight size={18} /> Review Results
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-5">
        {Object.entries(laneCounts).map(([lane, count]) => (
          <div key={lane} className={`clean-card !mb-0 !p-5 border-l-4 ${laneStyles[lane]}`}>
            <div className="text-xs font-bold uppercase tracking-[0.28em]">{lane}</div>
            <div className="mt-4 text-4xl font-black">{count}</div>
            <p className="mt-2 text-sm opacity-80">
              {lane === 'Action' && 'Tenders demanding immediate operator attention.'}
              {lane === 'Ready' && 'Workspaces clear for next-stage progression.'}
              {lane === 'Waiting' && 'Cases pending review, uploads, or clarifications.'}
              {lane === 'Blocked' && 'Cases held by missing data or unresolved decisions.'}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.6fr,1fr] gap-6">
        <div className="clean-card !mb-0">
          <div className="flex items-center justify-between mb-5">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">Tender Queue</p>
              <h3 className="mt-2 text-2xl font-black text-slate-900">Urgent deadlines and recent decisions</h3>
            </div>
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Clock3 size={16} />
              Operator-view prototype
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-xs uppercase tracking-[0.26em] text-slate-400 border-b border-slate-100">
                  <th className="py-3 px-3">State</th>
                  <th className="py-3 px-3">Title</th>
                  <th className="py-3 px-3">Authority</th>
                  <th className="py-3 px-3">Deadline</th>
                  <th className="py-3 px-3">Source</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((item) => (
                  <tr key={item.id} className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50/70">
                    <td className="py-4 px-3">
                      <span className={`badge-sm ${
                        item.state.includes('READY')
                          ? 'badge-eligible'
                          : item.state.includes('WAIT') || item.state.includes('REVIEW')
                            ? 'badge-review'
                            : item.state.includes('BLOCK') || item.state.includes('DECISION')
                              ? 'badge-not-eligible'
                              : 'badge-sm bg-blue-50 text-blue-700 border border-blue-100'
                      }`}>
                        {item.state}
                      </span>
                    </td>
                    <td className="py-4 px-3">
                      <div className="font-semibold text-slate-800">{item.title}</div>
                      <div className="text-xs text-slate-500 mt-1">{item.id}</div>
                    </td>
                    <td className="py-4 px-3 text-slate-600">{item.authority}</td>
                    <td className="py-4 px-3 text-slate-600">{item.deadline}</td>
                    <td className="py-4 px-3 text-slate-600">{item.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-6">
          <div className="clean-card !mb-0">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">Operational Metrics</p>
            <div className="mt-5 grid grid-cols-2 gap-4">
              <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
                <div className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Open Bundles</div>
                <div className="mt-3 text-3xl font-black text-slate-900">{tenderData ? 1 : 0}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
                <div className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Criteria Extracted</div>
                <div className="mt-3 text-3xl font-black text-slate-900">{tenderData?.criteria?.length || 0}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
                <div className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Bidders Evaluated</div>
                <div className="mt-3 text-3xl font-black text-slate-900">{evaluations ? Object.keys(evaluations).length : 0}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
                <div className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Bundle Pages</div>
                <div className="mt-3 text-3xl font-black text-slate-900">{tenderData?.pages || 0}</div>
              </div>
            </div>
          </div>

          <div className="clean-card !mb-0">
            <div className="flex items-center gap-3 mb-4">
              <ListTodo className="text-indigo-500" size={18} />
              <h3 className="text-lg font-bold text-slate-900">Operator Checklist</h3>
            </div>
            <div className="space-y-3 text-sm text-slate-600">
              <div className="rounded-xl bg-slate-50 border border-slate-100 p-4">1. Import or upload the tender bundle.</div>
              <div className="rounded-xl bg-slate-50 border border-slate-100 p-4">2. Verify metadata, source pages, and extracted criteria.</div>
              <div className="rounded-xl bg-slate-50 border border-slate-100 p-4">3. Evaluate bidders, resolve ambiguities, and record notes.</div>
              <div className="rounded-xl bg-slate-50 border border-slate-100 p-4">4. Publish results or request clarifications with a communication log.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
