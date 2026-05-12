import { useState } from 'react';
import { Scale, Shield, Zap, BarChart3, FileCheck, Lock, ArrowRight, Eye, EyeOff, AlertTriangle } from 'lucide-react';

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const ADMIN_USERNAME = 'admin';
  const ADMIN_PASSWORD = 'tendersight2026';

  const handleLogin = (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    setTimeout(() => {
      if (username === ADMIN_USERNAME && password === ADMIN_PASSWORD) {
        onLogin(true);
      } else {
        setError('Invalid credentials.');
        setLoading(false);
      }
    }, 800);
  };

  return (
    <div className="h-screen flex flex-col lg:flex-row overflow-hidden">

      {/* ══════════ Left: Product Showcase ══════════ */}
      <div className="flex-1 relative flex flex-col justify-between px-10 sm:px-14 py-8 bg-slate-950">

        {/* Gradient accent */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_rgba(79,70,229,0.12)_0%,_transparent_50%),radial-gradient(ellipse_at_bottom_right,_rgba(139,92,246,0.08)_0%,_transparent_50%)]" />

        {/* ── Top: Brand ── */}
        <div className="relative z-10">
          <div className="flex items-center gap-2.5 mb-6">
            <div className="p-2 bg-indigo-500/15 rounded-lg border border-indigo-500/25">
              <Scale size={22} className="text-indigo-400" />
            </div>
            <span className="text-xl font-extrabold bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
              TenderSight
            </span>
            <span className="text-[9px] font-bold text-indigo-400/60 border border-indigo-500/20 px-1.5 py-0.5 rounded-full">v2.0</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-white leading-[1.15] mb-3">
            Smarter Tender Evaluation
            <br />
            <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-purple-400 bg-clip-text text-transparent">for Government Procurement</span>
          </h1>

          <p className="text-slate-400 text-sm leading-relaxed max-w-lg">
            Automate eligibility verification, detect fraud rings, and generate audit-ready reports — powered by sovereign, on-premise Large Language Models.
          </p>
        </div>

        {/* ── Middle: Features (compact horizontal) ── */}
        <div className="relative z-10 flex gap-3 my-6">

          <div className="flex-1 p-3.5 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-indigo-500/30 transition-colors">
            <FileCheck size={18} className="text-indigo-400 mb-2" />
            <h3 className="text-xs font-bold text-white mb-1">Smart Extraction</h3>
            <p className="text-[11px] text-slate-500 leading-snug">Auto-extract eligibility criteria from complex tender PDFs</p>
          </div>

          <div className="flex-1 p-3.5 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-emerald-500/30 transition-colors">
            <BarChart3 size={18} className="text-emerald-400 mb-2" />
            <h3 className="text-xs font-bold text-white mb-1">AI Evaluation</h3>
            <p className="text-[11px] text-slate-500 leading-snug">Evidence-backed bidder scoring with confidence levels</p>
          </div>

          <div className="flex-1 p-3.5 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-red-500/20 transition-colors">
            <AlertTriangle size={18} className="text-red-400 mb-2" />
            <h3 className="text-xs font-bold text-white mb-1">Fraud Detection</h3>
            <p className="text-[11px] text-slate-500 leading-snug">Graph-based cartel & shell company identification</p>
          </div>

          <div className="flex-1 p-3.5 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-amber-500/30 transition-colors">
            <Zap size={18} className="text-amber-400 mb-2" />
            <h3 className="text-xs font-bold text-white mb-1">Instant Reports</h3>
            <p className="text-[11px] text-slate-500 leading-snug">Audit-ready PDF generation with anomaly analysis</p>
          </div>

        </div>

        {/* ── Bottom: Stats ── */}
        <div className="relative z-10">
          <div className="flex items-center gap-8 mb-4">
            <div>
              <div className="text-xl font-extrabold text-white">128K</div>
              <div className="text-[9px] text-slate-600 font-bold uppercase tracking-wider">Context Window</div>
            </div>
            <div className="w-px h-7 bg-slate-800" />
            <div>
              <div className="text-xl font-extrabold text-white">70B</div>
              <div className="text-[9px] text-slate-600 font-bold uppercase tracking-wider">LLM Parameters</div>
            </div>
            <div className="w-px h-7 bg-slate-800" />
            <div>
              <div className="text-xl font-extrabold text-white">12+</div>
              <div className="text-[9px] text-slate-600 font-bold uppercase tracking-wider">Indian Languages</div>
            </div>
            <div className="w-px h-7 bg-slate-800" />
            <div>
              <div className="text-xl font-extrabold text-white">3-Pass</div>
              <div className="text-[9px] text-slate-600 font-bold uppercase tracking-wider">Eval Protocol</div>
            </div>
          </div>

          <div className="flex items-center gap-5 text-[10px] text-slate-600 font-medium">
            <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-green-500" /> On-Premise LLM</span>
            <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-green-500" /> Data Sovereign</span>
            <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-green-500" /> Zero Cloud Dependency</span>
          </div>
        </div>
      </div>

      {/* ══════════ Right: Login ══════════ */}
      <div className="w-full lg:w-[460px] flex flex-col items-center justify-center p-8 sm:p-12 bg-slate-900 border-l border-slate-800/60 relative overflow-hidden">

        {/* Decorative gradient ring */}
        <div className="absolute -top-32 -right-32 w-64 h-64 bg-indigo-600/5 rounded-full blur-[60px]" />
        <div className="absolute -bottom-20 -left-20 w-48 h-48 bg-violet-600/5 rounded-full blur-[50px]" />

        <div className="w-full max-w-sm relative z-10">

          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex p-3.5 bg-gradient-to-br from-indigo-500/15 to-violet-500/10 rounded-2xl border border-indigo-500/20 mb-5 shadow-lg shadow-indigo-500/5">
              <Lock size={26} className="text-indigo-400" />
            </div>
            <h2 className="text-2xl font-extrabold text-white mb-1">Welcome Back</h2>
            <p className="text-sm text-slate-500">Sign in to access the evaluation dashboard</p>
          </div>

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="block text-xs font-bold text-slate-400 mb-2">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-3 bg-slate-800/60 border border-slate-700/60 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/40 focus:bg-slate-800 transition-all text-sm"
                placeholder="Enter your username"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 mb-2">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-800/60 border border-slate-700/60 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/40 focus:bg-slate-800 transition-all pr-12 text-sm"
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-300 transition-colors p-1"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <p className="text-xs text-red-400 font-medium bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-2.5">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl font-bold text-sm transition-all duration-200 flex items-center justify-center gap-2 shadow-xl shadow-indigo-500/20 disabled:opacity-50 active:scale-[0.98]"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>Access Dashboard <ArrowRight size={16} /></>
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="mt-8 pt-6 border-t border-slate-800/60 text-center space-y-2">
            <div className="flex items-center justify-center gap-2 text-[11px] text-slate-600">
              <Shield size={12} className="text-slate-600" />
              <span>Unauthorized access attempts are logged and monitored</span>
            </div>
            <p className="text-[10px] text-slate-700">
              TenderSight v2.0 — Built for CRPF Procurement Division
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
