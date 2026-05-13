import { useMemo, useState } from 'react';
import {
  BadgeCheck,
  BookOpenCheck,
  BriefcaseBusiness,
  Compass,
  FileStack,
  Gauge,
  LogOut,
  Radar,
  RotateCcw,
  Scale,
  Send,
  ShieldCheck,
  Sparkles,
  UsersRound,
  Workflow,
} from 'lucide-react';
import LoginPage from './components/LoginPage';
import TenderUpload from './components/TenderUpload';
import BidderManagement from './components/BidderManagement';
import ResultsDashboard from './components/ResultsDashboard';
import OperatorDashboard from './components/OperatorDashboard';
import SourcesPage from './components/SourcesPage';
import BundleWorkspace from './components/BundleWorkspace';
import TenderBriefing from './components/TenderBriefing';
import BoundaryPage from './components/BoundaryPage';
import ValidationPage from './components/ValidationPage';
import IssuerRoadmapPage from './components/IssuerRoadmapPage';

const WORKSPACE_NAV = [
  { id: 'dashboard', label: 'Operator Home', icon: Gauge },
  { id: 'sources', label: 'Sources', icon: Radar },
  { id: 'bundle', label: 'Bundle Workspace', icon: FileStack },
  { id: 'briefing', label: 'Tender Briefing', icon: BriefcaseBusiness },
  { id: 'bidders', label: 'Bidder Evaluation', icon: UsersRound },
  { id: 'results', label: 'Publish & Results', icon: Send },
];

const TRUST_NAV = [
  { id: 'boundary', label: 'Security Boundary', icon: ShieldCheck },
  { id: 'validation', label: 'Validation Dossier', icon: BadgeCheck },
  { id: 'roadmap', label: 'Issuer Roadmap', icon: Compass },
];

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeView, setActiveView] = useState('dashboard');
  const [tenderData, setTenderData] = useState(null);
  const [bidders, setBidders] = useState([]);
  const [evaluations, setEvaluations] = useState(null);
  const [cartelAlerts, setCartAlerts] = useState([]);
  const [dispatchLog, setDispatchLog] = useState([]);

  const resetAll = () => {
    setActiveView('dashboard');
    setTenderData(null);
    setBidders([]);
    setEvaluations(null);
    setCartAlerts([]);
    setDispatchLog([]);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    resetAll();
  };

  const handleTenderProcessed = (data) => {
    setTenderData(data);
    setEvaluations(null);
    setBidders([]);
    setCartAlerts([]);
    setDispatchLog([]);
    setActiveView('briefing');
  };

  const workflowProgress = useMemo(() => {
    if (!tenderData) return 1;
    if (!evaluations) {
      return activeView === 'briefing' ? 2 : activeView === 'bidders' ? 3 : 2;
    }
    if (!dispatchLog.length) return 4;
    return 5;
  }, [activeView, dispatchLog.length, evaluations, tenderData]);

  if (!isAuthenticated) {
    return <LoginPage onLogin={() => setIsAuthenticated(true)} />;
  }

  const hasTender = Boolean(tenderData);
  const hasResults = Boolean(evaluations && Object.keys(evaluations).length);

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-background">
      <aside className="w-full md:w-80 bg-white/80 backdrop-blur-xl border-r border-white sticky top-0 flex flex-col md:h-screen">
        <div className="p-6 border-b border-slate-100">
          <div className="flex items-center gap-3 text-2xl font-extrabold mb-2">
            <div className="p-3 rounded-2xl bg-indigo-50 text-indigo-600">
              <Scale size={26} />
            </div>
            <div>
              <span className="text-gradient-wow block">TenderSight</span>
              <span className="text-[11px] uppercase tracking-[0.28em] text-slate-400 font-bold">
                Issuer-Side Procurement Intelligence
              </span>
            </div>
          </div>
          <p className="text-sm text-slate-500 leading-relaxed">
            From tender bundle to officer-reviewed decision and publish workflow.
          </p>
        </div>

        <div className="px-6 py-5 border-b border-slate-100">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-400">Pipeline</p>
          <div className="mt-4 space-y-3">
            {[
              'Bundle',
              'Briefing',
              'Evaluate',
              'Results',
              'Publish',
            ].map((stepLabel, index) => {
              const step = index + 1;
              const complete = workflowProgress > step;
              const active = workflowProgress === step;
              return (
                <div key={stepLabel} className={`flex items-center gap-3 ${active ? 'text-indigo-700' : complete ? 'text-emerald-700' : 'text-slate-400'}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    complete ? 'bg-emerald-500 text-white' : active ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-500'
                  }`}>
                    {complete ? '✓' : step}
                  </div>
                  <span className={`text-sm ${active || complete ? 'font-bold' : 'font-medium'}`}>{stepLabel}</span>
                </div>
              );
            })}
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-4 py-5 space-y-6">
          <NavSection
            title="Workspace"
            items={WORKSPACE_NAV}
            activeView={activeView}
            setActiveView={setActiveView}
            disableRule={(id) => (['briefing', 'bidders', 'results'].includes(id) && !hasTender) || (id === 'results' && !hasResults)}
          />
          <NavSection
            title="Trust"
            items={TRUST_NAV}
            activeView={activeView}
            setActiveView={setActiveView}
          />
        </nav>

        <div className="p-4 border-t border-slate-100 space-y-2">
          <button
            onClick={resetAll}
            className="w-full py-2.5 px-4 flex items-center justify-center gap-2 text-sm font-semibold text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors"
          >
            <RotateCcw size={16} /> Reset Workspace
          </button>
          <button
            onClick={handleLogout}
            className="w-full py-2.5 px-4 flex items-center justify-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors"
          >
            <LogOut size={16} /> Logout
          </button>
        </div>
      </aside>

      <main className="flex-1 p-6 md:p-10 overflow-y-auto h-screen">
        <TopRibbon tenderData={tenderData} evaluations={evaluations} dispatchLog={dispatchLog} />

        {activeView === 'dashboard' && (
          <OperatorDashboard
            tenderData={tenderData}
            evaluations={evaluations}
            onOpenBundle={() => setActiveView('bundle')}
            onOpenSources={() => setActiveView('sources')}
            onOpenResults={() => setActiveView(hasResults ? 'results' : hasTender ? 'briefing' : 'bundle')}
          />
        )}

        {activeView === 'sources' && <SourcesPage tenderData={tenderData} />}

        {activeView === 'bundle' && (
          hasTender ? (
            <BundleWorkspace tenderData={tenderData} onOpenUpload={() => setActiveView('bundle')} />
          ) : (
            <TenderUpload onTenderProcessed={handleTenderProcessed} />
          )
        )}

        {activeView === 'briefing' && hasTender && (
          <TenderBriefing
            tenderData={tenderData}
            evaluations={evaluations}
            onContinue={() => setActiveView('bidders')}
          />
        )}

        {activeView === 'bidders' && hasTender && (
          <BidderManagement
            tenderId={tenderData.tender_id}
            criteria={tenderData.criteria}
            bidders={bidders}
            setBidders={setBidders}
            onEvaluationComplete={(evals, cartels) => {
              setEvaluations(evals);
              if (cartels) setCartAlerts(cartels);
              setActiveView('results');
            }}
          />
        )}

        {activeView === 'results' && hasResults && (
          <ResultsDashboard
            tenderId={tenderData.tender_id}
            tenderData={tenderData}
            criteria={tenderData.criteria}
            evaluations={evaluations}
            setEvaluations={setEvaluations}
            cartelAlerts={cartelAlerts}
            dispatchLog={dispatchLog}
            setDispatchLog={setDispatchLog}
          />
        )}

        {activeView === 'boundary' && <BoundaryPage />}
        {activeView === 'validation' && <ValidationPage />}
        {activeView === 'roadmap' && <IssuerRoadmapPage />}

        {activeView !== 'dashboard' && !hasTender && !['boundary', 'validation', 'roadmap', 'sources', 'bundle'].includes(activeView) && (
          <EmptyState
            title="Start with a tender bundle"
            body="Upload a tender workspace first, then TenderSight can unlock briefing, evaluation, and publish views."
            actionLabel="Open Bundle Intake"
            onAction={() => setActiveView('bundle')}
          />
        )}

        {activeView === 'results' && !hasResults && (
          <EmptyState
            title="No evaluation results yet"
            body="Run bidder evaluation first. Once results exist, this page becomes the publication and clarification workspace."
            actionLabel="Open Bidder Evaluation"
            onAction={() => setActiveView('bidders')}
          />
        )}
      </main>
    </div>
  );
}

