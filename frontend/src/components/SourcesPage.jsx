import { Activity, Database, Globe, UploadCloud } from 'lucide-react';
import { buildSourceAdapters } from '../workspace-utils';

const toneStyles = {
  green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  amber: 'bg-amber-50 text-amber-700 border-amber-200',
  blue: 'bg-blue-50 text-blue-700 border-blue-200',
};

const icons = {
  GeM: Globe,
  DefProc: Activity,
  Uploads: UploadCloud,
};

export default function SourcesPage({ tenderData }) {
  const adapters = buildSourceAdapters(tenderData);

  return (
    <div className="max-w-6xl mx-auto mt-6 space-y-8 pb-10">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-indigo-600">Sources</p>
        <h2 className="mt-3 text-4xl font-black text-slate-900 tracking-tight">Portal adapters and import posture</h2>
        <p className="mt-3 text-slate-600 max-w-3xl leading-relaxed">
          This ideathon surface shows where TenderSight can ingest work from, whether the connector is healthy,
          and how many bundle artifacts are currently attached to the workspace.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {adapters.map((adapter) => {
          const Icon = icons[adapter.name] || Database;
          return (
            <div key={adapter.name} className="clean-card !mb-0">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-3">
                    <div className="p-3 rounded-2xl bg-slate-50 border border-slate-100 text-slate-700">
                      <Icon size={20} />
                    </div>
                    <div>
                      <h3 className="text-2xl font-black text-slate-900">{adapter.name}</h3>
                      <p className="text-sm text-slate-500">{adapter.mode}</p>
                    </div>
                  </div>
                </div>
                <span className={`badge-sm border ${toneStyles[adapter.tone]}`}>{adapter.status}</span>
              </div>

              <div className="mt-6 grid grid-cols-2 gap-4">
                <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
                  <div className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Fetches</div>
                  <div className="mt-3 text-3xl font-black text-slate-900">{adapter.fetches}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
                  <div className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Status</div>
                  <div className="mt-3 text-lg font-bold text-slate-900">{adapter.mode}</div>
                </div>
              </div>

              <p className="mt-6 text-sm text-slate-600 leading-relaxed">{adapter.note}</p>
            </div>
          );
        })}
      </div>

      <div className="clean-card !mb-0">
        <div className="flex items-center gap-3 mb-4">
          <Database className="text-indigo-500" size={18} />
          <h3 className="text-lg font-bold text-slate-900">Import log concept</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
            <div className="font-bold text-slate-800">Last upload batch</div>
            <div className="mt-2 text-slate-600">
              {tenderData?.bundle_documents?.length
                ? `${tenderData.bundle_documents.length} document(s) processed for ${tenderData.tender_id}.`
                : 'No bundle uploaded in this session.'}
            </div>
          </div>
          <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
            <div className="font-bold text-slate-800">Connector model</div>
            <div className="mt-2 text-slate-600">Operator-triggered imports only. No silent polling or hidden acquisitions.</div>
          </div>
          <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
            <div className="font-bold text-slate-800">Ideathon note</div>
            <div className="mt-2 text-slate-600">GeM and DefProc adapters are surfaced as product concepts with explicit health indicators and local upload fallback.</div>
          </div>
        </div>
      </div>
    </div>
  );
}
