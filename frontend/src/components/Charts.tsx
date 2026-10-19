import { useEffect, useMemo, useRef, useState } from "react";
import type { Objective, Problem, State, TracePoint } from "../types";

const colors = ["#315cf4", "#e76f51", "#149f8c", "#8250df", "#d69e2e", "#1591a8", "#cf3f74"];
const faces = [[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[3,7,6],[3,6,2],[0,4,7],[0,7,3],[1,2,6],[1,6,5]];
const edges = [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];

function oriented(d: { width: number; length: number; height: number }, orientation: number) {
  const [w, l, h] = [d.width, d.length, d.height];
  return [
    { width: w, length: l, height: h }, { width: w, length: h, height: l },
    { width: l, length: w, height: h }, { width: l, length: h, height: w },
    { width: h, length: w, height: l }, { width: h, length: l, height: w },
  ][orientation] ?? d;
}

function vertices(x: number, y: number, z: number, w: number, l: number, h: number) {
  return [[x,y,z],[x+w,y,z],[x+w,y+l,z],[x,y+l,z],[x,y,z+h],[x+w,y,z+h],[x+w,y+l,z+h],[x,y+l,z+h]];
}

function edgeTrace(points: number[][], color: string, width = 3) {
  const x: (number | null)[] = [], y: (number | null)[] = [], z: (number | null)[] = [];
  edges.forEach(([a,b]) => { x.push(points[a][0], points[b][0], null); y.push(points[a][1], points[b][1], null); z.push(points[a][2], points[b][2], null); });
  return { type: "scatter3d", mode: "lines", x, y, z, line: { color, width }, hoverinfo: "skip", showlegend: false };
}

function colorFor(id: string) {
  let hash = 0;
  for (const char of id) hash = ((hash << 5) - hash + char.charCodeAt(0)) | 0;
  return colors[Math.abs(hash) % colors.length];
}

export function summarize(problem: Problem, state: State, objective: Objective) {
  const inside = state.placements.filter((p) => p.truck_id !== null);
  const packages = new Map(problem.packages.map((item) => [item.id, item]));
  const total = inside.reduce((sum, p) => sum + (packages.get(p.package_id)?.value ?? 0), 0);
  const urgency = inside.reduce((sum, p) => {
    const item = packages.get(p.package_id);
    return sum + (item ? item.value / (item.eta + 1) : 0);
  }, 0);
  return { objective: objective === "total_value" ? total : urgency, total, inside: inside.length, outside: state.placements.length - inside.length };
}

export function StateChart({ problem, state, prominent = false }: { problem: Problem; state: State; prominent?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<null | { x: number; y: number; id: string; truck: string; size: string; position: string; value: number; weight: number }>(null);
  const visualization = useMemo(() => {
    const result: any[] = [];
    const annotations: any[] = [];
    let offset = 0;
    const gap = Math.max(2, ...problem.trucks.map((t) => t.dimensions.width * 0.35));
    for (const truck of problem.trucks) {
      const d = truck.dimensions;
      result.push(edgeTrace(vertices(offset, 0, 0, d.width, d.length, d.height), "#8a94a6", 4));
      const placed = state.placements.filter((p) => p.truck_id === truck.id && p.position);
      for (const placement of placed) {
        const item = problem.packages.find((p) => p.id === placement.package_id)!;
        const size = oriented(item.dimensions, placement.orientation);
        const pos = placement.position!;
        const points = vertices(offset + pos.x, pos.y, pos.z, size.width, size.length, size.height);
        result.push({
          type: "mesh3d", x: points.map((p) => p[0]), y: points.map((p) => p[1]), z: points.map((p) => p[2]),
          i: faces.map((f) => f[0]), j: faces.map((f) => f[1]), k: faces.map((f) => f[2]),
          color: colorFor(item.id), opacity: 1, flatshading: true,
          lighting: { ambient: .72, diffuse: .7, roughness: .82, specular: .12 },
          meta: { id: item.id, truck: truck.id, size: `${size.width} × ${size.length} × ${size.height}`, position: `(${pos.x}, ${pos.y}, ${pos.z})`, value: item.value, weight: item.weight },
          hoverinfo: "none", showlegend: false,
        });
        result.push(edgeTrace(points, item.is_fragile ? "#b42318" : "#24324a", 2));
        annotations.push({
          x: offset + pos.x + size.width / 2, y: pos.y + size.length / 2, z: pos.z + size.height + .08,
          text: `<b>${item.id}</b>`, showarrow: false,
          bgcolor: "rgba(255,255,255,.68)", bordercolor: "rgba(255,255,255,.88)", borderwidth: 1, borderpad: 4,
          font: { family: "Inter, sans-serif", size: 11, color: "#171a20" },
        });
      }
      result.push({ type: "scatter3d", mode: "text", x: [offset + d.width / 2], y: [d.length / 2], z: [d.height + .5], text: [`<b>${truck.id}</b>`], hoverinfo: "skip", showlegend: false });
      offset += d.width + gap;
    }
    return { traces: result, annotations };
  }, [problem, state]);

  useEffect(() => {
    if (!ref.current || !window.Plotly) return;
    const graph = ref.current as HTMLDivElement & { on: (event: string, callback: (data?: any) => void) => void; removeListener: (event: string, callback: (data?: any) => void) => void };
    let disposed = false;
    let pointerX = 0;
    let pointerY = 0;
    const trackPointer = (event: MouseEvent) => { pointerX = event.clientX; pointerY = event.clientY; };
    graph.addEventListener("mousemove", trackPointer);
    const maxLength = Math.max(...problem.trucks.map((t) => t.dimensions.length));
    const maxHeight = Math.max(...problem.trucks.map((t) => t.dimensions.height));
    const showTooltip = (data?: any) => {
      const point = data?.points?.[0];
      const meta = point?.data?.meta;
      const pointer = data?.event ?? { clientX: pointerX, clientY: pointerY };
      if (!meta || !ref.current) return;
      const bounds = ref.current.getBoundingClientRect();
      setTooltip({
        ...meta,
        x: Math.max(10, Math.min(pointer.clientX - bounds.left + 14, bounds.width - 230)),
        y: Math.max(10, Math.min(pointer.clientY - bounds.top + 14, bounds.height - 190)),
      });
    };
    const hideTooltip = () => setTooltip(null);
    const plotReady = window.Plotly.newPlot(graph, visualization.traces, {
      autosize: true, height: prominent ? undefined : 520, margin: { l: 0, r: 0, t: 12, b: 0 }, paper_bgcolor: "rgba(0,0,0,0)",
      scene: {
        annotations: visualization.annotations,
        xaxis: { visible: false },
        yaxis: { visible: false, range: [-.5, maxLength + .5] },
        zaxis: { visible: false, range: [0, maxHeight + 1] },
        camera: { eye: { x: 1.55, y: 1.45, z: 1.05 } }, aspectmode: "data",
      },
      font: { family: "Inter, ui-sans-serif, system-ui", color: "#20242c", size: 12 }, showlegend: false,
      hoverlabel: { bgcolor: "rgba(255,255,255,.08)", bordercolor: "rgba(255,255,255,.18)", font: { family: "Inter, sans-serif", color: "#1d1d1f" } },
    }, { responsive: true, displaylogo: false, scrollZoom: true });
    Promise.resolve(plotReady).then(() => {
      if (disposed || typeof graph.on !== "function") return;
      graph.on("plotly_hover", showTooltip);
      graph.on("plotly_unhover", hideTooltip);
    }).catch(() => { if (!disposed) setTooltip(null); });
    return () => {
      disposed = true;
      graph.removeListener?.("plotly_hover", showTooltip);
      graph.removeListener?.("plotly_unhover", hideTooltip);
      graph.removeEventListener("mousemove", trackPointer);
      window.Plotly.purge(graph);
    };
  }, [problem, prominent, visualization]);
  return <div className={`state-chart-wrap plot state-plot${prominent ? " main-state-plot" : ""}`}>
    <div ref={ref} className="state-chart-canvas" aria-label="Visualisasi tiga dimensi armada" />
    {tooltip && <div className="package-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
      <strong>{tooltip.id}</strong><span>{tooltip.truck}</span>
      <dl><div><dt>Ukuran</dt><dd>{tooltip.size}</dd></div><div><dt>Koordinat</dt><dd>{tooltip.position}</dd></div><div><dt>Value</dt><dd>{tooltip.value}</dd></div><div><dt>Berat</dt><dd>{tooltip.weight}</dd></div></dl>
    </div>}
  </div>;
}

export function TrajectoryChart({ trace }: { trace: TracePoint[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || !trace.length || !window.Plotly) return;
    const data: any[] = [
      { x: trace.map((p) => p.step), y: trace.map((p) => p.objective), type: "scatter", mode: "lines", name: "Current", line: { color: "#315cf4", width: 2 } },
      { x: trace.map((p) => p.step), y: trace.map((p) => p.best_objective), type: "scatter", mode: "lines", name: "Best", line: { color: "#149f8c", width: 2, dash: "dot" } },
    ];
    if (trace.some((p) => p.population_mean_objective !== null)) data.push({ x: trace.map((p) => p.generation), y: trace.map((p) => p.population_mean_objective), type: "scatter", mode: "lines", name: "Mean population", line: { color: "#e76f51", width: 2 } });
    window.Plotly.newPlot(ref.current, data, {
      autosize: true, height: 360, margin: { l: 56, r: 16, t: 24, b: 48 }, paper_bgcolor: "#fff", plot_bgcolor: "#fff",
      xaxis: { title: "Iterasi", gridcolor: "#eceef2", zeroline: false }, yaxis: { title: "Objective", gridcolor: "#eceef2", zeroline: false },
      legend: { orientation: "h", y: 1.12 }, font: { family: "Inter, ui-sans-serif, system-ui", color: "#20242c", size: 12 },
    }, { responsive: true, displaylogo: false });
    return () => { if (ref.current) window.Plotly.purge(ref.current); };
  }, [trace]);
  if (!trace.length) return <div className="empty-state">Belum ada titik trajectory.</div>;
  return <div ref={ref} className="plot" />;
}

export function ComparisonChart({ rows, metric = "best_objective_median", axisLabel = "Objective", color = "#315cf4" }: { rows: Record<string, any>[]; metric?: string; axisLabel?: string; color?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || !rows.length || !window.Plotly) return;
    window.Plotly.newPlot(ref.current, [{
      x: rows.map((r) => r.group_label.replaceAll("_", " ")), y: rows.map((r) => r[metric]), type: "bar",
      marker: { color, line: { color: "rgba(255,255,255,.7)", width: 1 } }, hovertemplate: "%{x}<br>%{y:.3f}<extra></extra>",
    }], {
      autosize: true, height: 330, margin: { l: 58, r: 18, t: 22, b: 72 }, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      bargap: .38, xaxis: { tickangle: -16, showgrid: false, zeroline: false }, yaxis: { title: axisLabel, gridcolor: "rgba(79,89,104,.1)", zeroline: false }, showlegend: false,
      font: { family: "Inter, ui-sans-serif, system-ui", color: "#20242c", size: 12 },
    }, { responsive: true, displaylogo: false });
    return () => { if (ref.current) window.Plotly.purge(ref.current); };
  }, [axisLabel, color, metric, rows]);
  return <div ref={ref} className="plot" />;
}
