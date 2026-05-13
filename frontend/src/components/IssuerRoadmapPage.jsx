import { Compass, FileSignature, SearchCheck, Sparkles } from 'lucide-react';

export default function IssuerRoadmapPage() {
  return (
    <div className="max-w-6xl mx-auto mt-6 space-y-8 pb-10">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-indigo-600">Issuer Roadmap</p>
        <h2 className="mt-3 text-4xl font-black text-slate-900 tracking-tight">What TenderSight can grow into next</h2>
        <p className="mt-3 text-slate-600 max-w-3xl leading-relaxed">
          Unlike bidder-side tender intelligence tools, TenderSight already starts from issuer-side evaluation.
          This roadmap page helps you tell judges that the current prototype is a working base, not just an idea.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <RoadmapCard
          icon={SearchCheck}
          title="Near-term"
          items={[
            'Live GeM / DefProc assisted discovery inside the queue',
            'Corrigendum diffing across tender bundle versions',
            'Officer-approved publish / clarification messaging with delivery receipts',
          ]}
        />
        <RoadmapCard
          icon={FileSignature}
          title="Mid-term"
          items={[
            'Signed result packets and bidder-facing secure access links',
            'Cross-tender entity intelligence and repeat-risk scoring',
            'Role-based approvals across evaluator, reviewer, and authority',
          ]}
        />
        <RoadmapCard
          icon={Compass}
          title="Exploration"
          items={[
            'RFP ambiguity surfacing before publication',
            'Tender drafting guidance for clearer procurement language',
            'Policy-aware multilingual procurement intelligence at scale',
          ]}
        />
      </div>

      <div className="clean-card !mb-0">
        <div className="flex items-center gap-3 mb-4">
          <Sparkles className="text-indigo-500" size={18} />
          <h3 className="text-lg font-bold text-slate-900">Pitch angle for judges</h3>
        </div>
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
            “Others are roadmap-heavy on issuer-side intelligence. TenderSight already demonstrates issuer-side evaluation and now extends into operator workflow.”
          </div>
          <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
            “This roadmap is an expansion layer, not the first proof of value.”
          </div>
        </div>
      </div>
    </div>
  );
}

function RoadmapCard({ icon: Icon, title, items }) {
  return (
    <div className="clean-card !mb-0">
      <div className="flex items-center gap-3 mb-5">
        <div className="p-3 rounded-2xl bg-indigo-50 text-indigo-600">
          <Icon size={20} />
        </div>
        <h3 className="text-2xl font-black text-slate-900">{title}</h3>
      </div>
      <div className="space-y-3 text-sm text-slate-600">
        {items.map((item) => (
          <div key={item} className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
