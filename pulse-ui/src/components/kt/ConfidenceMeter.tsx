import { RadialBarChart, RadialBar, PolarAngleAxis } from 'recharts'

interface Props {
  confidence: number  // 0.0 – 1.0
  size?: number
}

function getColor(confidence: number): string {
  if (confidence >= 0.82) return '#22c55e'  // green
  if (confidence >= 0.60) return '#f59e0b'  // amber
  return '#3b82f6'                           // blue
}

function getLabel(confidence: number): string {
  if (confidence >= 0.90) return 'Excellent'
  if (confidence >= 0.82) return 'Confident'
  if (confidence >= 0.65) return 'Learning'
  if (confidence >= 0.40) return 'Exploring'
  return 'Just started'
}

export function ConfidenceMeter({ confidence, size = 140 }: Props) {
  const pct = Math.round(confidence * 100)
  const color = getColor(confidence)
  const label = getLabel(confidence)

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative">
        <RadialBarChart
          width={size}
          height={size}
          cx={size / 2}
          cy={size / 2}
          innerRadius={size * 0.35}
          outerRadius={size * 0.48}
          data={[{ value: pct, fill: color }]}
          startAngle={180}
          endAngle={0}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar
            background={{ fill: '#1e293b' }}
            dataKey="value"
            cornerRadius={size * 0.04}
            angleAxisId={0}
          />
        </RadialBarChart>

        {/* Center text */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center"
          style={{ paddingTop: size * 0.08 }}
        >
          <span className="text-2xl font-bold" style={{ color, lineHeight: 1 }}>
            {pct}%
          </span>
        </div>
      </div>

      <div className="text-center">
        <p className="text-xs font-medium" style={{ color }}>{label}</p>
        <p className="text-[10px] text-slate-500 mt-0.5">Confidence</p>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-slate-800 rounded-full h-1.5 mt-1">
        <div
          className="h-1.5 rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  )
}
