export type Dimensions = { width: number; length: number; height: number };
export type Truck = { id: string; dimensions: Dimensions; max_capacity: number };
export type Package = {
  id: string;
  dimensions: Dimensions;
  value: number;
  weight: number;
  is_fragile: boolean;
  eta: number;
};
export type Problem = { trucks: Truck[]; packages: Package[] };

export type Algorithm =
  | "steepest_ascent"
  | "sideways"
  | "stochastic"
  | "random_restart"
  | "simulated_annealing"
  | "genetic_algorithm";
export type Objective = "total_value" | "value_per_urgency";

export type RunConfig = {
  algorithm: Algorithm;
  objective: Objective;
  seed: number;
  max_evaluations: number;
  max_sideways: number;
  max_iterations: number;
  num_restarts: number;
  t_min: number;
  calibration_samples: number;
  population_size: number;
  generations: number;
  crossover_prob: number;
  mutation_prob: number | null;
};

export type Placement = {
  package_id: string;
  truck_id: string | null;
  position: { x: number; y: number; z: number } | null;
  orientation: number;
};
export type State = { placements: Placement[] };
export type TracePoint = {
  step: number;
  evaluations: number;
  objective: number;
  best_objective: number;
  temperature: number | null;
  delta: number | null;
  accept_prob: number | null;
  random_draw: number | null;
  accepted: boolean | null;
  generation: number | null;
  stuck: boolean | null;
  population_mean_objective: number | null;
  sideways_moves: number | null;
  restart: number | null;
  iteration_in_restart: number | null;
};
export type SearchResult = {
  algorithm: Algorithm;
  objective: Objective;
  seed: number;
  evaluations_used: number;
  stopped_reason: string;
  initial_state: State;
  initial_objective: number;
  best_state: State;
  best_objective: number;
  final_state: State;
  final_objective: number;
  trace: TracePoint[];
  config: RunConfig;
};
export type CompletedRun = {
  run_id: string;
  started_at: string;
  elapsed_seconds: number;
  artifact_dir: string | null;
  config: RunConfig;
  metrics: Record<string, any>;
  result: SearchResult;
  problem: Problem;
};
export type Job<T = unknown> = {
  id: string;
  kind: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  message: string;
  result: T | null;
  error: { type: string; message: string } | null;
};

declare global {
  interface Window {
    Plotly: {
      newPlot: (element: HTMLElement, data: any[], layout?: Record<string, any>, config?: Record<string, any>) => Promise<void>;
      purge: (element: HTMLElement) => void;
      Plots: { resize: (element: HTMLElement) => void };
    };
  }
}
