import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Acceso | Global Intelligence',
  robots: {
    index: false,
    follow: false,
    nocache: true,
  },
};

/**
 * Layout para rutas de autenticación.
 *
 * Pública por definición: NO monta `ClassificationBanner` ni
 * `ClassificationFooter`. El usuario aún no está autenticado y no debería
 * exponérsele información clasificada en este punto.
 */
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
