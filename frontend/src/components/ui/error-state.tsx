import { AlertTriangle } from 'lucide-react';

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center gap-4 p-8 text-center">
      <AlertTriangle size={32} className="text-red-500/60" />
      <p className="text-red-400 font-mono text-sm uppercase tracking-widest">
        {message}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-neutral-900 border border-neutral-700 text-neutral-400 hover:text-white hover:border-neutral-500 transition-colors font-mono text-xs uppercase tracking-widest rounded"
        >
          Retry
        </button>
      )}
    </div>
  );
}
