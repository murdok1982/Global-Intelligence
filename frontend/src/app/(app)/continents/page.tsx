import Link from "next/link";
import { Globe } from "lucide-react";

export default function ContinentsPage() {
  const continents = [
    { id: "namerica", name: "North America", nodes: 4230, risk: "Medium" },
    { id: "europe", name: "Europe", nodes: 8102, risk: "Medium-High" },
    { id: "asia", name: "Asia", nodes: 12400, risk: "High" },
    { id: "africa", name: "Africa", nodes: 3100, risk: "Critical" },
    { id: "latam", name: "Latin America", nodes: 2840, risk: "High" },
    { id: "meast", name: "Middle East", nodes: 5200, risk: "Critical" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div>
        <h1 className="text-3xl font-light tracking-tight text-white">Geopolitical Sectors</h1>
        <p className="text-neutral-500 mt-1 font-mono text-sm uppercase tracking-widest">Select macro-region to isolate intelligence nodes</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {continents.map((continent) => (
          <Link href={`/continents/${continent.id}`} key={continent.id} className="block group">
            <div className="bg-neutral-900/50 border border-neutral-800 rounded-lg p-6 hover:bg-neutral-800/80 hover:border-neutral-600 transition-all flex flex-col justify-between min-h-[200px] relative overflow-hidden">
              <div className="absolute -right-4 -bottom-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <Globe size={120} />
              </div>
              <div>
                <h3 className="text-2xl font-light text-neutral-200 group-hover:text-blue-400 transition-colors uppercase tracking-widest">{continent.name}</h3>
                <p className="text-neutral-500 font-mono text-xs mt-2">ID: {continent.id.toUpperCase()}_SECTOR</p>
              </div>
              <div className="mt-8 flex justify-between items-end">
                <div>
                  <p className="text-neutral-500 font-mono text-[10px] uppercase tracking-widest mb-1">Active Nodes</p>
                  <p className="text-xl font-medium text-neutral-300">{continent.nodes.toLocaleString()}</p>
                </div>
                <div className="text-right">
                  <p className="text-neutral-500 font-mono text-[10px] uppercase tracking-widest mb-1">Threat Level</p>
                  <p className={`text-sm font-bold ${continent.risk.includes('Critical') ? 'text-red-500' : continent.risk.includes('High') ? 'text-amber-500' : 'text-blue-500'}`}>
                    {continent.risk.toUpperCase()}
                  </p>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
