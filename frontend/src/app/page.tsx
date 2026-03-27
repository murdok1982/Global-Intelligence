export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-background text-foreground bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-neutral-900 via-background to-background">
      <div className="z-10 max-w-5xl w-full items-center justify-center lg:flex flex-col text-center">
        <h1 className="text-4xl md:text-5xl font-light tracking-widest text-neutral-200">
          GLOBAL <strong className="font-bold text-white">INTELLIGENCE</strong>
        </h1>
        <div className="w-24 h-1 bg-blue-600/50 mt-8 mb-6 rounded-full blur-sm" />
      </div>
      
      <div className="mt-8 text-center max-w-2xl">
        <p className="text-neutral-400 text-lg leading-relaxed font-light">
          State-grade strategic foresight and actionable geopolitical analysis, synthesized through recursive generative agents tracking public signals safely.
        </p>
        
        <div className="mt-14 flex flex-col sm:flex-row gap-6 justify-center items-center">
          <a href="/dashboard" className="px-8 py-3 w-full sm:w-auto rounded bg-blue-600/10 text-blue-400 border border-blue-600/30 hover:bg-blue-600/20 hover:text-white transition-all font-semibold uppercase tracking-widest text-xs ring-1 ring-blue-500/20 focus:outline-none focus:ring-blue-500">
            Secure Access
          </a>
          <a href="/auth" className="px-8 py-3 w-full sm:w-auto rounded-none border-b border-neutral-700 hover:border-neutral-400 transition-all text-neutral-400 hover:text-white uppercase tracking-widest text-xs focus:outline-none">
            Institutional Login
          </a>
        </div>
      </div>
    </main>
  );
}
