import { cn } from '@/lib/utils'

type RiskLevel = 'Low' | 'Medium' | 'High' | 'Critical'

const riskConfig: Record<RiskLevel, { label: string; className: string; dotClass: string }> = {
  Low:      { label: 'LOW',      className: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20', dotClass: 'bg-emerald-400' },
  Medium:   { label: 'MEDIUM',   className: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20',   dotClass: 'bg-yellow-400' },
  High:     { label: 'HIGH',     className: 'bg-orange-500/10 text-orange-400 border border-orange-500/20',   dotClass: 'bg-orange-400' },
  Critical: { label: 'CRITICAL', className: 'bg-red-500/10 text-red-400 border border-red-500/20',           dotClass: 'bg-red-400 animate-pulse' },
}

interface RiskBadgeProps {
  level: RiskLevel
}

export function RiskBadge({ level }: RiskBadgeProps) {
  const config = riskConfig[level]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-mono font-semibold',
        config.className
      )}
      role="status"
      aria-label={`Risk level: ${level}`}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full', config.dotClass)} aria-hidden="true" />
      {config.label}
    </span>
  )
}
