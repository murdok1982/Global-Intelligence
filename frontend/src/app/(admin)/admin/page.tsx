'use client';

import { Activity, Users, FileWarning, FileText, Globe } from 'lucide-react';
import { useAdminStats, useContributions, useReviewContribution } from '@/hooks/useAdmin';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import toast from 'react-hot-toast';

export default function AdminDashboard() {
  const { data: stats, isLoading: loadingStats, isError: errorStats, refetch: refetchStats } = useAdminStats();
  const { data: contributions, isLoading: loadingContribs, isError: errorContribs, refetch: refetchContribs } = useContributions();
  const reviewContribution = useReviewContribution();

  const handleReview = async (id: string, action: 'approve' | 'reject') => {
    try {
      await reviewContribution.mutateAsync({ id, action });
      toast.success(`Contribution ${action}d`);
    } catch {
      toast.error(`Failed to ${action} contribution`);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in">
      <div className="flex justify-between items-end border-b border-neutral-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-widest text-white uppercase">
            Internal Overseer
          </h1>
          <p className="text-neutral-500 mt-1 uppercase text-xs tracking-widest">
            Global Intelligence Governance & Audit
          </p>
        </div>
        <div className="bg-red-500/10 text-red-500 px-3 py-1 rounded border border-red-500/20 text-xs font-bold font-mono">
          E2E ENCRYPTION MATRICES: ACTIVE
        </div>
      </div>

      {/* Stats Grid */}
      {errorStats && (
        <ErrorState
          message="Failed to load system statistics"
          onRetry={() => refetchStats()}
        />
      )}

      {loadingStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded" />
          ))}
        </div>
      )}

      {!loadingStats && !errorStats && stats && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="bg-neutral-900 border border-neutral-800 p-4">
            <p className="text-neutral-500 text-xs uppercase tracking-widest mb-2 flex items-center gap-2">
              <Activity size={12} /> OSINT Agent Status
            </p>
            <p className="text-2xl font-light text-emerald-500">OPERATIONAL</p>
          </div>
          <div className="bg-neutral-900 border border-neutral-800 p-4">
            <p className="text-neutral-500 text-xs uppercase tracking-widest mb-2 flex items-center gap-2">
              <Users size={12} /> Users
            </p>
            <p className="text-2xl font-light text-white">{stats.users.toLocaleString()}</p>
          </div>
          <div className="bg-neutral-900 border border-neutral-800 p-4">
            <p className="text-neutral-500 text-xs uppercase tracking-widest mb-2 flex items-center gap-2">
              <Globe size={12} /> Countries
            </p>
            <p className="text-2xl font-light text-white">{stats.countries}</p>
          </div>
          <div className="bg-neutral-900 border border-neutral-800 p-4">
            <p className="text-neutral-500 text-xs uppercase tracking-widest mb-2 flex items-center gap-2">
              <FileText size={12} /> Reports
            </p>
            <p className="text-2xl font-light text-white">{stats.reports}</p>
          </div>
          <div className="bg-neutral-900 border border-neutral-800 p-4">
            <p className="text-neutral-500 text-xs uppercase tracking-widest mb-2 flex items-center gap-2">
              <FileWarning size={12} /> Pending Contributions
            </p>
            <p className="text-2xl font-light text-amber-500">
              {stats.pending_contributions}
            </p>
          </div>
        </div>
      )}

      {/* Contributions Queue */}
      <div className="bg-neutral-900 border border-neutral-800">
        <div className="border-b border-neutral-800 p-3 bg-neutral-950 flex justify-between items-center">
          <h3 className="text-xs uppercase tracking-widest text-neutral-400">
            Contributor Intelligence Clearance Queue
          </h3>
          {contributions && (
            <span className="font-mono text-[10px] text-neutral-600 uppercase tracking-widest">
              {contributions.filter((c) => c.status === 'pending').length} pending
            </span>
          )}
        </div>

        {errorContribs && (
          <ErrorState
            message="Failed to load contributions"
            onRetry={() => refetchContribs()}
          />
        )}

        {loadingContribs && (
          <div className="p-4 space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-14 rounded" />
            ))}
          </div>
        )}

        {!loadingContribs && !errorContribs && contributions && (
          <div className="p-4 space-y-2">
            {contributions.length === 0 && (
              <p className="text-neutral-600 font-mono text-xs text-center py-8 uppercase tracking-widest">
                Queue empty
              </p>
            )}

            {contributions.map((contrib) => (
              <div
                key={contrib.id}
                className="flex justify-between p-3 border border-neutral-800 bg-black items-center gap-4"
              >
                <div className="flex gap-4 text-sm font-mono text-neutral-400 flex-wrap flex-1">
                  <span className="text-blue-500 font-bold uppercase">
                    {contrib.country}
                  </span>
                  <span>Category: {contrib.category}</span>
                  {contrib.alias && (
                    <span className="text-neutral-600">
                      Alias: {contrib.alias}
                    </span>
                  )}
                  <span className="text-neutral-600 truncate max-w-[200px]">
                    {contrib.description}
                  </span>
                  <span
                    className={`text-[10px] uppercase tracking-widest ${
                      contrib.status === 'pending'
                        ? 'text-amber-500'
                        : contrib.status === 'approved'
                        ? 'text-emerald-500'
                        : 'text-red-500'
                    }`}
                  >
                    {contrib.status}
                  </span>
                </div>

                {contrib.status === 'pending' && (
                  <div className="flex gap-2 flex-shrink-0">
                    <button
                      onClick={() => handleReview(contrib.id, 'approve')}
                      disabled={reviewContribution.isPending}
                      className="bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 px-3 py-1 text-xs hover:bg-emerald-500/20 disabled:opacity-50 transition-colors min-h-[44px]"
                    >
                      APPROVE
                    </button>
                    <button
                      onClick={() => handleReview(contrib.id, 'reject')}
                      disabled={reviewContribution.isPending}
                      className="bg-red-500/10 text-red-500 border border-red-500/30 px-3 py-1 text-xs hover:bg-red-500/20 disabled:opacity-50 transition-colors min-h-[44px]"
                    >
                      DROP
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
