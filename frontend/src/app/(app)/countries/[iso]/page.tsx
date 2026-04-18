'use client';

import { use, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Briefcase,
  Landmark,
  Shield,
  Users,
  RadioTower,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useCountry, useCountryIntelligence } from '@/hooks/useCountries';
import { useGenerateReport } from '@/hooks/useReports';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import toast from 'react-hot-toast';

const CATEGORIES = [
  { id: 'economic', label: 'Economic', icon: Briefcase },
  { id: 'political', label: 'Political', icon: Landmark },
  { id: 'military', label: 'Military', icon: Shield },
  { id: 'social', label: 'Social', icon: Users },
  { id: 'security', label: 'Security', icon: RadioTower },
];

const riskBadge: Record<string, string> = {
  Low: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  Medium: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  High: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
  Critical: 'bg-red-500/10 text-red-500 border-red-500/20',
};

const confidenceColor = (score: number) => {
  if (score >= 0.8) return 'text-emerald-400';
  if (score >= 0.5) return 'text-amber-400';
  return 'text-red-400';
};

export default function CountryProfile({
  params,
}: {
  params: Promise<{ iso: string }>;
}) {
  const { iso } = use(params);
  const [activeCategory, setActiveCategory] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);

  const {
    data: country,
    isLoading: loadingCountry,
    isError: errorCountry,
  } = useCountry(iso);

  const {
    data: intelligence,
    isLoading: loadingIntel,
    isError: errorIntel,
    refetch: refetchIntel,
  } = useCountryIntelligence(iso, activeCategory, page);

  const generateReport = useGenerateReport();

  const handleGenerate = async () => {
    try {
      const report = await generateReport.mutateAsync({ country_iso: iso });
      toast.success(`Report generated: ${report.id.slice(0, 8)}...`);
    } catch {
      toast.error('Failed to generate report');
    }
  };

  const risk = country?.profile?.overall_risk_score;

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex justify-between items-start">
        <div>
          <Link
            href="/continents"
            className="flex items-center gap-2 text-neutral-500 hover:text-neutral-300 text-sm w-fit transition-colors mb-6"
          >
            <ArrowLeft size={16} /> Returns to Map
          </Link>
          <div className="flex items-center gap-4 flex-wrap">
            {loadingCountry ? (
              <Skeleton className="h-10 w-72 rounded" />
            ) : (
              <>
                <h1 className="text-4xl font-light tracking-widest text-white uppercase">
                  {country?.name ?? iso} PROFILE
                </h1>
                {risk && (
                  <span
                    className={`px-3 py-1 border text-xs font-mono font-bold tracking-widest rounded ${
                      riskBadge[risk] ?? riskBadge['Medium']
                    }`}
                  >
                    {risk.toUpperCase()} THREAT
                  </span>
                )}
              </>
            )}
          </div>
          <p className="text-neutral-500 mt-2 font-mono text-sm uppercase tracking-widest">
            Target Entity OSINT Synchronization
          </p>
        </div>

        <button
          onClick={handleGenerate}
          disabled={generateReport.isPending}
          className="px-6 py-3 bg-blue-600/10 text-blue-500 hover:bg-blue-600/20 hover:text-blue-400 border border-blue-600/30 rounded text-xs font-mono font-bold uppercase tracking-widest flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px]"
        >
          {generateReport.isPending ? (
            <>
              <div className="w-3 h-3 border border-blue-500 border-t-transparent rounded-full animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <AlertTriangle size={14} />
              Generate Daily Interactive Report
            </>
          )}
        </button>
      </div>

      {errorCountry && (
        <ErrorState message="Failed to load country profile" />
      )}

      {/* OSINT Category Tabs */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          const isActive = activeCategory === cat.id;
          return (
            <button
              key={cat.id}
              onClick={() => {
                setActiveCategory(isActive ? undefined : cat.id);
                setPage(1);
              }}
              className={`bg-neutral-900 border rounded p-4 hover:border-neutral-600 cursor-pointer transition-colors group text-left ${
                isActive
                  ? 'border-blue-500/40 bg-blue-500/5'
                  : 'border-neutral-800'
              }`}
            >
              <div className="flex justify-between items-start mb-6">
                <div
                  className={`p-2 rounded ${
                    isActive
                      ? 'bg-blue-500/10 text-blue-500'
                      : 'bg-neutral-800 text-neutral-500'
                  }`}
                >
                  <Icon size={16} />
                </div>
              </div>
              <p className="font-mono text-xs uppercase tracking-widest text-neutral-500 mb-1">
                Sector
              </p>
              <h3
                className={`font-medium ${
                  isActive ? 'text-blue-400' : 'text-neutral-300 group-hover:text-blue-400'
                }`}
              >
                {cat.label}
              </h3>
            </button>
          );
        })}
      </div>

      {/* Intelligence Feed */}
      <div className="border border-neutral-800 bg-neutral-900/30 rounded-lg">
        <div className="border-b border-neutral-800 p-4 bg-neutral-900/50 flex items-center justify-between">
          <h3 className="font-mono text-xs tracking-widest text-neutral-400 uppercase">
            Live Intelligence Feed Array
            {activeCategory && (
              <span className="ml-3 text-blue-400">— {activeCategory.toUpperCase()}</span>
            )}
          </h3>
          {intelligence && (
            <span className="font-mono text-[10px] text-neutral-600 uppercase tracking-widest">
              {intelligence.total} items
            </span>
          )}
        </div>

        {loadingIntel && (
          <div className="p-6 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-20 rounded" />
            ))}
          </div>
        )}

        {errorIntel && (
          <ErrorState
            message="Failed to load intelligence feed"
            onRetry={() => refetchIntel()}
          />
        )}

        {!loadingIntel && !errorIntel && intelligence && (
          <>
            {intelligence.items.length === 0 ? (
              <div className="p-8 flex flex-col items-center justify-center min-h-[300px]">
                <RadioTower size={48} className="mb-4 text-neutral-700" />
                <p className="font-mono text-sm uppercase tracking-widest text-neutral-600">
                  No signals in this sector
                </p>
              </div>
            ) : (
              <div className="divide-y divide-neutral-800/50">
                {intelligence.items.map((item) => (
                  <div
                    key={item.id}
                    className="p-5 hover:bg-neutral-900/40 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <span className="font-mono text-[10px] text-blue-500 uppercase tracking-widest bg-blue-500/10 px-2 py-0.5 rounded">
                        {item.agent_source}
                      </span>
                      <span
                        className={`font-mono text-[10px] ${confidenceColor(item.confidence_score)}`}
                      >
                        {Math.round(item.confidence_score * 100)}% confidence
                      </span>
                    </div>
                    <p className="text-neutral-300 text-sm font-light leading-relaxed">
                      {item.content}
                    </p>
                    <p className="text-neutral-600 font-mono text-[10px] mt-3 uppercase tracking-widest">
                      {new Date(item.created_at).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            )}

            {/* Pagination */}
            {intelligence.pages > 1 && (
              <div className="border-t border-neutral-800 p-4 flex items-center justify-between">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="flex items-center gap-2 font-mono text-xs text-neutral-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors min-h-[44px] px-3"
                >
                  <ChevronLeft size={14} /> Prev
                </button>
                <span className="font-mono text-xs text-neutral-600">
                  Page {intelligence.page} of {intelligence.pages}
                </span>
                <button
                  onClick={() =>
                    setPage((p) => Math.min(intelligence.pages, p + 1))
                  }
                  disabled={page === intelligence.pages}
                  className="flex items-center gap-2 font-mono text-xs text-neutral-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors min-h-[44px] px-3"
                >
                  Next <ChevronRight size={14} />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
