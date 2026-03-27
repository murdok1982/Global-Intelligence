import Link from "next/link";
import { FileText, Lock, Unlock } from "lucide-react";

export default function ReportsIndex() {
  const reports = [
    { id: "rep-001", title: "IRN: Nuclear Program Escalation Drivers", access: "authorized", date: "2026-03-27" },
    { id: "rep-002", title: "RUS: Military Logistics Disruptions", access: "authorized", date: "2026-03-26" },
    { id: "rep-003", title: "CHN: Paramilitary Naval Expansion", access: "locked", date: "2026-03-25" },
    { id: "rep-004", title: "VEN: Election Fraud Mitigation", access: "locked", date: "2026-03-24" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-700 max-w-5xl mx-auto">
      <div>
        <h1 className="text-3xl font-light tracking-tight text-white uppercase">Synthesized Reports</h1>
        <p className="text-neutral-500 mt-1 font-mono text-sm uppercase tracking-widest">Generative Intelligence Array</p>
      </div>

      <div className="flex flex-col gap-4">
        {reports.map((report) => (
          <Link href={report.access === 'authorized' ? `/reports/${report.id}` : '#'} key={report.id}>
            <div className={`p-6 border rounded-lg flex items-center justify-between transition-all ${
              report.access === 'authorized' 
                ? 'bg-neutral-900 border-neutral-800 hover:border-blue-500/50 hover:bg-neutral-800/80 cursor-pointer' 
                : 'bg-neutral-900/30 border-neutral-800/30 opacity-60 cursor-not-allowed'
            }`}>
              <div className="flex items-center gap-6">
                <div className={`p-3 rounded-full ${report.access === 'authorized' ? 'bg-blue-500/10 text-blue-500' : 'bg-neutral-800 text-neutral-600'}`}>
                  {report.access === 'authorized' ? <FileText size={20} /> : <Lock size={20} />}
                </div>
                <div>
                  <h3 className="text-lg font-medium text-neutral-200 tracking-wide">{report.title}</h3>
                  <p className="text-neutral-500 font-mono text-xs mt-2 uppercase tracking-widest">Published: {report.date}</p>
                </div>
              </div>
              
              <div className="hidden md:block">
                {report.access === 'authorized' ? (
                  <span className="px-3 py-1 bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 text-xs font-mono font-bold tracking-widest rounded flex items-center gap-2">
                    <Unlock size={12} /> CLEARED
                  </span>
                ) : (
                  <span className="px-3 py-1 bg-neutral-800 text-neutral-500 border border-neutral-700 text-xs font-mono font-bold tracking-widest rounded flex items-center gap-2">
                    <Lock size={12} /> RESTRICTED
                  </span>
                )}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
