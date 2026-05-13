import { BriefcaseBusiness, CalendarClock, FileBadge2, Landmark, Scale, ShieldCheck } from 'lucide-react';
import { deriveRecommendation, formatMoney } from '../workspace-utils';

const toneClass = {
  blue: 'bg-blue-50 border-blue-200 text-blue-800',
  green: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  amber: 'bg-amber-50 border-amber-200 text-amber-800',
  red: 'bg-red-50 border-red-200 text-red-800',
  slate: 'bg-slate-50 border-slate-200 text-slate-800',
};

export default function TenderBriefing({ tenderData, evaluations, onContinue }) {
  if (!tenderData) {
    return null;
  }

  const metadata = tenderData.metadata || {};
  const recommendation = deriveRecommendation(tenderData, evaluations);
  const sourceCount = tenderData.bundle_documents?.length || 0;

  return (
    <div className="max-w-6xl mx-auto mt-6 space-y-8 pb-10">
      <div className="glass-panel rounded-[2rem] p-8 relative overflow-hidden">
        <div className="absolute right-0 inset-y-0 w-80 bg-gradient-to-l from-indigo-500/10 to-transparent" />
        <div className="relative z-10">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-indigo-600">Tender Briefing</p>
          <div className="mt-4 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <h2 className="text-4xl font-black text-slate-900 tracking-tight">
                {metadata.title || tenderData.filename || 'Tender bundle briefing'}
              </h2>
              <p className="mt-3 text-slate-600 leading-relaxed">
                Executive summary before bidder evaluation. Review the authority, dates, EMD, estimated value,
                portal, and recommendation banner before pushing the bundle into the evaluation stage.
              </p>
            </div>
            <button onClick={onContinue} className="btn-primary-wow px-6 py-3 shrink-0">
              Continue To Bidder Evaluation
            </button>
          </div>

          <div className={`mt-8 rounded-[1.5rem] border p-6 ${toneClass[recommendation.tone]}`}>
            <div className="text-xs font-bold uppercase tracking-[0.3em]">Recommendation Banner</div>
            <div className="mt-3 text-4xl font-black">{recommendation.label}</div>
            <p className="mt-3 text-base leading-relaxed max-w-3xl">{recommendation.summary}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-5">
        <BriefingMetric icon={Landmark} label="Authority" value={metadata.authority || 'Needs confirmation'} />
        <BriefingMetric icon={CalendarClock} label="Closing Date" value={metadata.closing_date || 'Not detected'} />
        <BriefingMetric icon={Scale} label="EMD" value={formatMoney(metadata.emd_amount)} />
        <BriefingMetric icon={BriefcaseBusiness} label="Estimated Value" value={formatMoney(metadata.estimated_value)} />
        <BriefingMetric icon={FileBadge2} label="Portal" value={metadata.portal || 'Upload workflow'} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.4fr,1fr] gap-6">
        <div className="clean-card !mb-0">
          <div className="flex items-center gap-3 mb-4">
            <ShieldCheck className="text-indigo-500" size={18} />
            <h3 className="text-lg font-bold text-slate-900">Procurement summary</h3>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <SummaryRow label="Tender ID" value={tenderData.tender_id} />
            <SummaryRow label="Source documents" value={`${sourceCount} bundle file(s)`} />
            <SummaryRow label="Pages processed" value={`${tenderData.pages || 0} pages`} />
            <SummaryRow label="OCR confidence" value={`${Math.round((tenderData.confidence || 0) * 100)}%`} />
            <SummaryRow label="Criteria extracted" value={`${tenderData.criteria?.length || 0} clauses`} />
            <SummaryRow label="Primary engine" value={tenderData.ocr_engine || 'Auto'} />
            <SummaryRow label="Pre-bid date" value={metadata.pre_bid_date || 'Not detected'} />
            <SummaryRow label="Workspace mode" value="Bundle → Extract → Evaluate → Publish" />
          </div>
        </div>

        <div className="clean-card !mb-0">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">Operator notes</p>
          <h3 className="mt-2 text-2xl font-black text-slate-900">Why this screen matters</h3>
          <div className="mt-4 space-y-3 text-sm text-slate-600 leading-relaxed">
            <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
              Judges can immediately see TenderSight is reading a procurement bundle, not just a file.
            </div>
            <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
              The metadata panel makes your product feel much closer to actual operator software.
            </div>
            <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
              This screen bridges the jump between upload and evaluation, which was one of the biggest gaps before.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function BriefingMetric({ icon: Icon, label, value }) {
  return (
    <div className="clean-card !mb-0 !p-5 border-l-4 border-l-indigo-500">
      <div className="flex items-center gap-3">
        <div className="p-3 rounded-2xl bg-indigo-50 text-indigo-600">
          <Icon size={18} />
        </div>
        <div>
          <div className="text-xs font-bold uppercase tracking-[0.24em] text-slate-400">{label}</div>
          <div className="mt-2 font-bold text-slate-900 leading-tight">{value}</div>
        </div>
      </div>
    </div>
  );
}

function SummaryRow({ label, value }) {
  return (
    <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
      <div className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">{label}</div>
      <div className="mt-2 font-semibold text-slate-800">{value}</div>
    </div>
  );
}
