'use client';

import { useState } from 'react';
import {
  X,
  Copy,
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  KeyRound,
  FileLock2,
  Link2,
} from 'lucide-react';
import type {
  ReportSignatureBundle,
  SigningPubkey,
} from '@/lib/api/types';
import type { VerifyState } from '@/hooks/useReportSignature';
import { cn } from '@/lib/utils';

interface ReportSignatureModalProps {
  open: boolean;
  onClose: () => void;
  bundle: ReportSignatureBundle | undefined;
  pubkey: SigningPubkey | undefined;
  state: VerifyState;
  signedAt?: string | null;
}

type Tab = 'summary' | 'technical' | 'trust';

/**
 * Modal con detalles de la firma del reporte:
 * - Resumen: estado de verificación, fecha de firma, fingerprint.
 * - Verificación técnica: hash, firma base64, pubkey PEM.
 * - Cadena de confianza: explicación + alerta si la pubkey fue rotada.
 */
export function ReportSignatureModal({
  open,
  onClose,
  bundle,
  pubkey,
  state,
  signedAt,
}: ReportSignatureModalProps) {
  const [tab, setTab] = useState<Tab>('summary');

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="signature-modal-title"
      className="fixed inset-0 z-[80] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-neutral-950 border border-neutral-800 rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-800 px-6 py-4">
          <h2
            id="signature-modal-title"
            className="text-sm font-bold tracking-widest text-white uppercase flex items-center gap-2"
          >
            <FileLock2 size={16} className="text-blue-400" />
            Firma criptográfica del reporte
          </h2>
          <button
            onClick={onClose}
            aria-label="Cerrar modal"
            className="text-neutral-500 hover:text-white transition-colors w-10 h-10 flex items-center justify-center"
          >
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <nav
          className="flex border-b border-neutral-800 px-6"
          role="tablist"
          aria-label="Secciones de la firma"
        >
          <TabButton active={tab === 'summary'} onClick={() => setTab('summary')}>
            Resumen
          </TabButton>
          <TabButton
            active={tab === 'technical'}
            onClick={() => setTab('technical')}
          >
            Verificación técnica
          </TabButton>
          <TabButton active={tab === 'trust'} onClick={() => setTab('trust')}>
            Cadena de confianza
          </TabButton>
        </nav>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5 text-sm text-neutral-300 font-mono">
          {tab === 'summary' && (
            <SummaryTab
              bundle={bundle}
              pubkey={pubkey}
              state={state}
              signedAt={signedAt}
            />
          )}
          {tab === 'technical' && (
            <TechnicalTab bundle={bundle} pubkey={pubkey} state={state} />
          )}
          {tab === 'trust' && (
            <TrustTab bundle={bundle} pubkey={pubkey} state={state} />
          )}
        </div>
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        'px-4 py-3 text-xs uppercase tracking-widest font-bold border-b-2 transition-colors min-h-[44px]',
        active
          ? 'text-blue-400 border-blue-500'
          : 'text-neutral-500 border-transparent hover:text-neutral-300',
      )}
    >
      {children}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Summary tab
// ---------------------------------------------------------------------------

function SummaryTab({
  bundle,
  pubkey,
  state,
  signedAt,
}: {
  bundle: ReportSignatureBundle | undefined;
  pubkey: SigningPubkey | undefined;
  state: VerifyState;
  signedAt?: string | null;
}) {
  if (!bundle?.signature) {
    return (
      <div className="space-y-3">
        <StatusRow
          icon={<ShieldQuestion size={18} className="text-amber-400" />}
          label="Estado"
          value="Sin firmar"
          tone="amber"
        />
        <p className="text-neutral-500 text-xs leading-relaxed normal-case font-sans">
          Este reporte no tiene firma digital adjunta. No se puede garantizar
          su integridad ni su procedencia institucional.
        </p>
      </div>
    );
  }

  const verdict = renderVerdict(state);

  return (
    <div className="space-y-3">
      <StatusRow
        icon={verdict.icon}
        label="Estado de la firma"
        value={verdict.label}
        tone={verdict.tone}
      />
      <StatusRow
        icon={<KeyRound size={16} className="text-neutral-400" />}
        label="Algoritmo"
        value={pubkey?.algorithm ?? 'Ed25519'}
      />
      <StatusRow
        icon={<FileLock2 size={16} className="text-neutral-400" />}
        label="Fingerprint del firmante"
        value={
          bundle.public_key_fingerprint ?? '(no provisto por el backend)'
        }
        mono
      />
      <StatusRow
        icon={<KeyRound size={16} className="text-neutral-400" />}
        label="Fingerprint pubkey activa"
        value={pubkey?.fingerprint ?? '(pubkey no disponible)'}
        mono
      />
      {signedAt && (
        <StatusRow
          icon={<Link2 size={16} className="text-neutral-400" />}
          label="Firmado el"
          value={formatDate(signedAt)}
          mono
        />
      )}
      <StatusRow
        icon={<ShieldCheck size={16} className="text-neutral-400" />}
        label="Modo de verificación"
        value={
          state.mode === 'local'
            ? 'WebCrypto local (Ed25519 nativo)'
            : state.mode === 'server'
              ? 'Server-side (browser sin Ed25519)'
              : 'En curso'
        }
      />
      {state.error && (
        <div
          role="alert"
          className="border border-red-500/40 bg-red-500/10 rounded p-3 text-xs text-red-300 normal-case font-sans"
        >
          {state.error}
        </div>
      )}
    </div>
  );
}

