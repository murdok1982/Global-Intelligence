'use client';

import {
  ClipboardEvent,
  KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from 'react';
import { cn } from '@/lib/utils';

interface OtpInputProps {
  /** Valor actual (longitud variable; el componente acepta inputs parciales). */
  value: string;
  /** Callback con el nuevo valor (solo dígitos). */
  onChange: (next: string) => void;
  /** Disparado automáticamente cuando todas las casillas están llenas. */
  onComplete?: (value: string) => void;
  /** Número de dígitos. Por defecto 6 (TOTP estándar). */
  length?: number;
  /** Auto-focus en la primera casilla al montar. */
  autoFocus?: boolean;
  /** Desactiva la entrada. */
  disabled?: boolean;
  /** Etiqueta accesible para el grupo de inputs. */
  ariaLabel?: string;
  /** Indica que el valor actual ha fallado validación (anillo rojo). */
  invalid?: boolean;
}

/**
 * Entrada OTP de N dígitos — accesible (WCAG AA).
 *
 * Comportamiento:
 * - Sólo acepta dígitos (filtra cualquier otro carácter).
 * - Avanza el foco al rellenar cada caja; retrocede en Backspace.
 * - Pegado completo: si pegan "123456", se distribuye en todas las cajas.
 * - Flechas izquierda/derecha mueven el foco.
 * - Cuando se completa el valor, dispara `onComplete` una sola vez.
 * - Cada caja mide 48x56px (>= 44px requerido por WCAG).
 */
export function OtpInput({
  value,
  onChange,
  onComplete,
  length = 6,
  autoFocus = true,
  disabled = false,
  ariaLabel = 'Código de verificación',
  invalid = false,
}: OtpInputProps) {
  const inputsRef = useRef<Array<HTMLInputElement | null>>([]);
  const [pulse, setPulse] = useState(false);
  const completedRef = useRef(false);

  // Normaliza el valor: solo dígitos, truncado a length.
  const sanitized = value.replace(/\D/g, '').slice(0, length);
  const cells = Array.from({ length }, (_, i) => sanitized[i] ?? '');

  useEffect(() => {
    if (autoFocus && !disabled) {
      inputsRef.current[0]?.focus();
    }
  }, [autoFocus, disabled]);

  // Animación de "completado" + onComplete una vez por valor lleno.
  useEffect(() => {
    if (sanitized.length === length && !completedRef.current) {
      completedRef.current = true;
      setPulse(true);
      const timer = setTimeout(() => setPulse(false), 400);
      onComplete?.(sanitized);
      return () => clearTimeout(timer);
    }
    if (sanitized.length < length) {
      completedRef.current = false;
    }
  }, [sanitized, length, onComplete]);

  const updateAt = (index: number, digit: string) => {
    const next = cells.slice();
    next[index] = digit;
    onChange(next.join(''));
  };

  const handleChange = (index: number, raw: string) => {
    const digit = raw.replace(/\D/g, '').slice(-1); // último dígito tecleado
    if (!digit) {
      // Borrado manual de la caja
      updateAt(index, '');
      return;
    }
    updateAt(index, digit);
    // Avanzar foco
    const nextIndex = Math.min(index + 1, length - 1);
    inputsRef.current[nextIndex]?.focus();
    inputsRef.current[nextIndex]?.select();
  };

  const handleKeyDown = (index: number, event: KeyboardEvent<HTMLInputElement>) => {
    const current = cells[index] ?? '';
    if (event.key === 'Backspace') {
      if (current) {
        updateAt(index, '');
      } else if (index > 0) {
        updateAt(index - 1, '');
        inputsRef.current[index - 1]?.focus();
      }
      event.preventDefault();
      return;
    }
    if (event.key === 'ArrowLeft' && index > 0) {
      inputsRef.current[index - 1]?.focus();
      event.preventDefault();
      return;
    }
    if (event.key === 'ArrowRight' && index < length - 1) {
      inputsRef.current[index + 1]?.focus();
      event.preventDefault();
    }
  };

  const handlePaste = (event: ClipboardEvent<HTMLInputElement>) => {
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '');
    if (!pasted) return;
    event.preventDefault();
    const trimmed = pasted.slice(0, length);
    onChange(trimmed);
    const focusIndex = Math.min(trimmed.length, length - 1);
    inputsRef.current[focusIndex]?.focus();
    inputsRef.current[focusIndex]?.select();
  };

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={cn(
        'flex items-center justify-center gap-2 sm:gap-3 transition-transform',
        pulse && 'scale-[1.02]',
      )}
    >
      {cells.map((digit, i) => (
        <input
          key={i}
          ref={(el) => {
            inputsRef.current[i] = el;
          }}
          type="text"
          inputMode="numeric"
          autoComplete={i === 0 ? 'one-time-code' : 'off'}
          pattern="[0-9]*"
          maxLength={1}
          disabled={disabled}
          value={digit}
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={handlePaste}
          onFocus={(e) => e.target.select()}
          aria-label={`Dígito ${i + 1} de ${length}`}
          aria-invalid={invalid}
          className={cn(
            'w-12 h-14 text-center text-2xl font-mono tabular-nums',
            'bg-neutral-900 border rounded text-white',
            'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-neutral-950',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'transition-all duration-150',
            invalid
              ? 'border-red-500/60 focus:ring-red-500'
              : digit
                ? 'border-blue-500/60 focus:ring-blue-500'
                : 'border-neutral-700 focus:ring-blue-500',
            pulse && !invalid && 'border-emerald-500/80 ring-2 ring-emerald-500/40',
          )}
        />
      ))}
    </div>
  );
}
