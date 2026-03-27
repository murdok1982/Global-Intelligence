import { Shield, Activity, Users, FileWarning, Key } from "lucide-react";

export default function AdminDashboard() {
  return (
    <div className="space-y-8 animate-in fade-in">
      <div className="flex justify-between items-end border-b border-neutral-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-widest text-white uppercase">Internal Overseer</h1>
          <p className="text-neutral-500 mt-1 uppercase text-xs tracking-widest">Global Intelligence Governance & Audit</p>
        </div>
        <div className="bg-red-500/10 text-red-500 px-3 py-1 rounded border border-red-500/20 text-xs font-bold font-mono">
          E2E ENCRYPTION MATRICES: ACTIVE
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-neutral-900 border border-neutral-800 p-4">
           <p className="text-neutral-500 text-xs uppercase tracking-widest mb-2 flex items-center gap-2">
             <Activity size={12} /> OSINT Agent Status
           </p>
           <p className="text-2xl font-light text-emerald-500">OPERATIONAL</p>
        </div>
        <div className="bg-neutral-900 border border-neutral-800 p-4">
           <p className="text-neutral-500 text-xs uppercase tracking-widest mb-2 flex items-center gap-2">
             <Key size={12} /> OpenRouter APIs
           </p>
           <p className="text-2xl font-light text-emerald-500">CONNECTED</p>
        </div>
        <div className="bg-neutral-900 border border-neutral-800 p-4">
           <p className="text-neutral-500 text-xs uppercase tracking-widest mb-2 flex items-center gap-2">
             <Users size={12} /> Subscriptions (Active)
           </p>
           <p className="text-2xl font-light text-white">1,402</p>
        </div>
        <div className="bg-neutral-900 border border-neutral-800 p-4">
           <p className="text-neutral-500 text-xs uppercase tracking-widest mb-2 flex items-center gap-2">
             <FileWarning size={12} /> Pending Contributions
           </p>
           <p className="text-2xl font-light text-amber-500">23</p>
        </div>
      </div>

      <div className="bg-neutral-900 border border-neutral-800">
        <div className="border-b border-neutral-800 p-3 bg-neutral-950 flex justify-between">
           <h3 className="text-xs uppercase tracking-widest text-neutral-400">Contributor Intelligence Clearance Queue</h3>
        </div>
        <div className="p-4 space-y-2">
            <div className="flex justify-between p-3 border border-neutral-800 bg-black items-center">
              <div className="flex gap-4 text-sm font-mono text-neutral-400">
                 <span className="text-blue-500 font-bold">NAMERICA</span>
                 <span>Category: Economic</span>
                 <span className="text-neutral-600">ID: c_sub_001A</span>
              </div>
              <div className="flex gap-2">
                <button className="bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 px-3 py-1 text-xs hover:bg-emerald-500/20">APPROVE</button>
                <button className="bg-red-500/10 text-red-500 border border-red-500/30 px-3 py-1 text-xs hover:bg-red-500/20">DROP</button>
              </div>
            </div>
        </div>
      </div>
    </div>
  );
}