function StatusRow({
  icon,
  label,
  value,
  tone,
  mono,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone?: 'green' | 'red' | 'amber';
  mono?: boolean;
}) {
  const toneClass =
    tone === 'green'
      ? 'text-emerald-300'
      : tone === 'red'
        ? 'text-red-300'
        : tone === 'amber'
          ? 'text-amber-300'
          : 'text-neutral-200';
  return (
    <div className="flex items-start gap-3 border border-neutral-800 bg-neutral-900/40 rounded px-3 py-2.5">
      <span className="mt-0.5 flex-shrink-0">{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="text-[10px] uppercase tracking-widest text-neutral-500 mb-1">
          {label}
        </p>
        <p className={cn('text-sm break-all', toneClass, mono && 'font-mono')}>
          {value}
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Technical tab
// ---------------------------------------------------------------------------

function TechnicalTab({
  bundle,
  pubkey,
  state,
}: {
  bundle: ReportSignatureBundle | undefined;
  pubkey: SigningPubkey | undefined;
  state: VerifyState;
}) {
  if (!bundle) {
    return (
      <p className="text-neutral-500 text-xs normal-case font-sans">
        Sin información técnica disponible.
      </p>
    );
  }
  return (
    <div className="space-y-4">
      <DataBlock
        label="Canonical payload hash (server)"
        value={bundle.canonical_payload_hash}
      />
      <DataBlock
        label="Canonical payload hash (local)"
        value={state.local_payload_hash ?? '(no calculado)'}
      />
      <DataBlock
        label="Firma (base64, truncada)"
        value={truncateMiddle(bundle.signature ?? '', 80)}
        copyValue={bundle.signature ?? ''}
      />
      <DataBlock
        label="Public key PEM (truncada)"
        value={truncateMiddle(pubkey?.public_key_pem ?? '', 240)}
        copyValue={pubkey?.public_key_pem}
        multiline
      />
      {state.local_payload_hash &&
        bundle.canonical_payload_hash !== state.local_payload_hash && (
          <div
            role="alert"
            className="border border-red-500/40 bg-red-500/10 rounded p-3 text-xs text-red-300 normal-case font-sans"
          >
            ATENCIÓN: el hash del canonical payload recalculado en el cliente
            no coincide con el del backend. Esto puede indicar un cambio en el
            formato canónico o adulteración del documento.
          </div>
        )}
    </div>
  );
}

function DataBlock({
  label,
  value,
  copyValue,
  multiline,
}: {
  label: string;
  value: string;
  copyValue?: string;
  multiline?: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    if (!copyValue) return;
    try {
      await navigator.clipboard.writeText(copyValue);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // no-op
    }
  };
  return (
    <div className="border border-neutral-800 bg-neutral-900/40 rounded">
      <div className="flex items-center justify-between px-3 py-2 border-b border-neutral-800">
        <span className="text-[10px] uppercase tracking-widest text-neutral-400">
          {label}
        </span>
        {copyValue && (
          <button
            type="button"
            onClick={handleCopy}
            className="text-neutral-500 hover:text-white transition-colors flex items-center gap-1 text-[10px] uppercase tracking-widest min-h-[36px] px-2"
            aria-label={`Copiar ${label}`}
          >
            <Copy size={12} />
            {copied ? 'Copiado' : 'Copiar'}
          </button>
        )}
      </div>
      <pre
        className={cn(
          'p-3 text-[11px] text-neutral-300 font-mono break-all whitespace-pre-wrap',
          multiline ? 'max-h-40 overflow-y-auto' : '',
        )}
      >
        {value || '(vacío)'}
      </pre>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Trust tab
// ---------------------------------------------------------------------------

function TrustTab({
  bundle,
  pubkey,
  state,
}: {
  bundle: ReportSignatureBundle | undefined;
  pubkey: SigningPubkey | undefined;
  state: VerifyState;
}) {
  const rotated =
    bundle?.public_key_fingerprint &&
    pubkey?.fingerprint &&
    bundle.public_key_fingerprint !== pubkey.fingerprint;

  return (
    <div className="space-y-4 text-sm normal-case font-sans leading-relaxed">
      <p className="text-neutral-300">
        La verificación se realizó comparando el reporte recibido contra la
        clave pública institucional obtenida del endpoint público
        <code className="px-1 mx-1 bg-neutral-800 rounded text-blue-300 font-mono text-xs">
          /api/v1/public/signing/pubkey
        </code>
        . La clave pública es no-secreta — su distribución abierta no
        compromete el sistema.
      </p>
      <p className="text-neutral-400 text-xs">
        El cliente reconstruyó el canonical payload (mismo formato JSON
        ordenado que el backend) y verificó la firma Ed25519
        {state.mode === 'local'
          ? ' localmente usando WebCrypto del navegador.'
          : state.mode === 'server'
            ? ' delegando al endpoint server-side porque el navegador no expone Ed25519 en WebCrypto.'
            : '.'}
      </p>

      {rotated && (
        <div
          role="alert"
          className="border border-amber-500/40 bg-amber-500/10 rounded p-3 text-amber-200"
        >
          <p className="text-xs font-bold uppercase tracking-widest mb-1">
            Firma con clave anterior
          </p>
          <p className="text-xs">
            Este reporte fue firmado con una clave previa
            <code className="px-1 mx-1 bg-amber-950 rounded font-mono">
              {bundle?.public_key_fingerprint}
            </code>
            distinta de la activa
            <code className="px-1 mx-1 bg-amber-950 rounded font-mono">
              {pubkey?.fingerprint}
            </code>
            . Si la firma es válida, el documento conserva su autenticidad
            histórica pre-rotación. Si su entorno no archiva la clave
            antigua, la verificación local mostrará firma inválida — en ese
            caso solicite la clave archivada al administrador.
          </p>
        </div>
      )}

      <ul className="text-xs text-neutral-500 list-disc pl-5 space-y-1">
        <li>Algoritmo: Ed25519 (RFC 8032).</li>
        <li>Codificación de clave: PEM PKCS#8 SubjectPublicKeyInfo.</li>
        <li>
          Hash de payload: SHA-256 sobre el JSON canónico con
          <code className="mx-1 bg-neutral-800 rounded px-1 font-mono">
            sort_keys=True
          </code>
          y separadores ajustados.
        </li>
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function renderVerdict(state: VerifyState): {
  icon: React.ReactNode;
  label: string;
  tone: 'green' | 'red' | 'amber';
} {
  if (state.verifying || state.mode === 'pending') {
    return {
      icon: <ShieldQuestion size={18} className="text-blue-300" />,
      label: 'Verificando…',
      tone: 'amber',
    };
  }
  if (state.valid === true) {
    return {
      icon: <ShieldCheck size={18} className="text-emerald-400" />,
      label: 'Firma verificada — documento auténtico',
      tone: 'green',
    };
  }
  if (state.valid === false) {
    return {
      icon: <ShieldAlert size={18} className="text-red-400" />,
      label: 'FIRMA INVÁLIDA — documento adulterado',
      tone: 'red',
    };
  }
  return {
    icon: <ShieldQuestion size={18} className="text-amber-400" />,
    label: 'Estado desconocido',
    tone: 'amber',
  };
}

function truncateMiddle(s: string, maxLen: number): string {
  if (!s || s.length <= maxLen) return s;
  const half = Math.floor((maxLen - 3) / 2);
  return `${s.slice(0, half)}…${s.slice(-half)}`;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  } catch {
    return iso;
  }
}
