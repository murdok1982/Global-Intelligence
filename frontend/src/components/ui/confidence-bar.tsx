import { cn } from '@/lib/utils'

interface ConfidenceBarProps {
  score: number
}

export function ConfidenceBar({ score }: ConfidenceBarProps) {
  const percentage = Math.round(score * 100)
  const colorClass =
    percentage >= 80
      ? 'bg-emerald-500'
      : percentage >= 60
        ? 'bg-yellow-500'
        : 'bg-red-500'

  return (
    <div
      className="flex items-center gap-2"
      role="meter"
      aria-valuenow={percentage}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Confidence: ${percentage}%`}
    >
      <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', colorClass)}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs font-mono text-muted-foreground w-8 text-right">{percentage}%</span>
    </div>
  )
}
