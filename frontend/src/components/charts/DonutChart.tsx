import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';

interface DonutChartProps {
  data: {
    name: string;
    value: number;
    color?: string;
  }[];
  innerRadius?: number;
  outerRadius?: number;
  showLabels?: boolean;
}

const COLORS = [
  'hsl(186 100% 50%)',  // cyan
  'hsl(0 100% 71%)',    // coral
  'hsl(258 90% 76%)',   // purple
  'hsl(142 76% 45%)',   // green
  'hsl(38 92% 50%)',    // amber
  'hsl(200 80% 60%)',   // blue
  'hsl(330 80% 60%)',   // pink
  'hsl(60 80% 50%)',    // yellow
];

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="glass-card px-3 py-2">
        <p className="text-sm font-medium">{data.name}</p>
        <p className="text-lg font-bold text-cyan">
          {data.value.toLocaleString()}
        </p>
      </div>
    );
  }
  return null;
};

export function DonutChart({
  data,
  innerRadius = 60,
  outerRadius = 100,
  showLabels = true,
}: DonutChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={innerRadius}
          outerRadius={outerRadius}
          paddingAngle={2}
          dataKey="value"
          animationBegin={0}
          animationDuration={1000}
        >
          {data.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.color || COLORS[index % COLORS.length]}
              stroke="transparent"
              className="transition-all duration-300 hover:opacity-80"
            />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        {showLabels && (
          <Legend
            verticalAlign="bottom"
            iconType="circle"
            iconSize={8}
            formatter={(value) => (
              <span className="text-sm text-muted-foreground">{value}</span>
            )}
          />
        )}
      </PieChart>
    </ResponsiveContainer>
  );
}
