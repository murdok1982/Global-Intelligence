'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ShieldCheck,
  ShieldX,
  Search,
} from 'lucide-react';
import apiClient from '@/lib/api-client';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import { ClassificationBadge } from '@/components/security/ClassificationBadge';
import type {
  AuditEvent,
  AuditEventsFilter,
  AuditEventsPage,
  AuditOutcome,
  AuditVerifyResponse,
} from '@/lib/api/types';
import { ClassificationLevel } from '@/lib/classification';

const PAGE_SIZE = 50;

function OutcomeChip({ outcome }: { outcome: AuditOutcome }) {
  const map: Record<AuditOutcome, { label: string; cls: string; Icon: typeof CheckCircle }> = {
    success: {
      label: 'success',
      cls: 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10',
      Icon: CheckCircle,
    },
    denied: {
      label: 'denied',
      cls: 'text-amber-300 border-amber-500/40 bg-amber-500/10',
      Icon: ShieldX,
    },
    error: {
      label: 'error',
      cls: 'text-red-300 border-red-500/40 bg-red-500/10',
      Icon: XCircle,
    },
  };
  const { label, cls, Icon } = map[outcome] ?? map.error;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-mono uppercase tracking-wider ${cls}`}
    >
      <Icon className="w-3 h-3" />
      {label}
    </span>
  );
}

export default function AuditLogPage() {
  const [filter, setFilter] = useState<AuditEventsFilter>({ page: 1, size: PAGE_SIZE });
  const [verifyResult, setVerifyResult] = useState<AuditVerifyResponse | null>(null);
  const [verifying, setVerifying] = useState(false);

  const params = useMemo(() => {
    const p: Record<string, string> = {};
    if (filter.event_type) p.event_type = filter.event_type;
    if (filter.actor) p.actor = filter.actor;
    if (filter.from) p.from = filter.from;
    if (filter.to) p.to = filter.to;
    if (filter.classification != null) {
      p.classification = String(filter.classification);
    }
    if (filter.outcome) p.outcome = filter.outcome;
    p.page = String(filter.page ?? 1);
    p.size = String(filter.size ?? PAGE_SIZE);
    return p;
  }, [filter]);

  const { data, isLoading, isError, refetch } = useQuery<AuditEventsPage>({
    queryKey: ['admin', 'audit', 'events', params],
    queryFn: async () => {
      const { data } = await apiClient.get<AuditEventsPage>('/admin/audit/events', { params });
      return data;
    },
    placeholderData: (prev) => prev,
  });

  const runVerify = async () => {
    setVerifying(true);
    try {
      const { data } = await apiClient.get<AuditVerifyResponse>('/admin/audit/verify');
      setVerifyResult(data);
    } catch {
      setVerifyResult({
        valid: false,
        total_events: 0,
        broken_at: null,
        last_hash: '<error>',
      });
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in">
      <div className="flex justify-between items-end border-b border-neutral-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-widest text-white uppercase flex items-center gap-3">
            <Activity className="w-6 h-6 text-emerald-400" />
            Audit Log
          </h1>
          <p className="text-neutral-500 mt-1 uppercase text-xs tracking-widest">
            Registro inmutable · cadena hash SHA-256
          </p>
        </div>
        <button
          onClick={runVerify}
          disabled={verifying}
          className="px-4 py-2 text-xs uppercase tracking-widest font-bold text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/10 rounded transition disabled:opacity-50"
        >
          <ShieldCheck className="w-4 h-4 inline mr-2" />
          {verifying ? 'Verificando…' : 'Verificar integridad'}
        </button>
      </div>

      {verifyResult && (
        <div
          className={`border rounded p-4 flex items-start gap-3 ${
            verifyResult.valid
              ? 'border-emerald-500/40 bg-emerald-500/5'
              : 'border-red-500/60 bg-red-500/10 animate-pulse'
          }`}
          role="alert"
        >
          {verifyResult.valid ? (
            <CheckCircle className="w-6 h-6 text-emerald-400 flex-shrink-0 mt-1" />
          ) : (
            <AlertTriangle className="w-6 h-6 text-red-400 flex-shrink-0 mt-1" />
          )}
          <div className="flex-1 text-sm">
            <p
              className={`font-bold uppercase tracking-wider ${
                verifyResult.valid ? 'text-emerald-300' : 'text-red-300'
              }`}
            >
              {verifyResult.valid
                ? 'Cadena íntegra'
                : 'ADULTERACIÓN DETECTADA'}
            </p>
            <p className="text-neutral-400 mt-1">
              {verifyResult.total_events} eventos auditados ·{' '}
              {verifyResult.valid
                ? `Last hash: ${verifyResult.last_hash.slice(0, 16)}…`
                : `Evento roto: ${verifyResult.broken_at ?? 'desconocido'}`}
            </p>
          </div>
          <button
            onClick={() => setVerifyResult(null)}
            className="text-neutral-500 hover:text-white text-xs"
          >
            cerrar
          </button>
        </div>
      )}

      {/* Filtros */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-2 bg-neutral-950 border border-neutral-800 rounded p-3">
        <input
          type="text"
          placeholder="event_type"
          value={filter.event_type ?? ''}
          onChange={(e) =>
            setFilter({ ...filter, event_type: e.target.value || undefined, page: 1 })
          }
          className="px-2 py-1.5 text-xs bg-neutral-900 border border-neutral-700 rounded font-mono"
        />
        <input
          type="text"
          placeholder="actor email/id"
          value={filter.actor ?? ''}
          onChange={(e) => setFilter({ ...filter, actor: e.target.value || undefined, page: 1 })}
          className="px-2 py-1.5 text-xs bg-neutral-900 border border-neutral-700 rounded font-mono"
        />
        <input
          type="date"
          value={filter.from ?? ''}
          onChange={(e) => setFilter({ ...filter, from: e.target.value || undefined, page: 1 })}
          className="px-2 py-1.5 text-xs bg-neutral-900 border border-neutral-700 rounded font-mono"
        />
        <input
          type="date"
          value={filter.to ?? ''}
          onChange={(e) => setFilter({ ...filter, to: e.target.value || undefined, page: 1 })}
          className="px-2 py-1.5 text-xs bg-neutral-900 border border-neutral-700 rounded font-mono"
        />
        <select
          value={filter.classification ?? ''}
          onChange={(e) =>
            setFilter({
              ...filter,
              classification: e.target.value === '' ? undefined : Number(e.target.value),
              page: 1,
            })
          }
          className="px-2 py-1.5 text-xs bg-neutral-900 border border-neutral-700 rounded font-mono"
        >
          <option value="">— clasificación —</option>
          <option value={ClassificationLevel.PUBLIC}>PUBLIC</option>
          <option value={ClassificationLevel.RESTRICTED}>RESTRICTED</option>
          <option value={ClassificationLevel.CONFIDENTIAL}>CONFIDENTIAL</option>
          <option value={ClassificationLevel.SECRET}>SECRET</option>
        </select>
        <select
          value={filter.outcome ?? ''}
          onChange={(e) =>
            setFilter({
              ...filter,
              outcome: (e.target.value || undefined) as AuditOutcome | undefined,
              page: 1,
            })
          }
          className="px-2 py-1.5 text-xs bg-neutral-900 border border-neutral-700 rounded font-mono"
        >
          <option value="">— outcome —</option>
          <option value="success">success</option>
          <option value="denied">denied</option>
          <option value="error">error</option>
        </select>
      </div>

      {isError && (
        <ErrorState message="No se pudo cargar el log de auditoría" onRetry={() => refetch()} />
      )}

      {isLoading && !data ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-10 rounded" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <div className="overflow-x-auto border border-neutral-800 rounded">
          <table className="w-full text-xs font-mono">
            <thead className="bg-neutral-900 text-neutral-400 uppercase tracking-widest">
              <tr>
                <th className="px-3 py-2 text-left">timestamp</th>
                <th className="px-3 py-2 text-left">event</th>
                <th className="px-3 py-2 text-left">actor</th>
                <th className="px-3 py-2 text-left">resource</th>
                <th className="px-3 py-2 text-left">clasif.</th>
                <th className="px-3 py-2 text-left">outcome</th>
                <th className="px-3 py-2 text-left">hash</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((e: AuditEvent) => (
                <tr key={e.id} className="border-t border-neutral-800 hover:bg-neutral-900/50">
                  <td className="px-3 py-2 text-neutral-300 whitespace-nowrap">
                    {new Date(e.timestamp).toISOString().replace('T', ' ').slice(0, 19)}
                  </td>
                  <td className="px-3 py-2 text-emerald-300">{e.event_type}</td>
                  <td className="px-3 py-2 text-neutral-400">
                    {e.actor_user_id ? e.actor_user_id.slice(0, 8) : '—'}
                  </td>
                  <td className="px-3 py-2 text-neutral-400">
                    {e.resource_type
                      ? `${e.resource_type}:${e.resource_id?.slice(0, 8) ?? '—'}`
                      : '—'}
                  </td>
                  <td className="px-3 py-2">
                    {e.classification != null ? (
                      <ClassificationBadge
                        classification={e.classification as ClassificationLevel}
                        short
                      />
                    ) : (
                      <span className="text-neutral-600">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <OutcomeChip outcome={e.outcome} />
                  </td>
                  <td className="px-3 py-2 text-neutral-600">{e.row_hash.slice(0, 10)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-12 border border-neutral-800 rounded">
          <Search className="w-8 h-8 text-neutral-600 mx-auto mb-2" />
          <p className="text-neutral-500 text-sm">Sin eventos para los filtros activos.</p>
        </div>
      )}

      {data && data.pages > 1 && (
        <div className="flex justify-between items-center text-xs uppercase tracking-widest text-neutral-500">
          <span>
            Página {data.page} de {data.pages} · {data.total} eventos
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setFilter({ ...filter, page: Math.max(1, (filter.page ?? 1) - 1) })}
              disabled={(filter.page ?? 1) <= 1}
              className="px-3 py-1.5 border border-neutral-700 rounded hover:border-neutral-500 disabled:opacity-30"
            >
              Anterior
            </button>
            <button
              onClick={() =>
                setFilter({ ...filter, page: Math.min(data.pages, (filter.page ?? 1) + 1) })
              }
              disabled={(filter.page ?? 1) >= data.pages}
              className="px-3 py-1.5 border border-neutral-700 rounded hover:border-neutral-500 disabled:opacity-30"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
