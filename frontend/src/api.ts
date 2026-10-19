import type { Job, Objective, Problem, RunConfig } from "./types";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => `${item.loc?.slice(-2).join(" → ")}: ${item.msg}`).join("\n")
      : detail || `Request gagal (${response.status})`;
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

export const api = {
  example: () => request<Problem>("/api/problems/example"),
  fixture: (name: string) => request<Problem>(`/api/problems/fixtures/${name}`),
  validate: (problem: Problem, seed: number, objective: Objective) =>
    request<any>("/api/problems/validate", {
      method: "POST",
      body: JSON.stringify({ problem, seed, objective }),
    }),
  startRun: (problem: Problem, config: RunConfig, persist_artifacts: boolean) =>
    request<{ job_id: string }>("/api/runs", {
      method: "POST",
      body: JSON.stringify({ problem, config, persist_artifacts }),
    }),
  job: <T>(id: string) => request<Job<T>>(`/api/jobs/${id}`),
  reference: (problem: Problem, objective: Objective, candidate_value: number) =>
    request<any>("/api/references", {
      method: "POST",
      body: JSON.stringify({ problem, objective, candidate_value }),
    }),
  previewExperiment: (payload: Record<string, unknown>) =>
    request<any>("/api/experiments/preview", { method: "POST", body: JSON.stringify(payload) }),
  startExperiment: (payload: Record<string, unknown>) =>
    request<{ job_id: string }>("/api/experiments", { method: "POST", body: JSON.stringify(payload) }),
};
