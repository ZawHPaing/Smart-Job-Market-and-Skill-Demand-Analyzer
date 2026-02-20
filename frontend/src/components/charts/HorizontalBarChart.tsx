import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface HorizontalBarChartProps {
  data: {
    name: string;
    value: number;
    secondaryValue?: number;
    color?: string;
  }[];
  showSecondary?: boolean;
  primaryLabel?: string;
  secondaryLabel?: string;
  formatValue?: (value: number) => string;
  formatSecondary?: (value: number) => string;
  maxValue?: number; // ADD THIS LINE
}

const COLORS = [
  "hsl(186 100% 50%)",
  "hsl(0 100% 71%)",
  "hsl(258 90% 76%)",
  "hsl(142 76% 45%)",
  "hsl(38 92% 50%)",
  "hsl(200 80% 60%)",
];

const CustomTooltip = ({ active, payload, formatValue, formatSecondary }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="glass-card px-3 py-2">
        <p className="text-sm font-medium mb-1">{data.name}</p>
        <p className="text-sm">
          <span className="text-muted-foreground">Postings: </span>
          <span className="font-medium text-cyan">
            {formatValue ? formatValue(data.value) : data.value.toLocaleString()}
          </span>
        </p>
        {data.secondaryValue && (
          <p className="text-sm">
            <span className="text-muted-foreground">Salary: </span>
            <span className="font-medium text-coral">
              {formatSecondary
                ? formatSecondary(data.secondaryValue)
                : `$${data.secondaryValue.toLocaleString()}`}
            </span>
          </p>
        )}
      </div>
    );
  }
  return null;
};

export function HorizontalBarChart({
  data,
  showSecondary = false,
  primaryLabel = "Postings",
  secondaryLabel = "Salary",
  formatValue = (v) => v.toLocaleString(),
  formatSecondary = (v) => `$${(v / 1000).toFixed(0)}K`,
  maxValue, // ADD THIS LINE
}: HorizontalBarChartProps) {
  // REPLACE THIS LINE:
  // const maxValue = Math.max(...data.map((d) => d.value));
  
  // WITH THESE LINES:
  const calculatedMaxValue = maxValue !== undefined ? maxValue : Math.max(...data.map((d) => d.value));

  return (
    <div className="space-y-3">
      {data.map((item, index) => (
        <div key={`${item.name}-${index}`} className="group">
          <div className="flex items-center justify-between mb-1">
            {/* ✅ Truncated, but full title appears on hover */}
            <span
              className="text-sm font-medium truncate max-w-[200px] cursor-help"
              title={item.name}
              aria-label={item.name}
            >
              {item.name}
            </span>

            <div className="flex items-center gap-3 text-sm">
              <span className="text-cyan font-medium">{formatValue(item.value)}</span>
              {showSecondary && item.secondaryValue !== undefined && item.secondaryValue !== null && (
                <span className="text-coral font-medium">{formatSecondary(item.secondaryValue)}</span>
              )}
            </div>
          </div>

          <div className="relative h-6 bg-secondary/50 rounded-lg overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 rounded-lg transition-all duration-700 ease-out group-hover:opacity-90"
              style={{
                // REPLACE THIS LINE:
                // width: `${(item.value / maxValue) * 100}%`,
                // WITH THIS LINE:
                width: `${(item.value / calculatedMaxValue) * 100}%`,
                background: `linear-gradient(90deg, ${COLORS[index % COLORS.length]}, ${
                  COLORS[index % COLORS.length]
                }80)`,
              }}
            />

            {showSecondary && item.secondaryValue !== undefined && item.secondaryValue !== null && (
              <div
                className="absolute inset-y-0 rounded-lg border-2 border-coral/60 bg-transparent"
                style={{
                  left: 0,
                  width: `${(item.secondaryValue / 250000) * 100}%`,
                }}
              />
            )}
          </div>
        </div>
      ))}

      {/* Legend */}
      <div className="flex items-center justify-end gap-4 pt-2">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-cyan" />
          <span className="text-xs text-muted-foreground">{primaryLabel}</span>
        </div>
        {showSecondary && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full border-2 border-coral" />
            <span className="text-xs text-muted-foreground">{secondaryLabel}</span>
          </div>
        )}
      </div>
    </div>
  );
}