function NavSection({ title, items, activeView, setActiveView, disableRule = () => false }) {
  return (
    <div>
      <p className="px-3 text-xs font-bold uppercase tracking-[0.28em] text-slate-400 mb-3">{title}</p>
      <div className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          const disabled = disableRule(item.id);
          const active = activeView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => !disabled && setActiveView(item.id)}
              disabled={disabled}
              className={`w-full flex items-center gap-3 px-3 py-3 rounded-2xl text-left transition-all ${
                active
                  ? 'bg-indigo-50 text-indigo-700 shadow-sm'
                  : disabled
                    ? 'text-slate-300 cursor-not-allowed'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <Icon size={18} />
              <span className={`text-sm ${active ? 'font-bold' : 'font-semibold'}`}>{item.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function TopRibbon({ tenderData, evaluations, dispatchLog }) {
  return (
    <div className="mb-6 rounded-[1.5rem] border border-white/80 bg-white/70 backdrop-blur-xl px-6 py-4 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.28em] text-slate-400">
            <Workflow size={14} />
            Workspace Status
          </div>
          <div className="mt-2 text-sm text-slate-600">
            {tenderData
              ? `${tenderData.tender_id} · ${tenderData.bundle_documents?.length || 1} source file(s) · ${tenderData.criteria?.length || 0} criteria`
              : 'No active tender bundle yet'}
          </div>
        </div>
        <div className="flex flex-wrap gap-3 text-sm">
          <RibbonPill icon={FileStack} label="Bundle" value={tenderData ? 'Loaded' : 'Pending'} />
          <RibbonPill icon={BookOpenCheck} label="Evaluations" value={evaluations ? Object.keys(evaluations).length : 0} />
          <RibbonPill icon={Send} label="Dispatches" value={dispatchLog.length} />
          <RibbonPill icon={Sparkles} label="Mode" value="Ideathon Prototype" />
        </div>
      </div>
    </div>
  );
}

function RibbonPill({ icon: Icon, label, value }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full bg-slate-50 border border-slate-200 px-4 py-2 text-slate-700">
      <Icon size={14} />
      <span className="font-semibold">{label}</span>
      <span className="text-slate-400">·</span>
      <span className="font-bold">{value}</span>
    </div>
  );
}

function EmptyState({ title, body, actionLabel, onAction }) {
  return (
    <div className="max-w-4xl mx-auto mt-10">
      <div className="clean-card text-center !p-10">
        <div className="mx-auto w-16 h-16 rounded-3xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
          <Scale size={30} />
        </div>
        <h2 className="mt-5 text-3xl font-black text-slate-900">{title}</h2>
        <p className="mt-3 text-slate-600 max-w-2xl mx-auto">{body}</p>
        <button onClick={onAction} className="mt-6 btn-primary-wow px-6 py-3">
          {actionLabel}
        </button>
      </div>
    </div>
  );
}

export default App;
