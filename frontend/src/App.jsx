import { useState } from 'react';
import { Scale, RotateCcw, AlertTriangle, LogOut } from 'lucide-react';
import LoginPage from './components/LoginPage';
import TenderUpload from './components/TenderUpload';
import BidderManagement from './components/BidderManagement';
import ResultsDashboard from './components/ResultsDashboard';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [step, setStep] = useState(1);
  const [tenderData, setTenderData] = useState(null);
  const [bidders, setBidders] = useState([]);
  const [evaluations, setEvaluations] = useState(null);
  const [cartelAlerts, setCartAlerts] = useState([]);

  const resetAll = () => {
    setStep(1);
    setTenderData(null);
    setBidders([]);
    setEvaluations(null);
    setCartAlerts([]);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    resetAll();
  };

  const handleTenderProcessed = (data) => {
    setTenderData(data);
    setStep(2);
  };

  const handleEvaluationComplete = (results) => {
    setEvaluations(results);
    setStep(3);
  };

  if (!isAuthenticated) {
    return <LoginPage onLogin={() => setIsAuthenticated(true)} />;
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-background">
      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-card border-r border-border md:h-screen sticky top-0 flex flex-col">
        <div className="p-6">
          <div className="flex items-center gap-2 text-2xl font-extrabold mb-2">
            <Scale className="text-indigo-600" size={28} />
            <span className="text-gradient-wow">TenderSight</span>
          </div>
          <p className="text-xs text-slate-500 font-medium leading-relaxed">
            AI-Powered Tender Evaluation for Government Procurement
          </p>
        </div>

        {/* Configuration */}
        <div className="px-6 py-4 border-t border-border text-sm text-slate-500">
          One Stop Tender Management Platform.
        </div>

        {/* Progress Tracker */}
        <div className="flex-1 px-6 py-6 border-t border-border">
          <div className="space-y-6">
            <div className={`flex items-center gap-3 ${step >= 1 ? 'text-blue-600 font-bold' : 'text-slate-400 font-medium'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${step > 1 ? 'bg-blue-600 text-white' : step === 1 ? 'bg-blue-100' : 'bg-slate-100'}`}>
                {step > 1 ? '✓' : '1'}
              </div>
              <span>📄 Tender</span>
            </div>

            <div className={`w-0.5 h-6 bg-slate-200 ml-4 -my-4 ${step > 1 ? 'bg-blue-200' : ''}`}></div>

            <div className={`flex items-center gap-3 ${step >= 2 ? 'text-blue-600 font-bold' : 'text-slate-400 font-medium'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${step > 2 ? 'bg-blue-600 text-white' : step === 2 ? 'bg-blue-100' : 'bg-slate-100'}`}>
                {step > 2 ? '✓' : '2'}
              </div>
              <span>📁 Bidders</span>
            </div>

            <div className={`w-0.5 h-6 bg-slate-200 ml-4 -my-4 ${step > 2 ? 'bg-blue-200' : ''}`}></div>

            <div className={`flex items-center gap-3 ${step >= 3 ? 'text-blue-600 font-bold' : 'text-slate-400 font-medium'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${step === 3 ? 'bg-blue-100 text-blue-600' : 'bg-slate-100'}`}>
                3
              </div>
              <span>⚖️ Results</span>
            </div>
          </div>
        </div>

        {/* Bottom Actions */}
        <div className="p-4 border-t border-border space-y-2">
          <button
            onClick={resetAll}
            className="w-full py-2 px-4 flex items-center justify-center gap-2 text-sm font-semibold text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <RotateCcw size={16} /> Reset Pipeline
          </button>
          <button
            onClick={handleLogout}
            className="w-full py-2 px-4 flex items-center justify-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <LogOut size={16} /> Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-6 md:p-10 overflow-y-auto h-screen">

        {step === 1 && (
          <TenderUpload
            onTenderProcessed={handleTenderProcessed}
          />
        )}

        {step === 2 && tenderData && (
          <BidderManagement
            tenderId={tenderData.tender_id}
            criteria={tenderData.criteria}
            bidders={bidders}
            setBidders={setBidders}
            onEvaluationComplete={(evals, cartels) => {
              setEvaluations(evals);
              if (cartels) setCartAlerts(cartels);
              setStep(3);
            }}
          />
        )}

        {step === 3 && tenderData && evaluations && (
          <ResultsDashboard
            tenderId={tenderData.tender_id}
            criteria={tenderData.criteria}
            evaluations={evaluations}
            setEvaluations={setEvaluations}
            cartelAlerts={cartelAlerts}
          />
        )}
      </main>
    </div>
  );
}

export default App;
