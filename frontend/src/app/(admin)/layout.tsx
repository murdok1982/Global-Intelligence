import { Metadata } from 'next';
import { ClassificationBanner } from '@/components/security/ClassificationBanner';
import { ClassificationFooter } from '@/components/security/ClassificationFooter';
import { ClassificationLevel, TLP } from '@/lib/classification';

export const metadata: Metadata = {
  title: 'Centro de Mando | Restringido',
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
      {/* Banner obligatorio: CONFIDENCIAL + TLP:AMBER+STRICT */}
      <ClassificationBanner
        classification={ClassificationLevel.CONFIDENTIAL}
        tlp={TLP.AMBER_STRICT}
        documentLabel="Centro de Mando"
      />

      {/* Aviso de control de acceso */}
      <div
        role="alert"
        aria-live="assertive"
        className="border-b border-red-900/40 p-3 bg-red-950/20 text-red-500 text-xs font-bold uppercase tracking-widest text-center flex items-center justify-center gap-4"
      >
        <span aria-hidden="true" className="animate-pulse">●</span>
        Centro de Mando Restringido — Sólo Personal Autorizado
        <span aria-hidden="true" className="animate-pulse">●</span>
      </div>

      <div className="p-8 max-w-7xl mx-auto pb-16">{children}</div>

      <ClassificationFooter
        classification={ClassificationLevel.CONFIDENTIAL}
        tlp={TLP.AMBER_STRICT}
      />
    </div>
  );
}
