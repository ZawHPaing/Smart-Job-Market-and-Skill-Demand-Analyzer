import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface StackedBarChartProps {
  data: Record<string, any>[];
  bars: { key: string; name: string; color: string }[];
  xAxisKey: string;
  height?: number;

  /**
   * If you pass:
   *   labelKey="industryLabel"
   *   tooltipLabelKey="industry"
   * then X axis shows short labels, tooltip shows full industry.
   */
  labelKey?: string;
  tooltipLabelKey?: string;
}

const fmtAxis = (v: number) =>
  v >= 1_000_000 ? `${(v / 1_000_000).toFixed(0)}M` : v >= 1_000 ? `${(v / 1_000).toFixed(0)}K` : `${v}`;

const CustomTooltip =
  ({ tooltipLabelKey }: { tooltipLabelKey?: string }) =>
  ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;

    // prefer full label from the row if available
    const row = payload?.[0]?.payload;
    const title = tooltipLabelKey && row?.[tooltipLabelKey] ? row[tooltipLabelKey] : label;

    return (
      <div className="glass-card px-3 py-2 max-w-[360px]">
        <p className="text-sm font-medium mb-2 break-words">{title}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-sm flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
            <span className="text-muted-foreground">{entry.name}: </span>
            <span className="font-medium" style={{ color: entry.color }}>
              {Number(entry.value || 0).toLocaleString()}
            </span>
          </p>
        ))}
      </div>
    );
  };

export function StackedBarChart({
  data,
  bars,
  xAxisKey,
  height = 300,
  labelKey,
  tooltipLabelKey,
}: StackedBarChartProps) {
  const axisKey = labelKey || xAxisKey;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 20%)" />

        {/* ✅ clean axis labels */}
        <XAxis
          dataKey={axisKey}
          interval={0}
          tick={false}
          axisLine={false}
          tickLine={false}
        />

        <YAxis
          tick={{ fill: "hsl(0 0% 65%)", fontSize: 12 }}
          axisLine={{ stroke: "hsl(0 0% 20%)" }}
          tickLine={{ stroke: "hsl(0 0% 20%)" }}
          tickFormatter={(v) => fmtAxis(Number(v))}
        />

        <Tooltip content={CustomTooltip({ tooltipLabelKey }) as any} />

        <Legend
          verticalAlign="bottom"
          iconType="circle"
          iconSize={8}
          formatter={(value) => <span className="text-sm text-muted-foreground">{value}</span>}
        />

        {bars.map((bar, index) => (
          <Bar
            key={bar.key}
            dataKey={bar.key}
            name={bar.name}
            stackId="stack"
            fill={bar.color}
            radius={index === bars.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]}
            animationDuration={700}
          />
        ))}
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}
