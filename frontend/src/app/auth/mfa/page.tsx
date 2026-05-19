'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ShieldCheck, KeyRound, AlertTriangle, ArrowLeft } from 'lucide-react';
import toast from 'react-hot-toast';
import { useQueryClient } from '@tanstack/react-query';
import { OtpInput } from '@/components/security/OtpInput';
import { useMfaChallenge } from '@/hooks/useMfa';
import {
  MFA_CHALLENGE_EXPIRES_KEY,
  MFA_CHALLENGE_STORAGE_KEY,
  persistAuthTokens,
} from '@/hooks/useAuth';

type Mode = 'totp' | 'recovery';

function formatRemaining(ms: number): string {
  if (ms <= 0) return '0:00';
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export default function MfaChallengePage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-neutral-950 flex items-center justify-center p-4">
          <p className="text-neutral-500 font-mono text-xs uppercase tracking-widest">
            Cargando desafío…
          </p>
        </main>
      }
    >
      <MfaChallengeInner />
    </Suspense>
  );
}

function MfaChallengeInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const challenge = useMfaChallenge();

  const [challengeToken, setChallengeToken] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [now, setNow] = useState<number>(() => Date.now());
  const [mode, setMode] = useState<Mode>('totp');
  const [code, setCode] = useState('');
  const [recoveryCode, setRecoveryCode] = useState('');
  const [invalid, setInvalid] = useState(false);

  // Recuperar challenge_token (query string > sessionStorage)
  useEffect(() => {
    const fromQuery = searchParams.get('challenge_token');
    if (fromQuery) {
      setChallengeToken(fromQuery);
      const exp = searchParams.get('expires_in');
      const ttl = exp ? Number(exp) * 1000 : 300 * 1000;
      setExpiresAt(Date.now() + ttl);
      return;
    }
    if (typeof window !== 'undefined') {
      const stored = sessionStorage.getItem(MFA_CHALLENGE_STORAGE_KEY);
      const storedExpires = sessionStorage.getItem(MFA_CHALLENGE_EXPIRES_KEY);
      if (!stored) {
        router.replace('/auth');
        return;
      }
      setChallengeToken(stored);
      setExpiresAt(storedExpires ? Number(storedExpires) : Date.now() + 300 * 1000);
    }
  }, [router, searchParams]);

  // Tick del countdown
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const remaining = expiresAt ? expiresAt - now : 0;
  const isExpired = expiresAt !== null && remaining <= 0;
  const expirePercent = useMemo(() => {
    if (!expiresAt) return 100;
    const total = 300 * 1000;
    return Math.max(0, Math.min(100, (remaining / total) * 100));
  }, [expiresAt, remaining]);

  // Al expirar → limpiar y volver al login
  useEffect(() => {
    if (isExpired) {
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem(MFA_CHALLENGE_STORAGE_KEY);
        sessionStorage.removeItem(MFA_CHALLENGE_EXPIRES_KEY);
      }
      toast.error('El desafío ha expirado. Inicia sesión de nuevo.');
      router.replace('/auth');
    }
  }, [isExpired, router]);

  const submit = async () => {
    if (!challengeToken) return;
    setInvalid(false);
    try {
      const tokens = await challenge.mutateAsync(
        mode === 'totp'
          ? { challenge_token: challengeToken, code }
          : { challenge_token: challengeToken, recovery_code: recoveryCode.trim() },
      );
      persistAuthTokens(tokens);
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem(MFA_CHALLENGE_STORAGE_KEY);
        sessionStorage.removeItem(MFA_CHALLENGE_EXPIRES_KEY);
      }
      queryClient.invalidateQueries({ queryKey: ['me'] });
      toast.success('Verificación correcta');
      router.replace('/dashboard');
    } catch (err) {
      setInvalid(true);
      const message =
        err instanceof Error ? err.message : 'Código inválido';
      toast.error(message);
    }
  };

  const canSubmit =
    !!challengeToken &&
    !challenge.isPending &&
    !isExpired &&
    (mode === 'totp' ? code.length === 6 : recoveryCode.trim().length >= 8);

  return (
    <main className="min-h-screen bg-neutral-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded bg-blue-600/10 border border-blue-500/20 mb-6">
            <ShieldCheck size={28} className="text-blue-500" aria-hidden="true" />
          </div>
          <h1 className="text-2xl font-light tracking-widest text-white uppercase">
            Verificación en dos pasos
          </h1>
          <p className="text-neutral-500 font-mono text-xs mt-2 uppercase tracking-widest">
            {mode === 'totp'
              ? 'Introduzca el código de su aplicación autenticadora'
              : 'Introduzca un código de recuperación'}
          </p>
        </div>

        {/* Countdown */}
        <div
          className="mb-6 border border-neutral-800 rounded p-3 bg-neutral-900/50"
          role="status"
          aria-live="polite"
        >
          <div className="flex justify-between items-center font-mono text-[10px] uppercase tracking-widest text-neutral-500 mb-2">
            <span>Tiempo restante</span>
            <span
              className={
                remaining < 30_000
                  ? 'text-red-400 tabular-nums'
                  : 'text-neutral-300 tabular-nums'
              }
            >
              {formatRemaining(remaining)}
            </span>
          </div>
          <div
            className="w-full h-1 bg-neutral-800 rounded overflow-hidden"
            aria-hidden="true"
          >
            <div
              className={
                remaining < 30_000
                  ? 'h-full bg-red-500 transition-all duration-1000'
                  : 'h-full bg-blue-500 transition-all duration-1000'
              }
              style={{ width: `${expirePercent}%` }}
            />
          </div>
        </div>

        {/* Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (canSubmit) submit();
          }}
          className="space-y-6"
        >
          {mode === 'totp' ? (
            <div>
              <label
                className="block font-mono text-[10px] uppercase tracking-widest text-neutral-500 mb-3 text-center"
              >
                Código de 6 dígitos
              </label>
              <OtpInput
                value={code}
                onChange={(v) => {
                  setInvalid(false);
                  setCode(v);
                }}
                onComplete={() => {
                  /* el usuario aún pulsa "Verificar" */
                }}
                invalid={invalid}
                disabled={challenge.isPending || isExpired}
              />
            </div>
          ) : (
            <div>
              <label
                htmlFor="recovery-code"
                className="block font-mono text-[10px] uppercase tracking-widest text-neutral-500 mb-2"
              >
                Código de recuperación
              </label>
              <input
                id="recovery-code"
                type="text"
                autoComplete="one-time-code"
                value={recoveryCode}
                onChange={(e) => {
                  setInvalid(false);
                  setRecoveryCode(e.target.value);
                }}
                placeholder="XXXX-XXXX-XXXX"
                disabled={challenge.isPending || isExpired}
                aria-invalid={invalid}
                className="w-full bg-neutral-900 border border-neutral-700 rounded p-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono tracking-widest"
              />
            </div>
          )}

          {challenge.isError && (
            <div
              role="alert"
              className="flex items-center gap-3 p-3 bg-red-500/10 border border-red-500/20 rounded"
            >
              <AlertTriangle size={14} className="text-red-500 flex-shrink-0" />
              <p className="text-red-400 font-mono text-xs">
                Código incorrecto o desafío caducado.
              </p>
            </div>
          )}

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full py-3 bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 hover:text-blue-300 border border-blue-600/30 rounded font-mono text-xs uppercase tracking-widest transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 min-h-[44px]"
          >
            {challenge.isPending ? (
              <>
                <div className="w-3 h-3 border border-blue-500 border-t-transparent rounded-full animate-spin" />
                Verificando…
              </>
            ) : (
              <>
                <KeyRound size={14} />
                Verificar
              </>
            )}
          </button>
        </form>

        {/* Toggle entre TOTP y recovery */}
        <div className="mt-6 text-center space-y-2">
          {mode === 'totp' ? (
            <button
              type="button"
              onClick={() => {
                setMode('recovery');
                setCode('');
                setInvalid(false);
              }}
              className="text-neutral-500 hover:text-neutral-300 transition-colors font-mono text-[11px] uppercase tracking-widest underline-offset-4 hover:underline"
            >
              Usar código de recuperación
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                setMode('totp');
                setRecoveryCode('');
                setInvalid(false);
              }}
              className="text-neutral-500 hover:text-neutral-300 transition-colors font-mono text-[11px] uppercase tracking-widest underline-offset-4 hover:underline inline-flex items-center gap-2"
            >
              <ArrowLeft size={12} aria-hidden="true" />
              Volver al código TOTP
            </button>
          )}
        </div>

        <p className="text-center text-neutral-600 font-mono text-[10px] uppercase tracking-widest mt-8">
          Transmisión cifrada · TLS 1.3
        </p>
      </div>
    </main>
  );
}
