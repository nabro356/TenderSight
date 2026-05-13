import { FileBadge, FileCheck2, FileStack, ScanSearch } from 'lucide-react';

export default function BundleWorkspace({ tenderData, onOpenUpload }) {
  if (!tenderData) {
    return (
      <div className="max-w-5xl mx-auto mt-10">
        <div className="clean-card text-center !p-10">
          <div className="mx-auto w-16 h-16 rounded-3xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <FileStack size={30} />
          </div>
          <h2 className="mt-5 text-3xl font-black text-slate-900">No active tender bundle yet</h2>
          <p className="mt-3 text-slate-600 max-w-2xl mx-auto">
            Start with one or more tender documents. TenderSight will combine them into a bundle,
            parse each source, extract criteria, and keep the document trail visible for review.
          </p>
          <button onClick={onOpenUpload} className="mt-6 btn-primary-wow px-6 py-3">
            Upload Tender Bundle
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto mt-6 space-y-8 pb-10">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-indigo-600">Bundle Workspace</p>
        <h2 className="mt-3 text-4xl font-black text-slate-900 tracking-tight">Tender bundle, parse state, and source pages</h2>
        <p className="mt-3 text-slate-600 max-w-3xl leading-relaxed">
          TenderSight now treats the tender as a bundle instead of a single upload. Each document carries a parse status,
          page count, engine, and confidence so the briefing can point back to the right source.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.15fr,1.85fr] gap-6">
        <div className="clean-card !mb-0">
          <div className="flex items-center gap-3 mb-5">
            <FileBadge className="text-indigo-500" size={18} />
            <h3 className="text-lg font-bold text-slate-900">Documents</h3>
          </div>

          <div className="space-y-3">
            {tenderData.bundle_documents?.map((doc) => (
              <div key={doc.name} className="rounded-2xl border border-slate-200 bg-white/80 px-4 py-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-semibold text-slate-800">{doc.name}</div>
                    <div className="text-xs text-slate-500 mt-1">
                      {doc.pages || 0} page(s) · {doc.ocr_engine} · {Math.round((doc.confidence || 0) * 100)}% confidence
                    </div>
                  </div>
                  <span className="badge-sm badge-eligible">{doc.status}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 rounded-2xl border border-slate-100 bg-slate-50 p-4 text-sm text-slate-600">
            <div className="font-bold text-slate-800">Bundle totals</div>
            <div className="mt-2">{tenderData.bundle_documents?.length || 0} document(s)</div>
            <div className="mt-1">{tenderData.pages || 0} total pages</div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="clean-card !mb-0">
            <div className="flex items-center gap-3 mb-4">
              <ScanSearch className="text-indigo-500" size={18} />
              <h3 className="text-lg font-bold text-slate-900">Extraction summary</h3>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
                <div className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Tender ID</div>
                <div className="mt-3 text-lg font-bold text-slate-900">{tenderData.tender_id}</div>
              </div>
              <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
                <div className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Criteria</div>
                <div className="mt-3 text-3xl font-black text-slate-900">{tenderData.criteria?.length || 0}</div>
              </div>
              <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
                <div className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">OCR Engine</div>
                <div className="mt-3 text-lg font-bold text-slate-900">{tenderData.ocr_engine}</div>
              </div>
              <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
                <div className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Confidence</div>
                <div className="mt-3 text-3xl font-black text-slate-900">{Math.round((tenderData.confidence || 0) * 100)}%</div>
              </div>
            </div>
          </div>

          <div className="clean-card !mb-0">
            <div className="flex items-center gap-3 mb-4">
              <FileCheck2 className="text-indigo-500" size={18} />
              <h3 className="text-lg font-bold text-slate-900">Raw text preview</h3>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 max-h-[420px] overflow-y-auto">
              <pre className="whitespace-pre-wrap text-sm text-slate-700 font-mono leading-relaxed">
                {tenderData.raw_text?.slice(0, 5000) || 'No extracted text available.'}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
