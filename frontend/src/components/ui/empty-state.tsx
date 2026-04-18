interface EmptyStateProps {
  title: string
  description?: string
  icon?: string
}

export function EmptyState({ title, description, icon = '○' }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 p-12 text-center">
      <span className="text-4xl opacity-20 font-mono" aria-hidden="true">{icon}</span>
      <p className="text-sm font-mono font-semibold text-muted-foreground uppercase tracking-widest">{title}</p>
      {description && (
        <p className="text-xs text-muted-foreground max-w-xs">{description}</p>
      )}
    </div>
  )
}
