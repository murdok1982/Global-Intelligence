import { Sidebar } from '@/components/layout/sidebar';
import { Header } from '@/components/layout/header';

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-neutral-950 font-sans text-neutral-200 selection:bg-blue-900/50">
      {/* Skip to main content — visible on keyboard focus only */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-background focus:text-foreground focus:border focus:rounded"
      >
        Skip to main content
      </a>
      <Sidebar />
      <div className="md:pl-64 flex flex-col min-h-screen">
        <Header />
        <main id="main-content" className="flex-1 pt-16 mt-4 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full pb-12">
          {children}
        </main>
      </div>
    </div>
  );
}
