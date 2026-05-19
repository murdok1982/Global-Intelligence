'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import { FileText, Lock, Unlock } from 'lucide-react';
import { useReports } from '@/hooks/useReports';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import { ClassificationBadge } from '@/components/security/ClassificationBadge';
import { ReportSignaturePresenceDot } from '@/components/security/ReportSignatureBadge';
import {
  ClassificationLevel,
  TLP,
  filterByClearance,
  toClassificationLevel,
  toTLP,
} from '@/lib/classification';

export default function ReportsIndex() {
  const { data: reports, isLoading, isError, refetch } = useReports();
  const { clearance } = useCurrentUser();

  /**
   * Defensa en profundidad: aunque el backend ya filtra por RLS, ocultamos
   * en el cliente cualquier informe cuya clasificación supere el clearance
   * del usuario actual.
   */
  const visibleReports = useMemo(() => {
    if (!reports) return [];
    return filterByClearance(reports, clearance);
  }, [reports, clearance]);

  return (
    <div className="space-y-8 animate-in fade-in duration-700 max-w-5xl mx-auto">
      <div>
        <h1 className="text-3xl font-light tracking-tight text-white uppercase">
          Informes sintetizados
        </h1>
        <p className="text-neutral-500 mt-1 font-mono text-sm uppercase tracking-widest">
          Matriz de inteligencia generativa
        </p>
      </div>

      {isError && (
        <ErrorState
          message="No se pudo cargar el archivo de informes"
          onRetry={() => refetch()}
        />
      )}

      {isLoading && (
        <div className="flex flex-col gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && !isError && reports && (
        <div className="flex flex-col gap-4">
          {visibleReports.length === 0 && (
            <p className="text-neutral-600 font-mono text-xs text-center py-12 uppercase tracking-widest">
              No hay informes accesibles para su nivel de clearance
            </p>
          )}

          {visibleReports.map((report) => {
            const isPublished = report.published;
            const date = new Date(report.report_date).toISOString().split('T')[0];
            const classification = toClassificationLevel(
              report.classification ?? ClassificationLevel.PUBLIC,
            );
            const tlp = toTLP(report.tlp ?? TLP.CLEAR);

            return (
              <Link
                href={isPublished ? `/reports/${report.id}` : '#'}
                key={report.id}
                aria-disabled={!isPublished}
                tabIndex={isPublished ? undefined : -1}
              >
                <div
                  className={`p-6 border rounded-lg flex items-center justify-between transition-all ${
                    isPublished
                      ? 'bg-neutral-900 border-neutral-800 hover:border-blue-500/50 hover:bg-neutral-800/80 cursor-pointer'
                      : 'bg-neutral-900/30 border-neutral-800/30 opacity-60 cursor-not-allowed'
                  }`}
                >
                  <div className="flex items-center gap-6">
                    <div
                      className={`p-3 rounded-full ${
                        isPublished
                          ? 'bg-blue-500/10 text-blue-500'
                          : 'bg-neutral-800 text-neutral-600'
                      }`}
                      aria-hidden="true"
                    >
                      {isPublished ? <FileText size={20} /> : <Lock size={20} />}
                    </div>
                    <div>
                      <h3 className="text-lg font-medium text-neutral-200 tracking-wide">
                        {report.executive_summary
                          ? report.executive_summary.slice(0, 80) +
                            (report.executive_summary.length > 80 ? '...' : '')
                          : `Informe ${report.id.slice(0, 8)}`}
                      </h3>
                      <div className="flex items-center gap-4 mt-2 flex-wrap">
                        <p className="text-neutral-500 font-mono text-xs uppercase tracking-widest">
                          Publicado: {date}
                        </p>
                        <p className="text-neutral-600 font-mono text-xs uppercase tracking-widest">
                          ID: {report.country_id.slice(0, 8)}
                        </p>
                        <ClassificationBadge
                          classification={classification}
                          tlp={tlp}
                          short
                        />
                        <ReportSignaturePresenceDot
                          signed={!!report.signature}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="hidden md:block">
                    {isPublished ? (
                      <span className="px-3 py-1 bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 text-xs font-mono font-bold tracking-widest rounded flex items-center gap-2">
                        <Unlock size={12} aria-hidden="true" /> PUBLICADO
                      </span>
                    ) : (
                      <span className="px-3 py-1 bg-neutral-800 text-neutral-500 border border-neutral-700 text-xs font-mono font-bold tracking-widest rounded flex items-center gap-2">
                        <Lock size={12} aria-hidden="true" /> RESTRINGIDO
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
