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
}

const COLORS = [
  "hsl(186 100% 50%)",
  "hsl(0 100% 71%)",
  "hsl(258 90% 76%)",
  "hsl(142 70% 45%)",
  "hsl(38 92% 50%)",
  "hsl(330 85% 60%)",
  "hsl(215 90% 60%)",
  "hsl(55 92% 55%)",
];

function shortName(name: string, max = 22) {
  const s = name.replace(/\s+/g, " ").trim();
  if (s.length <= max) return s;
  return s.slice(0, max - 1) + "…";
}

function fmtPct(n: number) {
  return `${(n * 100).toFixed(n < 0.1 ? 1 : 0)}%`;
}

const DonutTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div className="glass-card px-3 py-2">
      <p className="text-sm font-medium mb-1">{p.name}</p>
      <p className="text-sm text-muted-foreground">
        Employment: <span className="font-medium text-foreground">{Number(p.value).toLocaleString()}</span>
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
  topListCount = 6,
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

  return (
    <div className="w-full">
      {/* Chart */}
      <div className="w-full" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip content={<DonutTooltip />} />
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

            {/* Center label */}
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
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Clean label list (instead of ugly legend) */}
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {topList.map((d, i) => (
          <div
            key={d.name}
            className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-2"
            title={d.name} // full name on hover
          >
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="h-2.5 w-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: COLORS[i % COLORS.length] }}
              />
              <span className="text-sm text-muted-foreground truncate">
                {shortName(d.name, 30)}
              </span>
            </div>
            <div className="text-sm font-medium text-foreground">
              {fmtPct(d.__pct)}
            </div>
          </div>
        ))}
      </div>

      <p className="mt-2 text-xs text-muted-foreground">
        Hover slices to see full industry name and exact employment.
      </p>
    </div>
  );
}
