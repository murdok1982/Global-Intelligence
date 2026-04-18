interface LoadingStateProps {
  message?: string
}

export function LoadingState({ message = 'Decrypting signals...' }: LoadingStateProps) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-4 p-12"
      role="status"
      aria-live="polite"
    >
      <div className="flex gap-1" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="w-2 h-2 bg-primary rounded-full animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
      <p className="text-xs font-mono text-muted-foreground tracking-widest uppercase">{message}</p>
    </div>
  )
}
