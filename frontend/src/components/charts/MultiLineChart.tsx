import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface MultiLineChartProps {
  data: Record<string, any>[];
  lines: {
    key: string;
    name: string;
    color: string;
  }[];
  xAxisKey: string;
  height?: number;
  formatYAxis?: (value: number) => string;
  maxLines?: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="glass-card px-3 py-2">
        <p className="text-sm font-medium mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-sm flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
            <span className="text-muted-foreground">{entry.name}: </span>
            <span className="font-medium" style={{ color: entry.color }}>
              {typeof entry.value === "number"
                ? entry.value >= 1_000_000
                  ? `${(entry.value / 1_000_000).toFixed(1)}M`
                  : entry.value >= 1_000
                  ? `${(entry.value / 1_000).toFixed(0)}K`
                  : entry.value.toLocaleString()
                : entry.value}
            </span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

// Custom legend component with truncation and hover tooltips
const CustomLegend = ({ payload }: any) => {
  return (
    <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
      {payload.map((entry: any, index: number) => (
        <div
          key={`legend-${index}`}
          className="flex items-center gap-2 group"
        >
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span
            className="text-sm text-muted-foreground max-w-[150px] truncate cursor-help"
            title={entry.value} // Shows full name on hover
          >
            {entry.value}
          </span>
        </div>
      ))}
    </div>
  );
};

export function MultiLineChart({
  data,
  lines,
  xAxisKey,
  height = 300,
  formatYAxis = (v) =>
    v >= 1_000_000 ? `${v / 1_000_000}M` : v >= 1_000 ? `${v / 1_000}K` : v.toString(),
  maxLines = 6,
}: MultiLineChartProps) {
  // Deduplicate & hard-limit to maxLines
  const limitedLines = (() => {
    const seen = new Set<string>();
    const out: typeof lines = [];

    for (const l of lines || []) {
      const key = (l.key || "").trim();
      if (!key) continue;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(l);
      if (out.length >= maxLines) break;
    }
    return out;
  })();

  // Optionally, remove extra keys from data (prevents stale keys showing in tooltip/legend)
  const limitedData = (data || []).map((row) => {
    const cleaned: Record<string, any> = { ...row };
    for (const k of Object.keys(cleaned)) {
      if (k === xAxisKey) continue;
      if (!limitedLines.some((l) => l.key === k)) {
        delete cleaned[k];
      }
    }
    return cleaned;
  });

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsLineChart data={limitedData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 20%)" />
        <XAxis
          dataKey={xAxisKey}
          tick={{ fill: "hsl(0 0% 65%)", fontSize: 12 }}
          axisLine={{ stroke: "hsl(0 0% 20%)" }}
          tickLine={{ stroke: "hsl(0 0% 20%)" }}
        />
        <YAxis
          tick={{ fill: "hsl(0 0% 65%)", fontSize: 12 }}
          axisLine={{ stroke: "hsl(0 0% 20%)" }}
          tickLine={{ stroke: "hsl(0 0% 20%)" }}
          tickFormatter={formatYAxis}
        />
        <Tooltip content={<CustomTooltip />} />
        
        {/* Replace default Legend with custom one that has truncation + hover */}
        <Legend content={<CustomLegend />} />

        {limitedLines.map((line) => (
          <Line
            key={line.key}
            type="monotone"
            dataKey={line.key}
            name={line.name}
            stroke={line.color}
            strokeWidth={2}
            dot={{ fill: line.color, strokeWidth: 0, r: 4 }}
            activeDot={{ r: 6, stroke: line.color, strokeWidth: 2, fill: "hsl(0 0% 10%)" }}
            animationDuration={1500}
          />
        ))}
      </RechartsLineChart>
    </ResponsiveContainer>
  );
}