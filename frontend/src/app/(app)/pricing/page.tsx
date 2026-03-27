import { Check, ShieldAlert } from "lucide-react";

export default function PricingPage() {
  return (
    <div className="max-w-6xl mx-auto py-12 animate-in fade-in duration-700">
      <div className="text-center mb-16">
        <h1 className="text-4xl font-light tracking-widest text-white uppercase">Operational Clearance</h1>
        <p className="text-neutral-500 mt-4 font-mono text-sm uppercase tracking-widest max-w-2xl mx-auto">
          Secure your access to our algorithmic intelligence lake. Unfiltered OSINT synthesis for individuals and state-grade actors.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
        
        {/* Individual Plan */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-8 relative flex flex-col justify-between">
          <div>
            <h3 className="text-2xl font-light text-white mb-2">Analyst Tier</h3>
            <div className="flex items-baseline gap-2 mb-6">
              <span className="text-4xl font-bold text-white">€100</span>
              <span className="text-neutral-500 font-mono text-xs uppercase">/ month</span>
            </div>
            <p className="text-neutral-400 text-sm font-light mb-8">
              Targeted for independent researchers and intelligence analysts requiring structured daily ingestion.
            </p>
            <ul className="space-y-4 mb-8">
              <li className="flex items-start gap-3 text-neutral-300 text-sm">
                 <Check size={16} className="text-blue-500 mt-0.5" /> Access to 1 Custom Daily Report
              </li>
              <li className="flex items-start gap-3 text-neutral-300 text-sm">
                 <Check size={16} className="text-blue-500 mt-0.5" /> Restricted Chatbot Interaction (RAG constraints)
              </li>
              <li className="flex items-start gap-3 text-neutral-300 text-sm">
                 <Check size={16} className="text-blue-500 mt-0.5" /> Continent/Country Dashboard Access
              </li>
            </ul>
          </div>
          <button className="w-full py-4 rounded bg-neutral-800 hover:bg-neutral-700 text-white font-mono text-sm uppercase tracking-widest transition-colors font-bold tracking-widest border border-neutral-700">
            Subscribe Now
          </button>
        </div>

        {/* Institutional Plan */}
        <div className="bg-neutral-950 border border-blue-500/30 rounded-xl p-8 relative shadow-2xl flex flex-col justify-between overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-600 to-indigo-600" />
          
          <div>
             <div className="flex justify-between items-start mb-2">
                <h3 className="text-2xl font-light text-white">Custom Intelligence Engagement</h3>
                <span className="bg-blue-600/20 text-blue-400 border border-blue-500/30 px-2 py-1 uppercase tracking-widest text-[10px] font-mono rounded">
                  Institutional
                </span>
             </div>
            <div className="flex items-baseline gap-2 mb-6">
              <span className="text-4xl font-bold text-white">€10,000</span>
              <span className="text-neutral-500 font-mono text-xs uppercase">/ month</span>
            </div>
            <p className="text-neutral-400 text-sm font-light mb-8">
              State-grade depth. Human-reviewed pipelines, extreme source traceability, and custom agent deployment for high-value targets.
            </p>
            <ul className="space-y-4 mb-8">
              <li className="flex items-start gap-3 text-white text-sm font-medium">
                 <Check size={16} className="text-blue-500 mt-0.5" /> Unlimited Recursive Agentic Scans
              </li>
              <li className="flex items-start gap-3 text-white text-sm font-medium">
                 <Check size={16} className="text-blue-500 mt-0.5" /> Dedicated Orchestrator Nodes
              </li>
              <li className="flex items-start gap-3 text-white text-sm font-medium">
                 <Check size={16} className="text-blue-500 mt-0.5" /> Human-in-the-Loop Validation Workflows
              </li>
              <li className="flex items-start gap-3 text-white text-sm font-medium">
                 <Check size={16} className="text-blue-500 mt-0.5" /> API Webhook Extensibility
              </li>
            </ul>
          </div>
          <button className="w-full py-4 rounded bg-blue-600 text-white font-mono text-sm uppercase tracking-widest hover:bg-blue-500 transition-colors shadow-[0_0_20px_rgba(37,99,235,0.3)] font-bold tracking-widest">
            Request Clearance
          </button>
        </div>

      </div>
    </div>
  );
}
