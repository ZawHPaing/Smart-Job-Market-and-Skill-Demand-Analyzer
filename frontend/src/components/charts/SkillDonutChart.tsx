// frontend/src/components/charts/SkillDonutChart.tsx
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
  color?: string;
};

interface SkillDonutChartProps {
  data: DonutItem[];
  height?: number;
  innerRadius?: number;
  outerRadius?: number;
  showLabels?: boolean;
  centerText?: string;
  centerSubtext?: string;
}

const SKILL_COLORS = [
  "hsl(186 100% 50%)", // cyan
  "hsl(0 0% 25%)",     // dark gray for "not requiring"
];

function fmtPercent(value: number, total: number) {
  return `${((value / total) * 100).toFixed(1)}%`;
}

const SkillTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  const total = payload[0]?.payload?.total || 1;
  
  return (
    <div className="glass-card px-3 py-2">
      <p className="text-sm font-medium mb-1">{p.name}</p>
      <p className="text-sm text-muted-foreground">
        Jobs: <span className="font-medium text-foreground">{Number(p.value).toLocaleString()}</span>
      </p>
      <p className="text-sm text-muted-foreground">
        Share: <span className="font-medium text-foreground">{fmtPercent(p.value, total)}</span>
      </p>
    </div>
  );
};

export function SkillDonutChart({
  data,
  height = 260,
  innerRadius = 70,
  outerRadius = 90,
  showLabels = false,
  centerText,
  centerSubtext,
}: SkillDonutChartProps) {
  const total = data.reduce((a, b) => a + (b.value || 0), 0) || 1;

  // Add total to each item for tooltip
  const withTotal = data.map((d) => ({
    ...d,
    total,
  }));

  return (
    <div className="w-full">
      <div className="w-full" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip content={<SkillTooltip />} />
            <Pie
              data={withTotal}
              dataKey="value"
              nameKey="name"
              innerRadius={innerRadius}
              outerRadius={outerRadius}
              paddingAngle={2}
              stroke="hsl(0 0% 18%)"
              strokeWidth={1}
              isAnimationActive
              label={showLabels ? ({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%` : false}
            >
              {data.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.color || SKILL_COLORS[index % SKILL_COLORS.length]} 
                />
              ))}
            </Pie>

            {/* Center label - only show if provided */}
            {(centerText || centerSubtext) && (
              <>
                <text
                  x="50%"
                  y="48%"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="hsl(0 0% 92%)"
                  style={{ fontSize: 24, fontWeight: 700 }}
                >
                  {centerText}
                </text>
                <text
                  x="50%"
                  y="58%"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="hsl(0 0% 65%)"
                  style={{ fontSize: 14 }}
                >
                  {centerSubtext}
                </text>
              </>
            )}
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}