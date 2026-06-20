import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

const RefLine = ReferenceLine as any;

interface LineMetricChartProps {
  data: any[];
  dataKey: string;
  predKey?: string;
  threshold?: number;
  color?: string;
  predColor?: string;
  height?: number;
  xKey?: string;
}

export function LineMetricChart({
  data,
  dataKey,
  predKey,
  threshold,
  color = '#0D9488',
  predColor = '#7C3AED',
  height = 200,
  xKey = 'time',
}: LineMetricChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
        <XAxis dataKey={xKey} tick={{ fontSize: 9, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 9, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ background: 'rgba(255,255,255,0.96)', border: '1px solid #E2E8F0', borderRadius: 10, fontSize: 11 }}
        />
        {threshold !== undefined && (
          <RefLine y={threshold} stroke="#DC2626" strokeDasharray="4 3" strokeWidth={1.5}
            label={{ value: 'Limit', fill: '#DC2626', fontSize: 9, position: 'insideTopRight' }}
          />
        )}
        <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} name="Observed" />
        {predKey && (
          <Line type="monotone" dataKey={predKey} stroke={predColor} strokeWidth={2.5} strokeDasharray="6 4" dot={false} name="Predicted" />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
