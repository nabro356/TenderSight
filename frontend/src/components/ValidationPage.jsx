import { BadgeCheck, ClipboardCheck, Microscope, ScrollText } from 'lucide-react';

export default function ValidationPage() {
  return (
    <div className="max-w-6xl mx-auto mt-6 space-y-8 pb-10">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-indigo-600">Validation Dossier</p>
        <h2 className="mt-3 text-4xl font-black text-slate-900 tracking-tight">Proof, without hype</h2>
        <p className="mt-3 text-slate-600 max-w-3xl leading-relaxed">
          This page exists to do what strong competitors do well: separate what is implemented, what is demonstrated,
          what is mocked for ideathon storytelling, and what remains roadmap.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ValidationCard
          icon={BadgeCheck}
          title="Implemented today"
          items={[
            'Tender ingestion, criteria extraction, bidder evaluation, and report generation',
            'Human override flow with officer-controlled verdict changes',
            'Fraud signaling through anomaly and cartel checks',
            'Report Q&A via the embedded chat surface',
          ]}
        />
        <ValidationCard
          icon={Microscope}
          title="Demonstrated in prototype"
          items={[
            'Tender queue, source adapters, bundle workspace, and briefing views',
            'Publication / clarification workflow with contact extraction and dispatch log',
            'Security, validation, and roadmap trust surfaces',
            'Operator note capture for ambiguities and missing evidence',
          ]}
        />
      </div>

      <div className="clean-card !mb-0">
        <div className="flex items-center gap-3 mb-4">
          <ClipboardCheck className="text-indigo-500" size={18} />
          <h3 className="text-lg font-bold text-slate-900">Claim discipline</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <StatusBox label="Observed" text="Screens, operator flows, and seeded tender workspaces visible in the product." />
          <StatusBox label="Validated" text="Core evaluation pipeline and backend scoring flows implemented in the repo." />
          <StatusBox label="Roadmap" text="Live production notifications, hardened auth, and deeper tender discovery integrations." />
        </div>
      </div>

      <div className="clean-card !mb-0">
        <div className="flex items-center gap-3 mb-4">
          <ScrollText className="text-indigo-500" size={18} />
          <h3 className="text-lg font-bold text-slate-900">Public-safe wording</h3>
        </div>
        <div className="space-y-3 text-sm text-slate-600">
          <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
            “AI-assisted tender evaluation with officer-controlled overrides and source-linked audit trail.”
          </div>
          <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
            “Publish and clarification workflows are demonstrated in prototype form for ideathon evaluation.”
          </div>
          <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
            “No government endorsement is claimed or implied.”
          </div>
        </div>
      </div>
    </div>
  );
}

function ValidationCard({ icon: Icon, title, items }) {
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

function StatusBox({ label, text }) {
  return (
    <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
      <div className="text-xs font-bold uppercase tracking-[0.24em] text-slate-400">{label}</div>
      <div className="mt-3 text-slate-700 font-medium leading-relaxed">{text}</div>
    </div>
  );
}
