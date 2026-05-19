'use client';

import { useState } from 'react';
import {
  KeyRound,
  ShieldCheck,
  AlertTriangle,
  Copy,
  Download,
  RotateCw,
  Archive,
} from 'lucide-react';
import {
  usePublicSigningKey,
  useRotateSigningKey,
} from '@/hooks/useReportSignature';
import { ErrorState } from '@/components/ui/error-state';
import toast from 'react-hot-toast';

/**
 * Centro de gestión de la clave de firma institucional.
 *
 * Acciones:
 *  - Visualizar la pubkey activa y su fingerprint.
 *  - Descargar la pubkey en PEM.
 *  - Rotar la clave (doble confirmación + razón obligatoria).
 *
 * NOTA: el endpoint /admin/signing/archive aún no existe en el backend.
 * Cuando se exponga, esta página mostrará el histórico completo.
 */
export default function SigningAdminPage() {
  const pubkeyQuery = usePublicSigningKey();
  const rotateMutation = useRotateSigningKey();

  const [showRotateDialog, setShowRotateDialog] = useState(false);
  const [confirmText, setConfirmText] = useState('');
  const [reason, setReason] = useState('');
  const [stage, setStage] = useState<1 | 2>(1);
  const [rotatedResult, setRotatedResult] = useState<
    | {
        new_fingerprint: string;
        archived_old_fingerprint: string | null;
        public_key_pem: string;
      }
    | null
  >(null);

  const handleStartRotate = () => {
    setStage(1);
    setConfirmText('');
    setReason('');
    setShowRotateDialog(true);
    setRotatedResult(null);
  };

  const handleNextStage = () => {
    if (!reason.trim()) {
      toast.error('Debe indicar la razón de la rotación.');
      return;
    }
    setStage(2);
  };

  const handleConfirmRotate = async () => {
    if (confirmText !== 'ROTAR') {
      toast.error("Escriba 'ROTAR' para confirmar.");
      return;
    }
    try {
      const result = await rotateMutation.mutateAsync({ reason });
      setRotatedResult(result);
      toast.success('Clave rotada con éxito.');
      pubkeyQuery.refetch();
    } catch (err) {
      toast.error(
        err instanceof Error
          ? `Falló la rotación: ${err.message}`
          : 'Falló la rotación de la clave.',
      );
    }
  };

  const handleCloseDialog = () => {
    setShowRotateDialog(false);
    setStage(1);
    setConfirmText('');
    setReason('');
  };

  const handleCopyPem = async (pem: string) => {
    try {
      await navigator.clipboard.writeText(pem);
      toast.success('PEM copiado al portapapeles.');
    } catch {
      toast.error('No se pudo copiar.');
    }
  };

  const handleDownloadPem = (pem: string, fingerprint: string) => {
    const blob = new Blob([pem], { type: 'application/x-pem-file' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `signing-pubkey-${fingerprint}.pem`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8 animate-in fade-in">
      <header className="border-b border-neutral-800 pb-4 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-widest text-white uppercase flex items-center gap-3">
            <KeyRound className="w-6 h-6 text-blue-400" />
            Clave de firma institucional
          </h1>
          <p className="text-neutral-500 mt-1 uppercase text-xs tracking-widest">
            Ed25519 · gestión y rotación
          </p>
        </div>
        <button
          type="button"
          onClick={handleStartRotate}
          disabled={rotateMutation.isPending}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs uppercase tracking-widest font-bold text-red-200 bg-red-950/40 border border-red-500/40 hover:bg-red-900/40 rounded transition min-h-[44px] disabled:opacity-50"
        >
          <RotateCw className="w-4 h-4" />
          Rotar clave de firma
        </button>
      </header>

      {pubkeyQuery.isError && (
        <ErrorState
          message="No se pudo obtener la clave pública activa"
          onRetry={() => pubkeyQuery.refetch()}
        />
      )}

      {pubkeyQuery.isLoading && (
        <div className="space-y-3">
          <SkeletonRow />
          <SkeletonRow />
          <SkeletonRow />
        </div>
      )}

      {pubkeyQuery.data && (
        <section className="space-y-4">
          <div className="border border-emerald-500/30 bg-emerald-950/20 rounded p-4 flex items-start gap-3">
            <ShieldCheck className="w-5 h-5 text-emerald-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-emerald-200 uppercase tracking-widest text-xs font-bold">
                Clave activa
              </p>
              <p className="text-neutral-300 text-sm mt-1 font-mono">
                Algoritmo: {pubkeyQuery.data.algorithm}
              </p>
              <p className="text-neutral-300 text-sm font-mono break-all">
                Fingerprint:{' '}
                <span className="text-emerald-300">
                  {pubkeyQuery.data.fingerprint}
                </span>
              </p>
            </div>
          </div>

          <div className="border border-neutral-800 bg-neutral-950 rounded">
            <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-800">
              <span className="text-xs uppercase tracking-widest text-neutral-400">
                Public key PEM
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleCopyPem(pubkeyQuery.data.public_key_pem)}
                  className="text-neutral-400 hover:text-white text-[10px] uppercase tracking-widest inline-flex items-center gap-1 px-2 py-1 min-h-[36px]"
                  aria-label="Copiar PEM al portapapeles"
                >
                  <Copy size={12} /> Copiar
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleDownloadPem(
                      pubkeyQuery.data.public_key_pem,
                      pubkeyQuery.data.fingerprint,
                    )
                  }
                  className="text-neutral-400 hover:text-white text-[10px] uppercase tracking-widest inline-flex items-center gap-1 px-2 py-1 min-h-[36px]"
                  aria-label="Descargar PEM"
                >
                  <Download size={12} /> Descargar
                </button>
              </div>
            </div>
            <pre className="p-4 text-[11px] text-neutral-300 font-mono break-all whitespace-pre-wrap max-h-64 overflow-y-auto">
              {pubkeyQuery.data.public_key_pem}
            </pre>
          </div>

          <div className="border border-neutral-800 bg-neutral-950 rounded p-4">
            <h2 className="text-xs uppercase tracking-widest text-neutral-400 mb-2 flex items-center gap-2">
              <Archive size={12} /> Claves archivadas
            </h2>
            <p className="text-neutral-500 text-xs">
              El listado histórico de claves rotadas aún no está expuesto por
              el backend. Cuando se exponga el endpoint
              <code className="mx-1 px-1 bg-neutral-800 rounded font-mono">
                /admin/signing/archive
              </code>
              esta sección mostrará el detalle. TODO.
            </p>
          </div>

          {rotatedResult && (
            <div
              role="status"
              aria-live="polite"
              className="border border-blue-500/40 bg-blue-950/30 rounded p-4 space-y-3"
            >
              <p className="text-blue-200 uppercase tracking-widest text-xs font-bold flex items-center gap-2">
                <ShieldCheck className="w-4 h-4" /> Nueva clave activa
              </p>
              <p className="text-neutral-300 text-sm font-mono break-all">
                Nuevo fingerprint:{' '}
                <span className="text-blue-300">
                  {rotatedResult.new_fingerprint}
                </span>
              </p>
              {rotatedResult.archived_old_fingerprint && (
                <p className="text-neutral-400 text-xs font-mono break-all">
                  Clave anterior archivada:{' '}
                  {rotatedResult.archived_old_fingerprint}
                </p>
              )}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleCopyPem(rotatedResult.public_key_pem)}
                  className="text-blue-200 border border-blue-500/40 hover:bg-blue-900/40 text-[11px] uppercase tracking-widest inline-flex items-center gap-1 px-3 py-2 rounded min-h-[40px]"
                >
                  <Copy size={12} /> Copiar nueva PEM
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleDownloadPem(
                      rotatedResult.public_key_pem,
                      rotatedResult.new_fingerprint,
                    )
                  }
                  className="text-blue-200 border border-blue-500/40 hover:bg-blue-900/40 text-[11px] uppercase tracking-widest inline-flex items-center gap-1 px-3 py-2 rounded min-h-[40px]"
                >
                  <Download size={12} /> Descargar
                </button>
              </div>
              <p className="text-neutral-400 text-xs">
                Distribuya este PEM a todos los clientes externos que verifiquen
                firmas. Los reportes firmados con la clave anterior siguen
                verificándose si el cliente conserva la clave archivada.
              </p>
            </div>
          )}
        </section>
      )}

      {showRotateDialog && (
        <RotateDialog
          stage={stage}
          reason={reason}
          confirmText={confirmText}
          onReason={setReason}
          onConfirmText={setConfirmText}
          onNext={handleNextStage}
          onCancel={handleCloseDialog}
          onConfirm={handleConfirmRotate}
          pending={rotateMutation.isPending}
        />
      )}
    </div>
  );
}

