import Link from "next/link";
import { ArrowLeft, Briefcase, Landmark, Shield, Users, RadioTower, AlertTriangle } from "lucide-react";

export default async function CountryProfile({ params }: { params: { iso: string } }) {
  const { iso } = await params;
  
  const categories = [
    { id: "economic", label: "Economic", icon: <Briefcase size={16} />, items: 24, status: "stable" },
    { id: "political", label: "Political", icon: <Landmark size={16} />, items: 89, status: "volatile" },
    { id: "military", label: "Military", icon: <Shield size={16} />, items: 12, status: "alert" },
    { id: "social", label: "Social", icon: <Users size={16} />, items: 45, status: "stable" },
    { id: "security", label: "Security", icon: <RadioTower size={16} />, items: 156, status: "critical" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex justify-between items-start">
        <div>
          <Link href="/continents" className="flex items-center gap-2 text-neutral-500 hover:text-neutral-300 text-sm w-fit transition-colors mb-6">
            <ArrowLeft size={16} /> Returns to Map
          </Link>
          <div className="flex items-center gap-4">
            <h1 className="text-4xl font-light tracking-widest text-white uppercase">{iso} PROFILE</h1>
            <span className="px-3 py-1 bg-red-500/10 text-red-500 border border-red-500/20 text-xs font-mono font-bold tracking-widest rounded">
              CRITICAL THREAT
            </span>
          </div>
          <p className="text-neutral-500 mt-2 font-mono text-sm uppercase tracking-widest">Target Entity OSINT Synchronization</p>
        </div>
        
        <button className="px-6 py-3 bg-blue-600/10 text-blue-500 hover:bg-blue-600/20 hover:text-blue-400 border border-blue-600/30 rounded text-xs font-mono font-bold uppercase tracking-widest flex items-center gap-2 transition-colors">
          <AlertTriangle size={14} />
          Generate Daily Interactive Report
        </button>
      </div>

      {/* OSINT Categories Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {categories.map((cat) => (
          <div key={cat.id} className="bg-neutral-900 border border-neutral-800 rounded p-4 hover:border-neutral-600 cursor-pointer transition-colors group">
            <div className="flex justify-between items-start mb-6">
              <div className={`p-2 rounded ${
                cat.status === 'critical' ? 'bg-red-500/10 text-red-500' : 
                cat.status === 'alert' ? 'bg-amber-500/10 text-amber-500' : 
                cat.status === 'volatile' ? 'bg-orange-500/10 text-orange-500' :
                'bg-blue-500/10 text-blue-500'
              }`}>
                {cat.icon}
              </div>
              <span className="font-mono text-xl font-light text-neutral-400 group-hover:text-white transition-colors">
                {cat.items}
              </span>
            </div>
            <p className="font-mono text-xs uppercase tracking-widest text-neutral-500 mb-1">Sector</p>
            <h3 className="font-medium text-neutral-300 group-hover:text-blue-400">{cat.label}</h3>
          </div>
        ))}
      </div>

      {/* Intelligence Feed Placeholder */}
      <div className="mt-8 border border-neutral-800 bg-neutral-900/30 rounded-lg">
        <div className="border-b border-neutral-800 p-4 bg-neutral-900/50">
          <h3 className="font-mono text-xs tracking-widest text-neutral-400 uppercase">Live Intelligence Feed Array</h3>
        </div>
        <div className="p-8 flex flex-col items-center justify-center min-h-[400px] text-neural-500 opacity-50">
          <RadioTower size={48} className="mb-4 text-neutral-600" />
          <p className="font-mono text-sm uppercase tracking-widest text-neutral-500">Decrypting signals...</p>
        </div>
      </div>
    </div>
  );
}
