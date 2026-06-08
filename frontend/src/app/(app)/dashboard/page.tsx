'use client';

import Link from 'next/link';
import dynamic from 'next/dynamic';
import { Activity, ShieldAlert, Cpu } from 'lucide-react';
import { useContinents } from '@/hooks/useContinents';
import { useAdminStats } from '@/hooks/useAdmin';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import { getTranslations } from '@/lib/i18n/translations';

const GeoIntelligenceMap = dynamic(
  () => import('@/components/map/GeoIntelligenceMap').then(mod => ({ default: mod.GeoIntelligenceMap })),
  { 
    ssr: false, 
    loading: () => (
      <div className="w-full h-full bg-neutral-900/50 border border-neutral-800 rounded-lg flex items-center justify-center">
        <div className="text-neutral-600 font-mono text-sm">Loading geospatial intelligence...</div>
      </div>
    )
  }
);

const riskColor: Record<string, string> = {
  Low: 'bg-emerald-600/50',
  Medium: 'bg-blue-600/50',
  High: 'bg-amber-500/50',
  Critical: 'bg-red-600/50',
};

export default function DashboardPage() {
  const { data: continents, isLoading, isError, refetch } = useContinents();
  const { data: stats } = useAdminStats();
  const t = getTranslations('en');

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* Title & Stats */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-light tracking-tight text-white">{t.dashboard.title}</h1>
          <p className="text-neutral-500 mt-1 font-mono text-sm uppercase tracking-widest">
            {t.dashboard.subtitle}
          </p>
        </div>

        <div className="flex gap-4 font-mono text-xs">
          <div className="bg-neutral-900 border border-neutral-800 rounded px-4 py-2 flex items-center gap-3">
            <Activity size={14} className="text-blue-500" />
            <span className="text-neutral-400">{t.dashboard.intelItems}:</span>
            <span className="text-white font-bold">
              {stats ? stats.intelligence_items.toLocaleString() : '—'}
            </span>
          </div>
          <div className="bg-neutral-900 border border-neutral-800 rounded px-4 py-2 flex items-center gap-3">
            <ShieldAlert size={14} className="text-red-500 animate-pulse" />
            <span className="text-neutral-400">{t.dashboard.pending}:</span>
            <span className="text-white font-bold">
              {stats ? stats.pending_contributions : '—'}
            </span>
          </div>
        </div>
      </div>

      {/* Main Map Area */}
      <div className="w-full aspect-[21/9] bg-neutral-900/50 border border-neutral-800 rounded-lg relative overflow-hidden">
        <GeoIntelligenceMap />
      </div>

      {/* Continents Grid */}
      {isError && (
        <ErrorState
          message="Failed to load geopolitical sectors"
          onRetry={() => refetch()}
        />
      )}

      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="min-h-[120px] rounded" />
          ))}
        </div>
      )}

      {!isLoading && !isError && continents && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          {continents.map((continent) => (
            <Link
              key={continent.id}
              href={`/continents/${continent.id}`}
              className="bg-neutral-900 border border-neutral-800 rounded p-4 hover:bg-neutral-800 hover:border-neutral-700 transition-colors cursor-pointer group flex flex-col justify-between min-h-[120px]"
            >
              <h3 className="text-sm font-semibold text-neutral-300 group-hover:text-blue-400 transition-colors">
                {continent.name}
              </h3>
              <div className="flex justify-between items-end mt-4">
                <span className="text-3xl font-light text-neutral-600 group-hover:text-neutral-400 transition-colors">
                  {continent.country_count}
                </span>
                <Cpu size={14} className="text-neutral-700 group-hover:text-blue-500/50" />
              </div>
              <div className="w-full bg-neutral-950 h-1 mt-3 rounded-full overflow-hidden">
                <div
                  className={`h-full ${riskColor['Medium']}`}
                  style={{ width: `${Math.min(100, (continent.country_count / 60) * 100)}%` }}
                />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
