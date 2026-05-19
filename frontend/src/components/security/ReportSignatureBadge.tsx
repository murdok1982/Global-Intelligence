'use client';

import { useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  Loader2,
  ShieldOff,
} from 'lucide-react';
import {
  usePublicSigningKey,
  useReportSignature,
  useVerifyReportSignature,
} from '@/hooks/useReportSignature';
import { ReportSignatureModal } from '@/components/security/ReportSignatureModal';
import type { SignedReport } from '@/lib/signing';
import { cn } from '@/lib/utils';

interface ReportSignatureBadgeProps {
  report: SignedReport;
  className?: string;
}

/**
 * Chip que muestra el estado de la firma criptográfica del reporte.
 *
 * Estados visuales:
 *  - SIN FIRMAR     → ámbar, no clickable (no hay datos extra que mostrar).
 *  - VERIFICANDO    → azul, loader.
 *  - VERIFICADO     → verde, ShieldCheck + fingerprint corto. Click → modal.
 *  - INVÁLIDA       → rojo pulsante con ShieldAlert. Click → modal.
 *  - NO SOPORTADO   → ámbar, ShieldQuestion, tooltip explicativo.
 */
export function ReportSignatureBadge({
  report,
  className,
}: ReportSignatureBadgeProps) {
  const [modalOpen, setModalOpen] = useState(false);

  const hasSignature = !!report.signature;

  const pubkeyQuery = usePublicSigningKey();
  const bundleQuery = useReportSignature(hasSignature ? report.id : undefined);

  const state = useVerifyReportSignature(
    hasSignature ? report : undefined,
    bundleQuery.data,
    pubkeyQuery.data,
  );

  // Caso 1: sin firma
  if (!hasSignature) {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 border rounded font-mono text-[10px] uppercase tracking-widest font-bold bg-amber-950/50 text-amber-300 border-amber-500/40',
          className,
        )}
        aria-label="Reporte sin firma criptográfica"
        role="status"
      >
        <ShieldOff size={12} aria-hidden="true" />
        Sin firmar
      </span>
    );
  }

  const loading =
    pubkeyQuery.isLoading ||
    bundleQuery.isLoading ||
    state.verifying ||
    state.mode === 'pending';
  const error = pubkeyQuery.isError || bundleQuery.isError;

  // Caso 2: cargando
  if (loading) {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 border rounded font-mono text-[10px] uppercase tracking-widest font-bold bg-blue-950/50 text-blue-300 border-blue-500/40',
          className,
        )}
        aria-label="Verificando firma criptográfica del reporte"
        role="status"
        aria-live="polite"
      >
        <Loader2 size={12} className="animate-spin" aria-hidden="true" />
        Verificando…
      </span>
    );
  }

  // Caso 3: error al obtener bundle o pubkey
  if (error) {
    return (
      <button
        type="button"
        onClick={() => setModalOpen(true)}
        className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 border rounded font-mono text-[10px] uppercase tracking-widest font-bold bg-amber-950/50 text-amber-300 border-amber-500/40 min-h-[28px] hover:bg-amber-900/50 transition-colors',
          className,
        )}
        aria-label="No se pudo verificar la firma — abrir detalles"
      >
        <ShieldQuestion size={12} aria-hidden="true" />
        Firma no verificable
      </button>
    );
  }

  const fpShort = state.fingerprint_match === false
    ? (bundleQuery.data?.public_key_fingerprint ?? '').slice(0, 8)
    : (pubkeyQuery.data?.fingerprint ?? '').slice(0, 8);

  // Caso 4: firma inválida → ALERTA roja pulsante
  if (state.valid === false && !state.error) {
    return (
      <>
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className={cn(
            'inline-flex items-center gap-1.5 px-2.5 py-1 border rounded font-mono text-[10px] uppercase tracking-widest font-bold bg-red-950/70 text-red-200 border-red-500/60 animate-pulse min-h-[28px] hover:bg-red-900/70 transition-colors',
            className,
          )}
          aria-label="Firma inválida — el documento puede estar adulterado. Abrir detalles"
          role="alert"
          aria-live="assertive"
        >
          <ShieldAlert size={12} aria-hidden="true" />
          Firma inválida — adulteración
        </button>
        <ReportSignatureModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          bundle={bundleQuery.data}
          pubkey={pubkeyQuery.data}
          state={state}
          signedAt={getSignedAt(report)}
        />
      </>
    );
  }

  // Caso 5: error durante verificación (p. ej. blob mal formado)
  if (state.error) {
    return (
      <>
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className={cn(
            'inline-flex items-center gap-1.5 px-2.5 py-1 border rounded font-mono text-[10px] uppercase tracking-widest font-bold bg-amber-950/50 text-amber-300 border-amber-500/40 min-h-[28px] hover:bg-amber-900/50 transition-colors',
            className,
          )}
          aria-label={`Firma no verificable: ${state.error}. Abrir detalles`}
          title={state.error}
        >
          <ShieldQuestion size={12} aria-hidden="true" />
          Verificación incompleta
        </button>
        <ReportSignatureModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          bundle={bundleQuery.data}
          pubkey={pubkeyQuery.data}
          state={state}
          signedAt={getSignedAt(report)}
        />
      </>
    );
  }

  // Caso 6: válida
  const mismatch = state.fingerprint_match === false;
  return (
    <>
      <button
        type="button"
        onClick={() => setModalOpen(true)}
        className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 border rounded font-mono text-[10px] uppercase tracking-widest font-bold min-h-[28px] transition-colors',
          mismatch
            ? 'bg-amber-950/50 text-amber-200 border-amber-500/50 hover:bg-amber-900/50'
            : 'bg-emerald-950/60 text-emerald-200 border-emerald-500/50 hover:bg-emerald-900/60',
          className,
        )}
        aria-label={`Firma verificada${mismatch ? ' con clave archivada' : ''}. Abrir detalles. Fingerprint ${fpShort}`}
      >
        <ShieldCheck size={12} aria-hidden="true" />
        <span>
          {mismatch ? 'Firmado · clave anterior' : 'Firmado · verificado'}
        </span>
        {fpShort && (
          <>
            <span aria-hidden="true" className="opacity-50">·</span>
            <span className="font-mono">{fpShort}</span>
          </>
        )}
      </button>
      <ReportSignatureModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        bundle={bundleQuery.data}
        pubkey={pubkeyQuery.data}
        state={state}
        signedAt={getSignedAt(report)}
      />
    </>
  );
}

function getSignedAt(report: SignedReport): string | null {
  const signedAt = (report as { signed_at?: string | null }).signed_at;
  return signedAt ?? null;
}

/**
 * Mini-badge para listados. NO ejecuta verificación criptográfica — solo
 * indica visualmente que el reporte trae una firma adjunta. La verificación
 * real se realiza cuando el usuario abre el detalle.
 */
export function ReportSignaturePresenceDot({
  signed,
  className,
}: {
  signed: boolean;
  className?: string;
}) {
  if (!signed) {
    return (
      <span
        className={cn(
          'inline-flex items-center justify-center w-5 h-5 rounded-full bg-neutral-900 border border-neutral-700 text-neutral-600',
          className,
        )}
        aria-label="Sin firma criptográfica"
        title="Sin firma criptográfica"
      >
        <ShieldOff size={10} aria-hidden="true" />
      </span>
    );
  }
  return (
    <span
      className={cn(
        'inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-950/60 border border-emerald-500/50 text-emerald-300',
        className,
      )}
      aria-label="Reporte firmado criptográficamente. Abrir para verificar"
      title="Reporte firmado (verificación al abrir)"
    >
      <ShieldCheck size={10} aria-hidden="true" />
    </span>
  );
}
