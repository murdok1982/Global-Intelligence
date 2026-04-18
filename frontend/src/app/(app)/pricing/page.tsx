import { Check } from "lucide-react";

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

        {/* Analyst Plan */}
        <article
          role="article"
          aria-labelledby="plan-analyst-heading"
          className="bg-neutral-900 border border-neutral-800 rounded-xl p-8 relative flex flex-col justify-between"
        >
          <div>
            <h2 id="plan-analyst-heading" className="text-2xl font-light text-white mb-2">Analyst Tier</h2>
            <div className="flex items-baseline gap-2 mb-6">
              <span aria-label="100 euros per month">
                <span className="text-4xl font-bold text-white">€100</span>
                <span className="text-neutral-500 font-mono text-xs uppercase ml-2" aria-hidden="true">/ month</span>
              </span>
            </div>
            <p className="text-neutral-400 text-sm font-light mb-8">
              Targeted for independent researchers and intelligence analysts requiring structured daily ingestion.
            </p>
            <ul className="space-y-4 mb-8" aria-label="Analyst Tier features">
              <li className="flex items-start gap-3 text-neutral-300 text-sm">
                <Check size={16} className="text-blue-500 mt-0.5" aria-hidden="true" />
                Access to 1 Custom Daily Report
              </li>
              <li className="flex items-start gap-3 text-neutral-300 text-sm">
                <Check size={16} className="text-blue-500 mt-0.5" aria-hidden="true" />
                Restricted Chatbot Interaction (RAG constraints)
              </li>
              <li className="flex items-start gap-3 text-neutral-300 text-sm">
                <Check size={16} className="text-blue-500 mt-0.5" aria-hidden="true" />
                Continent/Country Dashboard Access
              </li>
            </ul>
          </div>
          <button
            className="w-full py-4 rounded bg-neutral-800 hover:bg-neutral-700 text-white font-mono text-sm uppercase tracking-widest transition-colors font-bold border border-neutral-700 focus-visible:outline-2 focus-visible:outline-blue-500"
            aria-label="Subscribe to Analyst Tier — €100 per month"
          >
            Subscribe to Analyst Tier
          </button>
        </article>

        {/* Institutional Plan */}
        <article
          role="article"
          aria-labelledby="plan-institutional-heading"
          className="bg-neutral-950 border border-blue-500/30 rounded-xl p-8 relative shadow-2xl flex flex-col justify-between overflow-hidden"
        >
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-600 to-indigo-600" aria-hidden="true" />

          <div>
            <div className="flex justify-between items-start mb-2">
              <h2 id="plan-institutional-heading" className="text-2xl font-light text-white">Custom Intelligence Engagement</h2>
              <span
                className="bg-blue-600/20 text-blue-400 border border-blue-500/30 px-2 py-1 uppercase tracking-widest text-[10px] font-mono rounded"
                aria-label="Institutional tier"
              >
                Institutional
              </span>
            </div>
            <div className="flex items-baseline gap-2 mb-6">
              <span aria-label="10,000 euros per month">
                <span className="text-4xl font-bold text-white">€10,000</span>
                <span className="text-neutral-500 font-mono text-xs uppercase ml-2" aria-hidden="true">/ month</span>
              </span>
            </div>
            <p className="text-neutral-400 text-sm font-light mb-8">
              State-grade depth. Human-reviewed pipelines, extreme source traceability, and custom agent deployment for high-value targets.
            </p>
            <ul className="space-y-4 mb-8" aria-label="Custom Intelligence Engagement features">
              <li className="flex items-start gap-3 text-white text-sm font-medium">
                <Check size={16} className="text-blue-500 mt-0.5" aria-hidden="true" />
                Unlimited Recursive Agentic Scans
              </li>
              <li className="flex items-start gap-3 text-white text-sm font-medium">
                <Check size={16} className="text-blue-500 mt-0.5" aria-hidden="true" />
                Dedicated Orchestrator Nodes
              </li>
              <li className="flex items-start gap-3 text-white text-sm font-medium">
                <Check size={16} className="text-blue-500 mt-0.5" aria-hidden="true" />
                Human-in-the-Loop Validation Workflows
              </li>
              <li className="flex items-start gap-3 text-white text-sm font-medium">
                <Check size={16} className="text-blue-500 mt-0.5" aria-hidden="true" />
                API Webhook Extensibility
              </li>
            </ul>
          </div>
          <button
            className="w-full py-4 rounded bg-blue-600 text-white font-mono text-sm uppercase tracking-widest hover:bg-blue-500 transition-colors shadow-[0_0_20px_rgba(37,99,235,0.3)] font-bold focus-visible:outline-2 focus-visible:outline-white"
            aria-label="Request clearance for Custom Intelligence Engagement — €10,000 per month"
          >
            Request Clearance
          </button>
        </article>

      </div>

      {/* Legal disclaimer */}
      <div className="max-w-4xl mx-auto mt-12 pt-8 border-t border-neutral-800">
        <p className="text-neutral-600 text-xs font-mono leading-relaxed text-center">
          All subscriptions are billed monthly. Cancellations take effect at the end of the current billing cycle — no partial refunds are issued.
          Institutional engagements are subject to a signed service agreement and a minimum 3-month commitment.
          Global Intelligence reserves the right to suspend access for violations of the acceptable use policy.
          Prices are listed excluding applicable taxes (VAT/IVA). By subscribing you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}
