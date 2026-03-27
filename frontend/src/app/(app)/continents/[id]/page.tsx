import Link from "next/link";
import { ArrowLeft, Target } from "lucide-react";

export default async function ContinentDetail({ params }: { params: { id: string } }) {
  const { id } = await params;
  
  // Mock subset for UI scaffolding
  const countries = [
    { iso: "irn", name: "Iran", events: 142, risk: "CRITICAL" },
    { iso: "chn", name: "China", events: 890, risk: "HIGH" },
    { iso: "rus", name: "Russia", events: 753, risk: "CRITICAL" },
    { iso: "ven", name: "Venezuela", events: 89, risk: "HIGH" },
    { iso: "yem", name: "Yemen", events: 211, risk: "CRITICAL" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <Link href="/continents" className="flex items-center gap-2 text-neutral-500 hover:text-neutral-300 text-sm w-fit transition-colors">
        <ArrowLeft size={16} /> Returns to Sectors
      </Link>
      
      <div>
        <h1 className="text-3xl font-light tracking-tight text-white uppercase">{id} Sector</h1>
        <p className="text-neutral-500 mt-1 font-mono text-sm uppercase tracking-widest">Isolated Geopolitical Context</p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        <div className="grid grid-cols-12 gap-4 px-4 py-2 font-mono text-[10px] text-neutral-500 uppercase tracking-widest border-b border-neutral-800">
          <div className="col-span-1">ISO</div>
          <div className="col-span-5">Entity</div>
          <div className="col-span-3">OSINT Events (24h)</div>
          <div className="col-span-3 text-right">Risk Vector</div>
        </div>

        {countries.map((country) => (
          <Link href={`/countries/${country.iso}`} key={country.iso} className="group">
            <div className="grid grid-cols-12 gap-4 px-4 py-4 bg-neutral-900/40 border border-neutral-800/50 rounded hover:bg-neutral-800 hover:border-neutral-600 transition-all items-center">
              <div className="col-span-1 font-mono text-xs text-neutral-500 group-hover:text-blue-500">{country.iso.toUpperCase()}</div>
              <div className="col-span-5 font-medium text-neutral-300 group-hover:text-white flex items-center gap-2">
                <Target size={14} className="text-neutral-700 group-hover:text-blue-500" />
                {country.name}
              </div>
              <div className="col-span-3 font-mono text-sm text-neutral-400">
                {country.events}
              </div>
              <div className={`col-span-3 text-right font-mono text-xs font-bold ${country.risk === 'CRITICAL' ? 'text-red-500' : 'text-amber-500'}`}>
                {country.risk}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
