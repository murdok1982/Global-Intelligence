'use client';

import Link from 'next/link';
import { use } from 'react';
import { ArrowLeft, Target } from 'lucide-react';
import { useContinent, useContinentCountries } from '@/hooks/useContinents';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';

const riskTextColor: Record<string, string> = {
  Low: 'text-emerald-400',
  Medium: 'text-blue-400',
  High: 'text-amber-500',
  Critical: 'text-red-500',
};

export default function ContinentDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const {
    data: continent,
    isLoading: loadingContinent,
    isError: errorContinent,
  } = useContinent(id);

  const {
    data: countries,
    isLoading: loadingCountries,
    isError: errorCountries,
    refetch,
  } = useContinentCountries(id);

  const isLoading = loadingContinent || loadingCountries;
  const isError = errorContinent || errorCountries;

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <Link
        href="/continents"
        className="flex items-center gap-2 text-neutral-500 hover:text-neutral-300 text-sm w-fit transition-colors"
      >
        <ArrowLeft size={16} /> Returns to Sectors
      </Link>

      {isLoading && (
        <>
          <Skeleton className="h-10 w-64 rounded" />
          <div className="grid grid-cols-1 gap-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded" />
            ))}
          </div>
        </>
      )}

      {isError && (
        <ErrorState
          message="Failed to load sector data"
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && (
        <>
          <div>
            <h1 className="text-3xl font-light tracking-tight text-white uppercase">
              {continent?.name ?? id} Sector
            </h1>
            <p className="text-neutral-500 mt-1 font-mono text-sm uppercase tracking-widest">
              Isolated Geopolitical Context — {continent?.country_count ?? 0} entities
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4">
            <div className="grid grid-cols-12 gap-4 px-4 py-2 font-mono text-[10px] text-neutral-500 uppercase tracking-widest border-b border-neutral-800">
              <div className="col-span-2">ISO</div>
              <div className="col-span-6">Entity</div>
              <div className="col-span-4 text-right">Risk Vector</div>
            </div>

            {countries && countries.length === 0 && (
              <p className="text-neutral-600 font-mono text-xs text-center py-8 uppercase tracking-widest">
                No entities indexed for this sector
              </p>
            )}

            {countries?.map((country) => {
              const risk = country.profile?.overall_risk_score;
              return (
                <Link
                  href={`/countries/${country.iso_code}`}
                  key={country.id}
                  className="group"
                >
                  <div className="grid grid-cols-12 gap-4 px-4 py-4 bg-neutral-900/40 border border-neutral-800/50 rounded hover:bg-neutral-800 hover:border-neutral-600 transition-all items-center">
                    <div className="col-span-2 font-mono text-xs text-neutral-500 group-hover:text-blue-500">
                      {country.iso_code.toUpperCase()}
                    </div>
                    <div className="col-span-6 font-medium text-neutral-300 group-hover:text-white flex items-center gap-2">
                      <Target
                        size={14}
                        className="text-neutral-700 group-hover:text-blue-500"
                      />
                      {country.name}
                    </div>
                    <div
                      className={`col-span-4 text-right font-mono text-xs font-bold ${
                        riskTextColor[risk ?? 'Medium'] ?? 'text-neutral-400'
                      }`}
                    >
                      {risk?.toUpperCase() ?? 'UNKNOWN'}
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
