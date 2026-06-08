'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';
import {
  Crosshair,
  ArrowRightLeft,
  Building2,
  DollarSign,
  Search,
  Filter,
  Clock,
} from 'lucide-react';
import { useWeapons, useArmsTransfers, useMilitaryStats } from '@/hooks/useMilitaryData';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';

const GeoIntelligenceMap = dynamic(
  () => import('@/components/map/GeoIntelligenceMap').then((m) => m.GeoIntelligenceMap),
  { ssr: false, loading: () => <Skeleton className="w-full h-[500px] rounded-lg" /> }
);

const WEAPON_CATEGORIES = [
  'All',
  'Aircraft',
  'Armored Vehicles',
  'Naval Vessels',
  'Missiles',
  'Artillery',
  'Small Arms',
  'Air Defense',
  'UAV/Drones',
];

export default function MilitaryPage() {
  const [category, setCategory] = useState('');
  const [origin, setOrigin] = useState('');
  const [search, setSearch] = useState('');
  const [yearFrom, setYearFrom] = useState<number | undefined>(undefined);
  const [yearTo, setYearTo] = useState<number | undefined>(undefined);

  const { data: stats, isLoading: statsLoading } = useMilitaryStats();
  const { data: weapons, isLoading: weaponsLoading, isError: weaponsError, refetch: refetchWeapons } = useWeapons(
    category || undefined,
    origin || undefined,
    search || undefined
  );
  const { data: transfers, isLoading: transfersLoading } = useArmsTransfers(
    undefined,
    undefined,
    yearFrom,
    yearTo
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-light tracking-tight text-white">Military Intelligence</h1>
          <p className="text-neutral-500 mt-1 font-mono text-sm uppercase tracking-widest">
            Global defense posture &amp; arms monitoring
          </p>
        </div>
        <div className="bg-yellow-950 border border-yellow-500/50 rounded px-4 py-2 font-mono text-xs text-yellow-300 tracking-widest uppercase">
          Classification: Restricted
        </div>
      </div>

      <div className="w-full h-[500px]">
        <GeoIntelligenceMap />
      </div>

      {statsLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="min-h-[100px] rounded" />
          ))}
        </div>
      ) : stats ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={<Crosshair size={18} className="text-blue-500" />}
            label="Weapon Systems"
            value={stats.total_weapons.toLocaleString()}
          />
          <StatCard
            icon={<ArrowRightLeft size={18} className="text-amber-500" />}
            label="Arms Transfers"
            value={stats.total_transfers.toLocaleString()}
          />
          <StatCard
            icon={<Building2 size={18} className="text-cyan-500" />}
            label="Military Bases"
            value={stats.total_bases.toLocaleString()}
          />
          <StatCard
            icon={<DollarSign size={18} className="text-emerald-500" />}
            label="Global Spend"
            value={`$${(stats.global_spend_usd / 1e9).toFixed(1)}B`}
          />
        </div>
      ) : null}

      <div className="bg-neutral-900 border border-neutral-800 rounded-lg">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 border-b border-neutral-800">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Crosshair size={16} className="text-blue-500" />
            Weapons Catalog
          </h2>
          <div className="flex flex-wrap gap-2">
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-500" />
              <input
                type="text"
                placeholder="Search weapons..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-8 pl-8 pr-3 bg-neutral-950 border border-neutral-700 rounded text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-blue-600 w-48"
              />
            </div>
            <div className="relative">
              <Filter size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-500" />
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="h-8 pl-8 pr-8 bg-neutral-950 border border-neutral-700 rounded text-sm text-neutral-200 focus:outline-none focus:border-blue-600 appearance-none cursor-pointer"
              >
                {WEAPON_CATEGORIES.map((c) => (
                  <option key={c} value={c === 'All' ? '' : c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <input
              type="text"
              placeholder="Origin country"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              className="h-8 px-3 bg-neutral-950 border border-neutral-700 rounded text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-blue-600 w-36"
            />
          </div>
        </div>

        {weaponsLoading && (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 rounded" />
            ))}
          </div>
        )}

        {weaponsError && (
          <ErrorState message="Failed to load weapons data" onRetry={() => refetchWeapons()} />
        )}

        {!weaponsLoading && !weaponsError && weapons && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-800 text-neutral-500 font-mono text-xs uppercase tracking-widest">
                  <th className="text-left px-4 py-3">Designation</th>
                  <th className="text-left px-4 py-3">Name</th>
                  <th className="text-left px-4 py-3">Origin</th>
                  <th className="text-left px-4 py-3">Category</th>
                  <th className="text-right px-4 py-3">Cost (USD)</th>
                </tr>
              </thead>
              <tbody>
                {weapons.items.map((w) => (
                  <tr
                    key={w.id}
                    className="border-b border-neutral-800/50 hover:bg-neutral-800/50 transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-3 font-mono text-blue-400">{w.designation}</td>
                    <td className="px-4 py-3 text-neutral-200">{w.name}</td>
                    <td className="px-4 py-3 text-neutral-400">{w.origin_country}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 bg-neutral-800 border border-neutral-700 rounded text-xs text-neutral-300 font-mono">
                        {w.category}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-emerald-400">
                      {w.cost_usd != null ? `$${(w.cost_usd / 1e6).toFixed(1)}M` : '—'}
                    </td>
                  </tr>
                ))}
                {weapons.items.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-neutral-600 font-mono text-xs uppercase tracking-widest">
                      No weapons match current filters
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-neutral-900 border border-neutral-800 rounded-lg">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 border-b border-neutral-800">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Clock size={16} className="text-amber-500" />
            Arms Transfers Timeline
          </h2>
          <div className="flex gap-2 items-center">
            <input
              type="number"
              placeholder="From year"
              value={yearFrom ?? ''}
              onChange={(e) => setYearFrom(e.target.value ? Number(e.target.value) : undefined)}
              className="h-8 px-3 bg-neutral-950 border border-neutral-700 rounded text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-blue-600 w-24"
            />
            <span className="text-neutral-600">—</span>
            <input
              type="number"
              placeholder="To year"
              value={yearTo ?? ''}
              onChange={(e) => setYearTo(e.target.value ? Number(e.target.value) : undefined)}
              className="h-8 px-3 bg-neutral-950 border border-neutral-700 rounded text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-blue-600 w-24"
            />
          </div>
        </div>

        {transfersLoading && (
          <div className="p-4 space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-14 rounded" />
            ))}
          </div>
        )}

        {!transfersLoading && transfers && (
          <div className="divide-y divide-neutral-800/50">
            {transfers.slice(0, 20).map((t) => (
              <div key={t.id} className="flex items-center gap-4 px-4 py-3 hover:bg-neutral-800/50 transition-colors">
                <div className="w-16 text-center font-mono text-xs text-neutral-500">{t.year}</div>
                <div className="flex-1 flex items-center gap-2 text-sm min-w-0">
                  <span className="text-neutral-200 truncate">{t.supplier_country}</span>
                  <ArrowRightLeft size={14} className="text-blue-500 shrink-0" />
                  <span className="text-neutral-200 truncate">{t.recipient_country}</span>
                </div>
                <div className="text-sm text-neutral-400 truncate max-w-[200px]">{t.weapon_system}</div>
                <div className="text-sm font-mono text-emerald-400 shrink-0 w-24 text-right">
                  {t.value_usd != null ? `$${(t.value_usd / 1e6).toFixed(1)}M` : '—'}
                </div>
                <span className="px-2 py-0.5 bg-neutral-800 border border-neutral-700 rounded text-xs text-neutral-300 font-mono shrink-0">
                  {t.status}
                </span>
              </div>
            ))}
            {transfers.length === 0 && (
              <div className="px-4 py-8 text-center text-neutral-600 font-mono text-xs uppercase tracking-widest">
                No transfers found for selected period
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-4 flex flex-col justify-between min-h-[100px] hover:border-neutral-700 transition-colors">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-xs font-mono text-neutral-500 uppercase tracking-widest">{label}</span>
      </div>
      <p className="text-2xl font-light text-white mt-2">{value}</p>
    </div>
  );
}
