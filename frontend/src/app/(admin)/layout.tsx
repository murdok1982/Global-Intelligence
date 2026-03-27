import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Admin Command | Restricted',
  robots: {
    index: false,
    follow: false,
    nocache: true,
  },
};

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-black text-neutral-300 font-mono">
      {/* Admin specific strict aesthetic */}
      <div className="border-b border-red-900/40 p-3 bg-red-950/20 text-red-500 text-xs font-bold uppercase tracking-widest text-center flex items-center justify-center gap-4">
        <span className="animate-pulse">●</span>
        RESTRICTED COMMAND CENTER - AUTHORIZED PERSONNEL ONLY
        <span className="animate-pulse">●</span>
      </div>
      <div className="p-8 max-w-7xl mx-auto">
        {children}
      </div>
    </div>
  );
}
