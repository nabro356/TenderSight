import { GlobeLock, ServerCog, Shield, Waypoints } from 'lucide-react';

export default function BoundaryPage() {
  return (
    <div className="max-w-6xl mx-auto mt-6 space-y-8 pb-10">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-indigo-600">Security & Boundary</p>
        <h2 className="mt-3 text-4xl font-black text-slate-900 tracking-tight">What stays local, what crosses, and what we refuse to claim</h2>
        <p className="mt-3 text-slate-600 max-w-3xl leading-relaxed">
          This is the ideathon-safe trust surface. It makes your platform feel deliberate and enterprise-aware,
          while staying honest about what is local, what is configurable, and what is still prototype territory.
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <BoundaryCard
          icon={Shield}
          title="Inside the boundary"
          tone="green"
          items={[
            'Tender bundle storage on local workspace / deployment node',
            'Bidder submissions and evaluation records',
            'Source-linked evidence, officer overrides, and audit notes',
            'Document parsing, criteria extraction, and report generation',
          ]}
        />
        <BoundaryCard
          icon={Waypoints}
          title="Across the boundary"
          tone="amber"
          items={[
            'Portal access such as GeM / DefProc when configured',
            'Optional email or SMS publication flows after officer approval',
            'Optional hosted model routes for demo deployments',
            'Any integration is explicit, reviewable, and operator-triggered',
          ]}
        />
      </div>

      <div className="clean-card !mb-0">
        <div className="flex items-center gap-3 mb-4">
          <ServerCog className="text-indigo-500" size={18} />
          <h3 className="text-lg font-bold text-slate-900">What TenderSight should not claim</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          {[
            'NOT a fully autonomous government decision-maker',
            'NOT a blanket security guarantee',
            'NOT a silent portal scraper with hidden egress',
            'NOT a substitute for officer review or legal approval',
            'NOT claiming any government endorsement unless explicitly granted',
            'NOT production-grade notification infra by default in this prototype',
          ].map((item) => (
            <div key={item} className="rounded-2xl bg-slate-50 border border-slate-100 p-4 font-semibold text-slate-700">
              {item}
            </div>
          ))}
        </div>
      </div>

      <div className="clean-card !mb-0">
        <div className="flex items-center gap-3 mb-4">
          <GlobeLock className="text-indigo-500" size={18} />
          <h3 className="text-lg font-bold text-slate-900">Prototype posture</h3>
        </div>
        <p className="text-sm text-slate-600 leading-relaxed">
          For this ideathon build, publication workflows, source adapters, and trust surfaces are designed as
          operator-visible features. Nothing should look “magical.” That clarity itself is a competitive advantage.
        </p>
      </div>
    </div>
  );
}

function BoundaryCard({ icon: Icon, title, tone, items }) {
  const borderTone = tone === 'green' ? 'border-emerald-500 bg-emerald-50/60' : 'border-amber-500 bg-amber-50/60';

  return (
    <div className={`clean-card !mb-0 border-l-4 ${borderTone}`}>
      <div className="flex items-center gap-3 mb-5">
        <div className="p-3 rounded-2xl bg-white border border-white shadow-sm text-slate-700">
          <Icon size={20} />
        </div>
        <h3 className="text-2xl font-black text-slate-900">{title}</h3>
      </div>
      <div className="space-y-3 text-sm text-slate-600">
        {items.map((item) => (
          <div key={item} className="rounded-2xl bg-white/80 border border-white p-4">
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
