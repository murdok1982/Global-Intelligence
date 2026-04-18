'use client';

import Link from 'next/link';
import { Globe } from 'lucide-react';
import { useContinents } from '@/hooks/useContinents';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';

export default function ContinentsPage() {
  const { data: continents, isLoading, isError, refetch } = useContinents();

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div>
        <h1 className="text-3xl font-light tracking-tight text-white">Geopolitical Sectors</h1>
        <p className="text-neutral-500 mt-1 font-mono text-sm uppercase tracking-widest">
          Select macro-region to isolate intelligence nodes
        </p>
      </div>

      {isError && (
        <ErrorState
          message="Failed to load geopolitical sectors"
          onRetry={() => refetch()}
        />
      )}

      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="min-h-[200px] rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && !isError && continents && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {continents.map((continent) => (
            <Link
              href={`/continents/${continent.id}`}
              key={continent.id}
              className="block group"
            >
              <div className="bg-neutral-900/50 border border-neutral-800 rounded-lg p-6 hover:bg-neutral-800/80 hover:border-neutral-600 transition-all flex flex-col justify-between min-h-[200px] relative overflow-hidden">
                <div className="absolute -right-4 -bottom-4 opacity-5 group-hover:opacity-10 transition-opacity">
                  <Globe size={120} />
                </div>
                <div>
                  <h3 className="text-2xl font-light text-neutral-200 group-hover:text-blue-400 transition-colors uppercase tracking-widest">
                    {continent.name}
                  </h3>
                  <p className="text-neutral-500 font-mono text-xs mt-2">
                    CODE: {continent.code.toUpperCase()}
                  </p>
                </div>
                <div className="mt-8 flex justify-between items-end">
                  <div>
                    <p className="text-neutral-500 font-mono text-[10px] uppercase tracking-widest mb-1">
                      Countries
                    </p>
                    <p className="text-xl font-medium text-neutral-300">
                      {continent.country_count}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-neutral-500 font-mono text-[10px] uppercase tracking-widest mb-1">
                      Sector ID
                    </p>
                    <p className="text-sm font-bold text-blue-400 font-mono">
                      {continent.code.toUpperCase()}
                    </p>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
