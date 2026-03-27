import { Activity, ShieldAlert, Cpu } from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      
      {/* Title & Stats */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-light tracking-tight text-white">Global Overview</h1>
          <p className="text-neutral-500 mt-1 font-mono text-sm uppercase tracking-widest">Real-time intelligence nodes</p>
        </div>
        
        <div className="flex gap-4 font-mono text-xs">
           <div className="bg-neutral-900 border border-neutral-800 rounded px-4 py-2 flex items-center gap-3">
              <Activity size={14} className="text-blue-500" />
              <span className="text-neutral-400">ACTIVE NODES:</span>
              <span className="text-white font-bold">14,392</span>
           </div>
           <div className="bg-neutral-900 border border-neutral-800 rounded px-4 py-2 flex items-center gap-3">
              <ShieldAlert size={14} className="text-red-500 animate-pulse" />
              <span className="text-neutral-400">HIGH ALERTS:</span>
              <span className="text-white font-bold">12</span>
           </div>
        </div>
      </div>

      {/* Main Map Area */}
      <div className="w-full aspect-[21/9] bg-neutral-900/50 border border-neutral-800 rounded-lg relative overflow-hidden flex items-center justify-center p-6 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-950/20 via-neutral-950/20 to-transparent">
        
        <div className="absolute inset-0 bg-[url('https://upload.wikimedia.org/wikipedia/commons/8/80/World_map_-_low_resolution.svg')] bg-center bg-no-repeat bg-contain opacity-20 filter invert sepia hue-rotate-[200deg] saturate-[300%]" style={{ maskImage: 'linear-gradient(to bottom, black 50%, transparent 100%)' }}></div>
        
        {/* Placeholder Nodes */}
        <div className="absolute top-[40%] left-[45%] h-3 w-3 rounded-full bg-blue-500 ring-4 ring-blue-500/20 animate-pulse cursor-pointer"></div>
        <div className="absolute top-[35%] left-[20%] h-2 w-2 rounded-full bg-amber-500 ring-2 ring-amber-500/20 animate-pulse cursor-pointer"></div>
        <div className="absolute top-[50%] left-[65%] h-2 w-2 rounded-full bg-red-500 ring-4 ring-red-500/20 animate-[pulse_1s_ease-in-out_infinite] cursor-pointer"></div>

        <div className="absolute bottom-4 left-4 font-mono text-[10px] text-neutral-600 tracking-widest uppercase">
          [System] Awaiting geospatial vector tiles...
        </div>
      </div>

      {/* Continents Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {['North America', 'Europe', 'Asia', 'Middle East', 'Africa', 'LatAm'].map((region) => (
          <div key={region} className="bg-neutral-900 border border-neutral-800 rounded p-4 hover:bg-neutral-800 hover:border-neutral-700 transition-colors cursor-pointer group flex flex-col justify-between min-h-[120px]">
            <h3 className="text-sm font-semibold text-neutral-300 group-hover:text-blue-400 transition-colors">{region}</h3>
            <div className="flex justify-between items-end mt-4">
              <span className="text-3xl font-light text-neutral-600 group-hover:text-neutral-400 transition-colors">
                 {Math.floor(Math.random() * 90) + 10}
              </span>
              <Cpu size={14} className="text-neutral-700 group-hover:text-blue-500/50" />
            </div>
            <div className="w-full bg-neutral-950 h-1 mt-3 rounded-full overflow-hidden">
               <div className="bg-blue-600/50 h-full" style={{ width: `${Math.random() * 80 + 10}%` }}></div>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
}
