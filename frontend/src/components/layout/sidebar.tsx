'use client';

import Link from 'next/link';
import { Globe, FileText, Database, Shield, Zap, Key } from 'lucide-react';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import {
  CLASSIFICATION_COLOR,
  CLASSIFICATION_SHORT,
  ClassificationLevel,
} from '@/lib/classification';

// Mapa de barras de progreso por nivel — clases tailwind explícitas para JIT.
const PROGRESS_BAR: Record<ClassificationLevel, string> = {
  [ClassificationLevel.PUBLIC]: 'bg-emerald-500',
  [ClassificationLevel.RESTRICTED]: 'bg-yellow-500',
  [ClassificationLevel.CONFIDENTIAL]: 'bg-orange-500',
  [ClassificationLevel.SECRET]: 'bg-red-500',
};

export function Sidebar() {
  const { clearance, isAuthenticated, isLoading } = useCurrentUser();
  const palette = CLASSIFICATION_COLOR[clearance];

  return (
    <aside
      className="w-64 fixed left-0 bottom-0 bg-neutral-950 border-r border-neutral-800/50 flex flex-col items-center py-6 shadow-2xl z-40 hidden md:flex"
      style={{ top: 'var(--classification-banner-h, 0px)' }}
    >
      {/* Brand */}
      <div className="w-full px-6 mb-12">
        <h2 className="text-xl font-bold tracking-widest text-neutral-200 uppercase">
          GL<span className="text-blue-500 font-light">INTEL</span>
        </h2>
      </div>

      {/* Navigation */}
      <nav className="flex-1 w-full px-4 space-y-2" aria-label="Navegación principal">
        <NavItem href="/dashboard" icon={<Globe size={18} />} label="Mapa Global" active />
        <NavItem href="/intelligence" icon={<Database size={18} />} label="Repositorio Intel" />
        <NavItem href="/reports" icon={<FileText size={18} />} label="Síntesis Diaria" />
        <NavItem href="/scenarios" icon={<Zap size={18} />} label="Motor de Escenarios" />

        <div className="pt-6 pb-2 px-2">
          <p className="text-[10px] font-bold tracking-widest text-neutral-600 uppercase">Operaciones</p>
        </div>
        <NavItem href="/contribute" icon={<Shield size={18} />} label="Intake Seguro" />
        <NavItem href="/admin" icon={<Key size={18} />} label="Centro de Mando" />
      </nav>

      {/* User Status Bottom */}
      <div className="w-full px-6 mt-auto">
        <div
          className={`border rounded p-4 text-xs font-mono ${palette.bg} ${palette.border}`}
        >
          <p className={`mb-1 font-sans font-bold tracking-widest ${palette.text} opacity-80`}>
            CLEARANCE
          </p>
          {isLoading ? (
            <p className="text-neutral-500 tracking-wider">Cargando…</p>
          ) : isAuthenticated ? (
            <p className={`${palette.text} tracking-wider font-bold`}>
              NIVEL: {CLASSIFICATION_SHORT[clearance]}
            </p>
          ) : (
            <p className="text-neutral-500 tracking-wider">No autenticado</p>
          )}
          <div className="w-full bg-neutral-800 h-1 mt-3 rounded-full overflow-hidden">
            <div
              className={`h-full ${PROGRESS_BAR[clearance]}`}
              style={{
                width: `${((clearance + 1) / 4) * 100}%`,
              }}
              aria-hidden="true"
            />
          </div>
        </div>
      </div>
    </aside>
  );
}

function NavItem({
  href,
  icon,
  label,
  active = false,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
  active?: boolean;
}) {
  return (
    <Link
      href={href}
      role="menuitem"
      aria-current={active ? 'page' : undefined}
      className={`flex items-center gap-3 px-3 py-2.5 rounded text-sm transition-all group ${
        active
          ? 'bg-blue-600/10 text-blue-400 border border-blue-600/20'
          : 'text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200'
      }`}
    >
      <span
        className={
          active
            ? 'text-blue-500'
            : 'text-neutral-500 group-hover:text-neutral-300 transition-colors'
        }
        aria-hidden="true"
      >
        {icon}
      </span>
      <span className="font-medium tracking-wide">{label}</span>
    </Link>
  );
}

