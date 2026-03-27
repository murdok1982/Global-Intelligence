import Link from 'next/link';
import { Globe, FileText, Database, Shield, Zap, Key } from 'lucide-react';

export function Sidebar() {
  return (
    <aside className="w-64 fixed left-0 top-0 bottom-0 bg-neutral-950 border-r border-neutral-800/50 flex flex-col items-center py-6 shadow-2xl z-40 hidden md:flex">
      {/* Brand */}
      <div className="w-full px-6 mb-12">
        <h2 className="text-xl font-bold tracking-widest text-neutral-200 uppercase">
          GL<span className="text-blue-500 font-light">INTEL</span>
        </h2>
      </div>

      {/* Navigation */}
      <nav className="flex-1 w-full px-4 space-y-2">
        <NavItem href="/dashboard" icon={<Globe size={18} />} label="Global Map" active />
        <NavItem href="/intelligence" icon={<Database size={18} />} label="Intelligence Lake" />
        <NavItem href="/reports" icon={<FileText size={18} />} label="Daily Synthesis" />
        <NavItem href="/scenarios" icon={<Zap size={18} />} label="Scenario Engine" />
        
        <div className="pt-6 pb-2 px-2">
          <p className="text-[10px] font-bold tracking-widest text-neutral-600 uppercase">Operations</p>
        </div>
        <NavItem href="/contribute" icon={<Shield size={18} />} label="Secure Intake" />
        <NavItem href="/admin" icon={<Key size={18} />} label="Command Center" />
      </nav>

      {/* User Status Bottom */}
      <div className="w-full px-6 mt-auto">
        <div className="bg-neutral-900 border border-neutral-800 rounded p-4 text-xs font-mono text-neutral-400">
          <p className="text-neutral-500 mb-1 font-sans font-bold">CLEARANCE</p>
          <p className="text-blue-500 tracking-wider">LEVEL: INSTITUTIONAL</p>
          <div className="w-full bg-neutral-800 h-1 mt-3 rounded-full overflow-hidden">
             <div className="bg-blue-600 w-full h-full animate-pulse" />
          </div>
        </div>
      </div>
    </aside>
  );
}

function NavItem({ href, icon, label, active = false }: { href: string; icon: React.ReactNode; label: string; active?: boolean }) {
  return (
    <Link 
      href={href} 
      className={`flex items-center gap-3 px-3 py-2.5 rounded text-sm transition-all group ${
        active 
          ? 'bg-blue-600/10 text-blue-400 border border-blue-600/20' 
          : 'text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200'
      }`}
    >
      <span className={active ? "text-blue-500" : "text-neutral-500 group-hover:text-neutral-300 transition-colors"}>
        {icon}
      </span>
      <span className="font-medium tracking-wide">{label}</span>
    </Link>
  );
}