function SkeletonRow() {
  return <div className="h-14 rounded bg-neutral-900 animate-pulse" />;
}

// ---------------------------------------------------------------------------
// Diálogo de doble confirmación
// ---------------------------------------------------------------------------

function RotateDialog({
  stage,
  reason,
  confirmText,
  onReason,
  onConfirmText,
  onNext,
  onCancel,
  onConfirm,
  pending,
}: {
  stage: 1 | 2;
  reason: string;
  confirmText: string;
  onReason: (s: string) => void;
  onConfirmText: (s: string) => void;
  onNext: () => void;
  onCancel: () => void;
  onConfirm: () => void;
  pending: boolean;
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="rotate-dialog-title"
      className="fixed inset-0 z-[80] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
      onClick={onCancel}
    >
      <div
        className="bg-neutral-950 border border-red-500/40 rounded-lg shadow-2xl max-w-lg w-full overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="px-5 py-4 border-b border-red-500/30 bg-red-950/20 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <h2
            id="rotate-dialog-title"
            className="text-sm font-bold uppercase tracking-widest text-red-200"
          >
            Rotación de clave de firma — paso {stage} de 2
          </h2>
        </header>

        <div className="px-5 py-5 space-y-4 text-sm">
          {stage === 1 && (
            <>
              <p className="text-neutral-300 normal-case">
                Está a punto de rotar la clave Ed25519 institucional. Todos los
                reportes firmados con la clave anterior seguirán siendo
                verificables siempre que la clave archivada se distribuya a
                los clientes.
              </p>
              <label
                htmlFor="rotate-reason"
                className="block text-xs uppercase tracking-widest text-neutral-400"
              >
                Razón (obligatoria, queda en auditoría)
              </label>
              <textarea
                id="rotate-reason"
                value={reason}
                onChange={(e) => onReason(e.target.value)}
                placeholder="Ej: rotación anual programada, compromiso sospechado, cambio de operador…"
                className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-sm text-white font-mono min-h-[100px]"
                required
              />
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={onCancel}
                  className="px-4 py-2 text-xs uppercase tracking-widest text-neutral-400 border border-neutral-700 rounded hover:bg-neutral-900 min-h-[40px]"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={onNext}
                  className="px-4 py-2 text-xs uppercase tracking-widest font-bold text-red-200 border border-red-500/40 bg-red-950/40 rounded hover:bg-red-900/40 min-h-[40px]"
                >
                  Continuar
                </button>
              </div>
            </>
          )}

          {stage === 2 && (
            <>
              <p className="text-red-300 uppercase tracking-widest text-xs font-bold">
                Confirmación final
              </p>
              <p className="text-neutral-300 normal-case">
                Escriba la palabra{' '}
                <span className="font-mono font-bold text-red-300">ROTAR</span>{' '}
                para proceder. La acción se registra en el log de auditoría
                inmutable con el evento{' '}
                <code className="bg-neutral-800 px-1 rounded text-amber-300 font-mono">
                  signing.key.rotated
                </code>
                .
              </p>
              <label htmlFor="rotate-confirm" className="sr-only">
                Confirmar rotación escribiendo ROTAR
              </label>
              <input
                id="rotate-confirm"
                type="text"
                value={confirmText}
                onChange={(e) => onConfirmText(e.target.value)}
                placeholder="ROTAR"
                className="w-full bg-neutral-900 border border-red-500/40 rounded px-3 py-2 text-sm text-white font-mono uppercase tracking-widest"
                autoComplete="off"
                spellCheck={false}
              />
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={onCancel}
                  className="px-4 py-2 text-xs uppercase tracking-widest text-neutral-400 border border-neutral-700 rounded hover:bg-neutral-900 min-h-[40px]"
                  disabled={pending}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={onConfirm}
                  disabled={pending || confirmText !== 'ROTAR'}
                  className="px-4 py-2 text-xs uppercase tracking-widest font-bold text-red-100 bg-red-700/60 border border-red-500/70 rounded hover:bg-red-700/80 disabled:opacity-40 min-h-[40px]"
                >
                  {pending ? 'Rotando…' : 'Rotar clave ahora'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
