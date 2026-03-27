import Link from "next/link";
import { ArrowLeft, MessageSquare, Download, Share2, Target, ShieldAlert, Cpu } from "lucide-react";

export default function ReportDetail() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-8 animate-in fade-in duration-700 h-[calc(100vh-8rem)]">
      
      {/* Report Markdown Section */}
      <div className="bg-neutral-950 border border-neutral-800/50 rounded-lg p-8 overflow-y-auto">
        <Link href="/reports" className="flex items-center gap-2 text-neutral-500 hover:text-neutral-300 text-sm w-fit transition-colors mb-8 font-mono tracking-widest uppercase">
          <ArrowLeft size={16} /> Report Archive
        </Link>
        
        <div className="flex justify-between items-start mb-10 pb-6 border-b border-neutral-800/80">
          <div>
            <h1 className="text-3xl font-light tracking-tight text-white leading-tight">IRN: Nuclear Program Escalation Drivers</h1>
            <div className="flex gap-4 mt-6 uppercase tracking-widest text-[10px] font-mono font-bold">
               <span className="text-blue-500 bg-blue-500/10 px-2 py-1 rounded">OSINT Generation</span>
               <span className="text-neutral-400 bg-neutral-800 px-2 py-1 rounded">Clearance: Institutional</span>
               <span className="text-amber-500 bg-amber-500/10 px-2 py-1 rounded">High Confidence</span>
            </div>
          </div>
          <div className="flex gap-2">
            <button className="p-2 bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-white rounded transition-colors">
              <Download size={16} />
            </button>
            <button className="p-2 bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-white rounded transition-colors">
              <Share2 size={16} />
            </button>
          </div>
        </div>

        {/* Structured Synthesis Base */}
        <article className="prose prose-invert prose-neutral max-w-none">
          <h3 className="text-blue-500 font-mono tracking-widest text-sm uppercase">Executive Summary</h3>
          <p className="text-neutral-300 font-light leading-relaxed">
            Derived intelligence indices indicate a highly probable acceleration in enrichment thresholds. 
            Cross-referenced satellite metadata coupled with public sentiment divergence amongst internal hardliner nodes points to a strategic window of opportunity framing late Q3 2026.
          </p>
          
          <h3 className="text-blue-500 font-mono tracking-widest text-sm uppercase mt-8">Key Indicators</h3>
          <ul className="list-disc pl-5 space-y-2 text-neutral-400 font-light">
            <li><strong className="text-white">Economic Strain:</strong> 14% drop in non-oil exports.</li>
            <li><strong className="text-white">Military Deployments:</strong> Subterranean fortified movements tracked via commercial SAR arrays.</li>
            <li><strong className="text-white">Diplomatic Silence:</strong> Breakdown in informal back-channel negotiations.</li>
          </ul>

          <h3 className="text-blue-500 font-mono tracking-widest text-sm uppercase mt-8">Alternative Scenario Generation</h3>
          <p className="text-neutral-300 font-light leading-relaxed">
            Under a scenario where immediate sanction relief is conditionally offered, risk thresholds drop by 42%. However, the dominant trajectory remains unaltered without structural leadership shifts.
          </p>
        </article>
      </div>

      {/* Restricted Interface Chatbot (RAG) */}
      <div className="bg-neutral-900 border border-neutral-800/80 rounded-lg flex flex-col overflow-hidden relative shadow-2xl">
         
         <div className="bg-blue-950/20 border-b border-blue-900/40 p-4 flex items-center justify-between">
           <div className="flex items-center gap-3">
             <div className="w-8 h-8 rounded bg-blue-600/10 border border-blue-500/30 flex items-center justify-center text-blue-500">
               <Cpu size={16} />
             </div>
             <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-widest">Scenario Agent</h3>
                <p className="text-[10px] text-blue-400 font-mono uppercase tracking-widest">Locked to Report Context</p>
             </div>
           </div>
           <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse ring-2 ring-blue-500/20" />
         </div>
         
         {/* Chat Feed */}
         <div className="flex-1 p-4 overflow-y-auto space-y-6">
            <div className="flex gap-4">
              <div className="w-6 h-6 rounded-full bg-blue-600/20 flex-shrink-0" />
              <div>
                <p className="text-sm text-neutral-300 bg-neutral-800/50 border border-neutral-800 p-3 rounded-lg rounded-tl-none font-light">
                  I am explicitly constrained to this intelligence brief. I cannot access broader knowledge. What variable would you like me to simulate against these findings?
                </p>
              </div>
            </div>
         </div>
         
         {/* Chat Form */}
         <div className="p-4 border-t border-neutral-800 bg-neutral-950">
            <form className="relative">
              <input 
                type="text" 
                placeholder="Extract drivers, or simulate a 'what-if' node..." 
                className="w-full bg-neutral-900 border border-neutral-700 rounded p-3 pr-10 text-sm text-white placeholder-neutral-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
              />
              <button className="absolute right-3 top-3 text-neutral-500 hover:text-blue-500 transition-colors">
                <MessageSquare size={16} />
              </button>
            </form>
         </div>
      </div>
    </div>
  );
}
