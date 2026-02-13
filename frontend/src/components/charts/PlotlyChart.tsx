import Plot from "react-plotly.js";

type PlotlyFigure = { data: any[]; layout: any };

export default function PlotlyChart({
  fig,
  height = 350,
}: {
  fig: PlotlyFigure;
  height?: number;
}) {
  return (
    <Plot
      data={fig.data}
      layout={{ ...fig.layout, autosize: true, height }}
      style={{ width: "100%" }}
      useResizeHandler
      config={{ displayModeBar: false, responsive: true }}
    />
  );
}
