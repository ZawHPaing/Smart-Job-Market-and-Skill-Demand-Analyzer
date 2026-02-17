import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

type DonutItem = {
  name: string;
  value: number;
};

interface DonutChartProps {
  data: DonutItem[];
  height?: number;
  topListCount?: number; // how many labels to show under chart
  context?: 'industry' | 'skill' | 'default'; // Add context to determine what text to show
  showSubtitle?: boolean; // Control subtitle visibility
  showHoverText?: boolean; // Control hover instruction text visibility
  showCenterTotal?: boolean; // Control center total text visibility
}

const COLORS = [
  "hsl(186 100% 50%)", // cyan
  "hsl(0 100% 71%)",   // coral/red
  "hsl(258 90% 76%)",  // purple
  "hsl(142 70% 45%)",  // green
  "hsl(38 92% 50%)",   // amber/orange
  "hsl(330 85% 60%)",  // pink
  "hsl(215 90% 60%)",  // blue
  "hsl(55 92% 55%)",   // yellow
  "hsl(280 70% 65%)",  // lavender
  "hsl(190 90% 55%)",  // teal
  "hsl(350 80% 65%)",  // rose
  "hsl(120 60% 50%)",  // forest green
];

function shortName(name: string, max = 22) {
  const s = name.replace(/\s+/g, " ").trim();
  if (s.length <= max) return s;
  return s.slice(0, max - 1) + "…";
}

function fmtPct(n: number) {
  return `${(n * 100).toFixed(n < 0.1 ? 1 : 0)}%`;
}

const DonutTooltip = ({ active, payload, context = 'default' }: any) => {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  
  // Different tooltip content based on context
  const getValueLabel = () => {
    switch(context) {
      case 'skill':
        return 'Jobs:';
      case 'industry':
        return 'Employment:';
      default:
        return 'Value:';
    }
  };

  return (
    <div className="glass-card px-3 py-2">
      <p className="text-sm font-medium mb-1">{p.name}</p>
      <p className="text-sm text-muted-foreground">
        {getValueLabel()} <span className="font-medium text-foreground">{Number(p.value).toLocaleString()}</span>
      </p>
      <p className="text-sm text-muted-foreground">
        Share: <span className="font-medium text-foreground">{fmtPct(p.payload?.__pct ?? 0)}</span>
      </p>
    </div>
  );
};

export function DonutChart({
  data,
  height = 260,
  topListCount = 10,
  context = 'default',
  showSubtitle = true,
  showHoverText = true,
  showCenterTotal = true,
}: DonutChartProps) {
  const total = data.reduce((a, b) => a + (b.value || 0), 0) || 1;

  // add pct to each item for tooltip + list
  const withPct = data.map((d) => ({
    ...d,
    __pct: (d.value || 0) / total,
  }));

  // list under chart = sorted top N
  const topList = [...withPct]
    .sort((a, b) => (b.value || 0) - (a.value || 0))
    .slice(0, topListCount);

  // Split into two columns for display
  const midPoint = Math.ceil(topList.length / 2);
  const leftColumn = topList.slice(0, midPoint);
  const rightColumn = topList.slice(midPoint);

  // Get the appropriate subtitle text based on context
  const getSubtitleText = () => {
    switch(context) {
      case 'skill':
        return `Showing top ${topList.length} categories by job count`;
      case 'industry':
        return `Showing top ${topList.length} industries by employment`;
      default:
        return `Showing top ${topList.length} items by value`;
    }
  };

  // Get the appropriate hover text based on context
  const getHoverText = () => {
    switch(context) {
      case 'skill':
        return "Hover slices to see exact job counts.";
      case 'industry':
        return "Hover slices to see full industry name and exact employment.";
      default:
        return "Hover slices to see details.";
    }
  };

  return (
    <div className="w-full">
      {/* Chart */}
      <div className="w-full" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip content={<DonutTooltip context={context} />} />
            <Pie
              data={withPct}
              dataKey="value"
              nameKey="name"
              innerRadius="62%"
              outerRadius="88%"
              paddingAngle={2}
              stroke="hsl(0 0% 18%)"
              strokeWidth={1}
              isAnimationActive
            >
              {withPct.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>

            {/* Center label - conditionally shown */}
            {showCenterTotal && (
              <>
                <text
                  x="50%"
                  y="48%"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="hsl(0 0% 92%)"
                  style={{ fontSize: 14, fontWeight: 700 }}
                >
                  Total
                </text>
                <text
                  x="50%"
                  y="58%"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="hsl(0 0% 65%)"
                  style={{ fontSize: 12 }}
                >
                  {total >= 1_000_000
                    ? `${(total / 1_000_000).toFixed(1)}M`
                    : total.toLocaleString()}
                </text>
              </>
            )}
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Double column label list */}
      <div className="mt-3">
        <div className="grid grid-cols-2 gap-3">
          {/* Left Column */}
          <div className="space-y-2">
            {leftColumn.map((d, idx) => {
              const originalIndex = topList.findIndex(item => item.name === d.name);
              return (
                <div
                  key={d.name}
                  className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                  title={d.name}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className="h-2.5 w-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: COLORS[originalIndex % COLORS.length] }}
                    />
                    <span className="text-sm text-muted-foreground truncate">
                      {shortName(d.name, 25)}
                    </span>
                  </div>
                  <div className="text-sm font-medium text-foreground whitespace-nowrap ml-2">
                    {fmtPct(d.__pct)}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right Column */}
          <div className="space-y-2">
            {rightColumn.map((d, idx) => {
              const originalIndex = topList.findIndex(item => item.name === d.name);
              return (
                <div
                  key={d.name}
                  className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                  title={d.name}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className="h-2.5 w-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: COLORS[originalIndex % COLORS.length] }}
                    />
                    <span className="text-sm text-muted-foreground truncate">
                      {shortName(d.name, 25)}
                    </span>
                  </div>
                  <div className="text-sm font-medium text-foreground whitespace-nowrap ml-2">
                    {fmtPct(d.__pct)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Context-specific subtitle - conditionally shown */}
        {showSubtitle && topList.length > 0 && (
          <p className="mt-3 text-xs text-muted-foreground text-center">
            {getSubtitleText()}
          </p>
        )}
      </div>

      {/* Hover instruction text - conditionally shown */}
      {showHoverText && (
        <p className="mt-2 text-xs text-muted-foreground">
          {getHoverText()}
        </p>
      )}
    </div>
  );
}