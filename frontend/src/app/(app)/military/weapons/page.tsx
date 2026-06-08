'use client';

import { useState } from 'react';
import { Crosshair, Filter, Search, ChevronLeft } from 'lucide-react';
import Link from 'next/link';
import { useWeapons } from '@/hooks/useMilitaryData';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import type { Weapon } from '@/lib/types';

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

export default function WeaponsPage() {
  const [category, setCategory] = useState('');
  const [origin, setOrigin] = useState('');
  const [search, setSearch] = useState('');
  const [selectedWeapon, setSelectedWeapon] = useState<Weapon | null>(null);

  const { data, isLoading, isError, refetch } = useWeapons(
    category || undefined,
    origin || undefined,
    search || undefined,
    1,
    50
  );

  if (selectedWeapon) {
    return (
      <div className="space-y-6 animate-in fade-in duration-500">
        <button
          onClick={() => setSelectedWeapon(null)}
          className="flex items-center gap-2 text-sm text-neutral-400 hover:text-white transition-colors font-mono uppercase tracking-widest"
        >
          <ChevronLeft size={16} />
          Back to catalog
        </button>

        <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-6">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <Crosshair size={20} className="text-blue-500" />
                <h1 className="text-2xl font-light text-white">{selectedWeapon.name}</h1>
              </div>
              <p className="font-mono text-sm text-blue-400 tracking-wide">{selectedWeapon.designation}</p>
              <div className="flex gap-2 mt-2">
                <span className="px-2 py-0.5 bg-neutral-800 border border-neutral-700 rounded text-xs text-neutral-300 font-mono">
                  {selectedWeapon.category}
                </span>
                <span className="px-2 py-0.5 bg-neutral-800 border border-neutral-700 rounded text-xs text-neutral-300 font-mono">
                  {selectedWeapon.origin_country}
                </span>
              </div>
            </div>
            {selectedWeapon.cost_usd != null && (
              <div className="bg-neutral-950 border border-neutral-800 rounded px-4 py-3">
                <p className="text-xs font-mono text-neutral-500 uppercase tracking-widest">Unit Cost</p>
                <p className="text-xl font-mono text-emerald-400 mt-1">
                  ${selectedWeapon.cost_usd.toLocaleString()}
                </p>
              </div>
            )}
          </div>

          {selectedWeapon.description && (
            <div className="mt-6 border-t border-neutral-800 pt-6">
              <p className="text-sm text-neutral-400 leading-relaxed">{selectedWeapon.description}</p>
            </div>
          )}

          {Object.keys(selectedWeapon.key_specs).length > 0 && (
            <div className="mt-6 border-t border-neutral-800 pt-6">
              <h3 className="text-sm font-mono text-neutral-500 uppercase tracking-widest mb-4">
                Key Specifications
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {Object.entries(selectedWeapon.key_specs).map(([key, value]) => (
                  <div key={key} className="bg-neutral-950 border border-neutral-800 rounded p-3">
                    <p className="text-xs font-mono text-neutral-600 uppercase tracking-widest">{key}</p>
                    <p className="text-sm text-neutral-200 mt-1">{value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link
              href="/military"
              className="text-xs font-mono text-neutral-500 hover:text-blue-400 transition-colors uppercase tracking-widest"
            >
              Military
            </Link>
            <span className="text-neutral-700">/</span>
            <span className="text-xs font-mono text-neutral-400 uppercase tracking-widest">Weapons</span>
          </div>
          <h1 className="text-3xl font-light tracking-tight text-white">Weapons Catalog</h1>
          <p className="text-neutral-500 mt-1 font-mono text-sm uppercase tracking-widest">
            Global weapon systems database
          </p>
        </div>
        <div className="bg-yellow-950 border border-yellow-500/50 rounded px-4 py-2 font-mono text-xs text-yellow-300 tracking-widest uppercase">
          Classification: Restricted
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-500" />
          <input
            type="text"
            placeholder="Search weapons..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 pl-8 pr-3 bg-neutral-950 border border-neutral-700 rounded text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-blue-600 w-56"
          />
        </div>
        <div className="relative">
          <Filter size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-500" />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="h-9 pl-8 pr-8 bg-neutral-950 border border-neutral-700 rounded text-sm text-neutral-200 focus:outline-none focus:border-blue-600 appearance-none cursor-pointer"
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
          className="h-9 px-3 bg-neutral-950 border border-neutral-700 rounded text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-blue-600 w-40"
        />
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <Skeleton key={i} className="min-h-[200px] rounded-lg" />
          ))}
        </div>
      )}

      {isError && (
        <ErrorState message="Failed to load weapons catalog" onRetry={() => refetch()} />
      )}

      {!isLoading && !isError && data && (
        <>
          <p className="text-xs font-mono text-neutral-600 uppercase tracking-widest">
            {data.total.toLocaleString()} systems found
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.items.map((weapon) => (
              <button
                key={weapon.id}
                onClick={() => setSelectedWeapon(weapon)}
                className="bg-neutral-900 border border-neutral-800 rounded-lg p-5 hover:bg-neutral-800 hover:border-neutral-700 transition-colors cursor-pointer text-left group flex flex-col justify-between min-h-[200px]"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-mono text-xs text-blue-400 tracking-wide">{weapon.designation}</p>
                      <h3 className="text-base font-semibold text-neutral-200 group-hover:text-white transition-colors mt-1">
                        {weapon.name}
                      </h3>
                    </div>
                    <span className="text-lg shrink-0" title={weapon.origin_country}>
                      {getFlagEmoji(weapon.origin_country)}
                    </span>
                  </div>

                  <div className="flex gap-2 mt-3">
                    <span className="px-2 py-0.5 bg-neutral-800 border border-neutral-700 rounded text-[10px] text-neutral-400 font-mono uppercase">
                      {weapon.category}
                    </span>
                    <span className="px-2 py-0.5 bg-neutral-800 border border-neutral-700 rounded text-[10px] text-neutral-400 font-mono">
                      {weapon.origin_country}
                    </span>
                  </div>

                  {Object.keys(weapon.key_specs).length > 0 && (
                    <div className="mt-3 space-y-1">
                      {Object.entries(weapon.key_specs).slice(0, 3).map(([key, value]) => (
                        <div key={key} className="flex justify-between text-xs">
                          <span className="text-neutral-600 font-mono uppercase text-[10px]">{key}</span>
                          <span className="text-neutral-400">{value}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex items-end justify-between mt-4 pt-3 border-t border-neutral-800">
                  <span className="text-sm font-mono text-emerald-400">
                    {weapon.cost_usd != null ? `$${(weapon.cost_usd / 1e6).toFixed(1)}M` : '—'}
                  </span>
                  <span className="text-[10px] font-mono text-neutral-600 group-hover:text-blue-400 transition-colors uppercase tracking-widest">
                    View details →
                  </span>
                </div>
              </button>
            ))}
          </div>
          {data.items.length === 0 && (
            <div className="text-center py-12 text-neutral-600 font-mono text-xs uppercase tracking-widest">
              No weapons match current filters
            </div>
          )}
        </>
      )}
    </div>
  );
}

function getFlagEmoji(country: string): string {
  const flags: Record<string, string> = {
    'United States': '🇺🇸',
    'Russia': '🇷🇺',
    'China': '🇨🇳',
    'United Kingdom': '🇬🇧',
    'France': '🇫🇷',
    'Germany': '🇩🇪',
    'India': '🇮🇳',
    'Japan': '🇯🇵',
    'South Korea': '🇰🇷',
    'Israel': '🇮🇱',
    'Turkey': '🇹🇷',
    'Italy': '🇮🇹',
    'Brazil': '🇧🇷',
    'Saudi Arabia': '🇸🇦',
    'Australia': '🇦🇺',
    'Ukraine': '🇺🇦',
    'Iran': '🇮🇷',
    'North Korea': '🇰🇵',
    'Pakistan': '🇵🇰',
    'Sweden': '🇸🇪',
  };
  return flags[country] ?? '🏳️';
}
