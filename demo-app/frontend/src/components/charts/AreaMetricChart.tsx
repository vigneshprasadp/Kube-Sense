import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface AreaMetricChartProps {
  data: any[];
  dataKey: string;
  label?: string;
  color?: string;
  secondKey?: string;
  secondColor?: string;
  height?: number;
  xKey?: string;
  unit?: string;
}

export function AreaMetricChart({
  data,
  dataKey,
  label,
  color = '#0D9488',
  secondKey,
  secondColor = '#06B6D4',
  height = 220,
  xKey = 'name',
  unit = '',
}: AreaMetricChartProps) {
  return (
    <div>
      {label && <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-3">{label}</p>}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id={`grad-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.18} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
            {secondKey && (
              <linearGradient id={`grad-${secondKey}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={secondColor} stopOpacity={0.15} />
                <stop offset="100%" stopColor={secondColor} stopOpacity={0.02} />
              </linearGradient>
            )}
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
          <XAxis dataKey={xKey} tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={false} tickLine={false} unit={unit} />
          <Tooltip
            contentStyle={{ background: 'rgba(255,255,255,0.96)', border: '1px solid #E2E8F0', borderRadius: 12, fontSize: 12 }}
            labelStyle={{ color: '#475569', fontWeight: 600 }}
          />
          <Area type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2.5} fill={`url(#grad-${dataKey})`} dot={false} activeDot={{ r: 4, fill: color }} />
          {secondKey && (
            <Area type="monotone" dataKey={secondKey} stroke={secondColor} strokeWidth={2.5} fill={`url(#grad-${secondKey})`} dot={false} activeDot={{ r: 4, fill: secondColor }} />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
