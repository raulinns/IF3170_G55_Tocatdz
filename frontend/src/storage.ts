import type { Problem, RunConfig } from "./types";

export const defaultConfig: RunConfig = {
  algorithm: "steepest_ascent",
  objective: "total_value",
  seed: 42,
  max_evaluations: 50_000,
  max_sideways: 100,
  max_iterations: 10_000,
  num_restarts: 10,
  t_min: 0.001,
  calibration_samples: 100,
  population_size: 50,
  generations: 100,
  crossover_prob: 0.9,
  mutation_prob: null,
};

export function loadProblem(): Problem | null {
  try {
    const raw = localStorage.getItem("cargolab.problem");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveProblem(problem: Problem) {
  localStorage.setItem("cargolab.problem", JSON.stringify(problem));
}

export function loadConfig(): RunConfig {
  try {
    const raw = localStorage.getItem("cargolab.config");
    return raw ? { ...defaultConfig, ...JSON.parse(raw) } : defaultConfig;
  } catch {
    return defaultConfig;
  }
}

export function saveConfig(config: RunConfig) {
  localStorage.setItem("cargolab.config", JSON.stringify(config));
}

export function downloadJson(filename: string, data: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function downloadCsv(filename: string, rows: Record<string, unknown>[]) {
  const columns = Array.from(new Set(rows.flatMap((row) => Object.keys(row))));
  const escape = (value: unknown) => {
    const text = value !== null && typeof value === "object" ? JSON.stringify(value) : String(value ?? "");
    return `"${text.replaceAll('"', '""')}"`;
  };
  const csv = [columns.map(escape).join(","), ...rows.map((row) => columns.map((column) => escape(row[column])).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
