import { Search, Bell, Monitor } from "lucide-react";

export function Header() {
  return (
    <header className="h-16 fixed top-0 right-0 left-0 md:left-64 bg-background/80 backdrop-blur-md border-b border-neutral-800/50 z-30 flex items-center justify-between px-6">
      
      {/* Search Bar */}
      <div className="flex-1 max-w-md relative hidden sm:block">
        <label htmlFor="search" className="sr-only">Query Database</label>
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search size={16} className="text-neutral-500" />
        </div>
        <input 
          type="text" 
          id="search"
          placeholder="Query intelligence entities, nodes, countries..." 
          className="block w-full pl-10 pr-3 py-2 border border-neutral-800 rounded bg-neutral-900/50 text-neutral-300 sm:text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500 focus:outline-none transition-all placeholder-neutral-600"
        />
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-4 ml-auto">
        <button className="text-neutral-500 hover:text-neutral-300 transition-colors relative">
          <Monitor size={18} />
          <span className="absolute top-0 right-0 block h-2.5 w-2.5 rounded-full bg-blue-500 ring-2 ring-background"></span>
        </button>
        <button className="text-neutral-500 hover:text-neutral-300 transition-colors">
          <Bell size={18} />
        </button>
        
        {/* Profile */}
        <div className="h-8 w-8 rounded-full bg-neutral-800 border border-neutral-700 flex items-center justify-center text-xs font-mono text-neutral-300 cursor-pointer overflow-hidden ring-1 ring-blue-500/20">
          OP
        </div>
      </div>
      
    </header>
  );
}
