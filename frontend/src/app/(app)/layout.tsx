import { Sidebar } from '@/components/layout/sidebar';
import { Header } from '@/components/layout/header';

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-neutral-950 font-sans text-neutral-200 selection:bg-blue-900/50">
      <Sidebar />
      <div className="md:pl-64 flex flex-col min-h-screen">
        <Header />
        <main className="flex-1 pt-16 mt-4 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full pb-12">
          {children}
        </main>
      </div>
    </div>
  );
}
