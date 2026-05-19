'use client';

import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import {
  buildCanonicalPayload,
  isEd25519Supported,
  sha256Hex,
  verifyEd25519,
  type SignedReport,
} from '@/lib/signing';
import type {
  ReportSignatureBundle,
  RotateSigningKeyResponse,
  SignatureVerifyResponse,
  SigningPubkey,
} from '@/lib/api/types';

const ONE_HOUR = 60 * 60 * 1000;

// ---------------------------------------------------------------------------
// Public signing key — cacheada 1 hora, compartida en toda la app
// ---------------------------------------------------------------------------

export function usePublicSigningKey() {
  return useQuery<SigningPubkey>({
    queryKey: ['signing', 'pubkey'],
    queryFn: async () => {
      const { data } = await apiClient.get<SigningPubkey>('/public/signing/pubkey');
      return data;
    },
    staleTime: ONE_HOUR,
    gcTime: ONE_HOUR * 4,
    retry: 1,
  });
}

// ---------------------------------------------------------------------------
// Bundle de firma del reporte
// ---------------------------------------------------------------------------

export function useReportSignature(reportId: string | undefined) {
  return useQuery<ReportSignatureBundle>({
    queryKey: ['signing', 'report', reportId],
    queryFn: async () => {
      const { data } = await apiClient.get<ReportSignatureBundle>(
        `/reports/${reportId}/signature`,
      );
      return data;
    },
    enabled: !!reportId,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

// ---------------------------------------------------------------------------
// Verificación local
// ---------------------------------------------------------------------------

export type VerificationMode = 'local' | 'server' | 'pending';

export interface VerifyState {
  /** true / false / null mientras se calcula. */
  valid: boolean | null;
  /** En curso. */
  verifying: boolean;
  /** Mensaje de error si no se pudo verificar. */
  error: string | null;
  /** ¿El fingerprint del bundle coincide con la pubkey actual? */
  fingerprint_match: boolean | null;
  /** local = WebCrypto en navegador; server = fallback a POST /signing/verify. */
  mode: VerificationMode;
  /** sha256 del canonical payload reconstruido localmente (útil para mostrar). */
  local_payload_hash: string | null;
}

/**
 * Verifica la firma del reporte localmente con WebCrypto. Si el navegador
 * no soporta Ed25519, hace fallback al endpoint server-side.
 *
 * No se ejecuta hasta que `report`, `signatureBundle` y `pubkey` estén
 * todos disponibles y `signatureBundle.signature` no sea null.
 */
export function useVerifyReportSignature(
  report: SignedReport | undefined,
  signatureBundle: ReportSignatureBundle | undefined,
  pubkey: SigningPubkey | undefined,
): VerifyState {
  const [state, setState] = useState<VerifyState>({
    valid: null,
    verifying: false,
    error: null,
    fingerprint_match: null,
    mode: 'pending',
    local_payload_hash: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function run() {
      if (!report || !signatureBundle || !pubkey) return;
      if (!signatureBundle.signature) {
        setState({
          valid: null,
          verifying: false,
          error: null,
          fingerprint_match: null,
          mode: 'pending',
          local_payload_hash: null,
        });
        return;
      }

      setState((s) => ({ ...s, verifying: true, error: null }));

      // 1. Reconstruir canonical payload y su hash localmente
      let payload: Uint8Array;
      let localHash: string;
      try {
        payload = buildCanonicalPayload(report);
        localHash = await sha256Hex(payload);
      } catch (err) {
        if (cancelled) return;
        setState({
          valid: false,
          verifying: false,
          error:
            err instanceof Error
              ? `No se pudo construir el canonical payload: ${err.message}`
              : 'No se pudo construir el canonical payload',
          fingerprint_match: null,
          mode: 'pending',
          local_payload_hash: null,
        });
        return;
      }

      const fingerprintMatch = signatureBundle.public_key_fingerprint != null
        ? pubkey.fingerprint === signatureBundle.public_key_fingerprint
        : null;

      // 2. Intentar verificación local
      const localSupported = await isEd25519Supported();
      if (localSupported) {
        try {
          const valid = await verifyEd25519(
            pubkey.public_key_pem,
            payload,
            signatureBundle.signature,
          );
          if (cancelled) return;
          setState({
            valid,
            verifying: false,
            error: null,
            fingerprint_match: fingerprintMatch,
            mode: 'local',
            local_payload_hash: localHash,
          });
          return;
        } catch (err) {
          // Si fue ED25519_UNSUPPORTED caemos al fallback server.
          if (err instanceof Error && err.message === 'ED25519_UNSUPPORTED') {
            // continue to server fallback
          } else if (
            err instanceof Error &&
            err.message === 'INVALID_SIGNATURE_BLOB'
          ) {
            if (cancelled) return;
            setState({
              valid: false,
              verifying: false,
              error: 'Blob de firma con formato inválido',
              fingerprint_match: fingerprintMatch,
              mode: 'local',
              local_payload_hash: localHash,
            });
            return;
          } else {
            if (cancelled) return;
            setState({
              valid: false,
              verifying: false,
              error:
                err instanceof Error
                  ? err.message
                  : 'Fallo durante la verificación local',
              fingerprint_match: fingerprintMatch,
              mode: 'local',
              local_payload_hash: localHash,
            });
            return;
          }
        }
      }

      // 3. Fallback server-side
      try {
        const canonicalString = new TextDecoder('utf-8').decode(payload);
        const { data } = await apiClient.post<SignatureVerifyResponse>(
          '/public/signing/verify',
          {
            canonical_payload: canonicalString,
            signature: signatureBundle.signature,
          },
        );
        if (cancelled) return;
        setState({
          valid: data.valid,
          verifying: false,
          error: null,
          fingerprint_match: fingerprintMatch,
          mode: 'server',
          local_payload_hash: localHash,
        });
      } catch (err) {
        if (cancelled) return;
        setState({
          valid: false,
          verifying: false,
          error:
            err instanceof Error
              ? `Verificación server-side falló: ${err.message}`
              : 'Verificación server-side falló',
          fingerprint_match: fingerprintMatch,
          mode: 'server',
          local_payload_hash: localHash,
        });
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, [report, signatureBundle, pubkey]);

  return state;
}

// ---------------------------------------------------------------------------
// Admin: rotación de clave
// ---------------------------------------------------------------------------

export interface RotateSigningKeyInput {
  reason: string;
}

export function useRotateSigningKey() {
  return useMutation<RotateSigningKeyResponse, Error, RotateSigningKeyInput>({
    mutationFn: async (input) => {
      const reason = (input?.reason ?? '').trim();
      const { data } = await apiClient.post<RotateSigningKeyResponse>(
        '/classified/admin/signing/rotate',
        reason ? { reason } : {},
      );
      return data;
    },
  });
}
