'use client';

import { useState } from 'react';
import { ShieldCheck, ShieldAlert, KeyRound, Download, Copy, AlertTriangle, RefreshCw, X } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import toast from 'react-hot-toast';
import { OtpInput } from '@/components/security/OtpInput';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import {
  useMfaStatus,
  useEnrollMfa,
  useVerifyEnrollment,
  useDisableMfa,
} from '@/hooks/useMfa';
import type { MfaEnrollResponse } from '@/lib/api/types';

/**
 * Página de seguridad del usuario.
 *
 * Permite enrolar/desactivar TOTP MFA. Tras enrolar se muestran 10
 * códigos de recuperación de un solo uso. La activación efectiva exige
 * un código TOTP válido contra el secret guardado cifrado.
 */
export default function SecuritySettingsPage() {
  const { data: status, isLoading, isError, refetch } = useMfaStatus();
  const enroll = useEnrollMfa();
  const verify = useVerifyEnrollment();
  const disable = useDisableMfa();

  const [enrollData, setEnrollData] = useState<MfaEnrollResponse | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [showDisable, setShowDisable] = useState(false);

  const startEnrollment = async () => {
    try {
      const data = await enroll.mutateAsync();
      setEnrollData(data);
    } catch {
      toast.error('No se pudo iniciar el enrolamiento');
    }
  };

  const confirmEnrollment = async () => {
    if (verifyCode.length !== 6) return;
    try {
      await verify.mutateAsync({ code: verifyCode });
      toast.success('MFA activado correctamente');
      setEnrollData(null);
      setVerifyCode('');
    } catch {
      toast.error('Código inválido. Reintente.');
      setVerifyCode('');
    }
  };

  const cancelEnrollment = () => {
    setEnrollData(null);
    setVerifyCode('');
  };

  const confirmDisable = async () => {
    if (disableCode.length !== 6) return;
    try {
      await disable.mutateAsync({ code: disableCode });
      toast.success('MFA desactivado');
      setShowDisable(false);
      setDisableCode('');
    } catch {
      toast.error('Código inválido');
      setDisableCode('');
    }
  };

  const copyRecovery = (codes: string[]) => {
    navigator.clipboard.writeText(codes.join('\n'));
    toast.success('Códigos copiados al portapapeles');
  };

  const downloadRecovery = (codes: string[]) => {
    const blob = new Blob(
      [
        '# Global Intelligence — Códigos de recuperación MFA\n',
        '# Guarde este archivo en un lugar seguro y offline.\n',
        '# Cada código es de un solo uso.\n\n',
        ...codes.map((c) => `${c}\n`),
      ],
      { type: 'text/plain' },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'gi-recovery-codes.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8 animate-in fade-in">
      <div className="flex justify-between items-end border-b border-neutral-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-widest text-white uppercase">
            Seguridad de la cuenta
          </h1>
          <p className="text-neutral-500 mt-1 uppercase text-xs tracking-widest">
            Autenticación de doble factor
          </p>
        </div>
      </div>

      {isError && (
        <ErrorState
          message="No se pudo cargar el estado MFA"
          onRetry={() => refetch()}
        />
      )}

      {isLoading && <Skeleton className="h-32 rounded" />}

      {status && !enrollData && !showDisable && (
        <div className="border border-neutral-800 rounded p-6 bg-neutral-950">
          <div className="flex items-start gap-4">
            {status.enrolled ? (
              <ShieldCheck className="w-8 h-8 text-emerald-400 flex-shrink-0 mt-1" />
            ) : (
              <ShieldAlert className="w-8 h-8 text-amber-400 flex-shrink-0 mt-1" />
            )}
            <div className="flex-1">
              <h2 className="text-lg font-bold tracking-wider uppercase text-white">
                {status.enrolled ? 'MFA activo' : 'MFA inactivo'}
              </h2>
              <p className="text-neutral-400 text-sm mt-1">
                {status.enrolled
                  ? `Autenticador TOTP enrolado. ${status.recovery_codes_remaining} códigos de recuperación restantes.`
                  : 'El acceso al perímetro clasificado requiere activar la autenticación de doble factor.'}
              </p>
            </div>
            <div>
              {status.enrolled ? (
                <button
                  onClick={() => setShowDisable(true)}
                  className="px-4 py-2 text-xs uppercase tracking-widest font-bold text-red-300 border border-red-500/40 hover:bg-red-500/10 rounded transition"
                >
                  Desactivar MFA
                </button>
              ) : (
                <button
                  onClick={startEnrollment}
                  disabled={enroll.isPending}
                  className="px-4 py-2 text-xs uppercase tracking-widest font-bold text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/10 rounded transition disabled:opacity-50"
                >
                  {enroll.isPending ? 'Generando…' : 'Activar MFA'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {enrollData && (
        <div className="border border-emerald-500/40 rounded p-6 bg-neutral-950 space-y-6">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-lg font-bold tracking-wider uppercase text-emerald-300">
                Paso 1 — Escanea el código QR
              </h2>
              <p className="text-neutral-400 text-sm mt-1">
                Use una app TOTP (Authy, Google Authenticator, 1Password, Aegis).
              </p>
            </div>
            <button
              onClick={cancelEnrollment}
              className="text-neutral-500 hover:text-white"
              aria-label="Cancelar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex flex-col md:flex-row gap-6 items-center md:items-start">
            <div className="bg-white p-3 rounded">
              <QRCodeSVG value={enrollData.provisioning_uri} size={192} level="M" />
            </div>
            <div className="flex-1 space-y-3">
              <p className="text-xs text-neutral-500 uppercase tracking-widest">
                Entrada manual
              </p>
              <code className="block break-all text-sm bg-neutral-900 border border-neutral-800 rounded px-3 py-2 font-mono">
                {enrollData.secret_b32}
              </code>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(enrollData.secret_b32);
                  toast.success('Secret copiado');
                }}
                className="text-xs uppercase tracking-widest text-emerald-300 hover:underline"
              >
                <Copy className="w-3 h-3 inline mr-1" /> Copiar secret
              </button>
            </div>
          </div>

          <div className="border-t border-neutral-800 pt-6 space-y-4">
            <h2 className="text-lg font-bold tracking-wider uppercase text-emerald-300">
              Paso 2 — Códigos de recuperación
            </h2>
            <p className="text-neutral-400 text-sm">
              Guarde estos {enrollData.recovery_codes.length} códigos en un lugar seguro y offline.
              Cada uno es de un solo uso. Si pierde el autenticador serán su única vía de acceso.
            </p>
            <div className="grid grid-cols-2 gap-2 font-mono text-sm bg-neutral-900 border border-neutral-800 rounded p-4">
              {enrollData.recovery_codes.map((code, i) => (
                <div key={i} className="text-neutral-300">
                  <span className="text-neutral-600 mr-2">{String(i + 1).padStart(2, '0')}.</span>
                  {code}
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => downloadRecovery(enrollData.recovery_codes)}
                className="px-3 py-2 text-xs uppercase tracking-widest font-bold text-neutral-200 border border-neutral-700 hover:border-neutral-500 rounded transition"
              >
                <Download className="w-3 h-3 inline mr-1" /> Descargar .txt
              </button>
              <button
                onClick={() => copyRecovery(enrollData.recovery_codes)}
                className="px-3 py-2 text-xs uppercase tracking-widest font-bold text-neutral-200 border border-neutral-700 hover:border-neutral-500 rounded transition"
              >
                <Copy className="w-3 h-3 inline mr-1" /> Copiar todos
              </button>
            </div>
          </div>

          <div className="border-t border-neutral-800 pt-6 space-y-4">
            <h2 className="text-lg font-bold tracking-wider uppercase text-emerald-300">
              Paso 3 — Confirmar con código TOTP
            </h2>
            <p className="text-neutral-400 text-sm">
              Introduzca el código de 6 dígitos que muestra su autenticador.
            </p>
            <OtpInput value={verifyCode} onChange={setVerifyCode} />
            <button
              onClick={confirmEnrollment}
              disabled={verifyCode.length !== 6 || verify.isPending}
              className="w-full md:w-auto px-6 py-3 text-sm uppercase tracking-widest font-bold text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/10 rounded transition disabled:opacity-50"
            >
              {verify.isPending ? 'Verificando…' : 'Confirmar y activar MFA'}
            </button>
          </div>
        </div>
      )}

      {showDisable && (
        <div className="border border-red-500/40 rounded p-6 bg-neutral-950 space-y-4">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-lg font-bold tracking-wider uppercase text-red-300 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                Desactivar MFA
              </h2>
              <p className="text-neutral-400 text-sm mt-1">
                Esta acción reducirá la seguridad de su cuenta y revocará el acceso al perímetro clasificado.
                Introduzca un código TOTP para confirmar.
              </p>
            </div>
            <button
              onClick={() => {
                setShowDisable(false);
                setDisableCode('');
              }}
              className="text-neutral-500 hover:text-white"
              aria-label="Cancelar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <OtpInput value={disableCode} onChange={setDisableCode} />
          <button
            onClick={confirmDisable}
            disabled={disableCode.length !== 6 || disable.isPending}
            className="px-6 py-3 text-sm uppercase tracking-widest font-bold text-red-300 border border-red-500/40 hover:bg-red-500/10 rounded transition disabled:opacity-50"
          >
            <KeyRound className="w-4 h-4 inline mr-2" />
            {disable.isPending ? 'Desactivando…' : 'Confirmar desactivación'}
          </button>
        </div>
      )}

      <div className="border border-neutral-800 rounded p-6 bg-neutral-950">
        <h2 className="text-sm font-bold tracking-wider uppercase text-neutral-300 flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          WebAuthn / FIDO2
        </h2>
        <p className="text-neutral-500 text-xs mt-2">
          La autenticación con clave de seguridad física (YubiKey, Titan, Solo) está disponible
          como vía de doble factor adicional. Esta funcionalidad será habilitada en una próxima fase.
        </p>
      </div>
    </div>
  );
}
