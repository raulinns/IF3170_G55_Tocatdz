import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { downloadCsv, downloadJson } from "../storage";
import type { Job, Objective, Problem } from "../types";
import { ComparisonChart } from "./Charts";
import { ErrorNotice } from "./Shell";

const protocols = [
  { value: "steepest_ascent", label: "Steepest Ascent" },
  { value: "sideways", label: "Sideways" },
  { value: "stochastic", label: "Stochastic" },
  { value: "random_restart", label: "Random Restart" },
  { value: "simulated_annealing", label: "Simulated Annealing" },
  { value: "genetic_algorithm", label: "Genetic Algorithm" },
] as const;

type ExperimentResult = {
  experiment_id: string;
  experiment_dir: string;
  expected_runs: number;
  successful_runs: number;
  failed_runs: number;
  runs: Record<string, any>[];
  summary: Record<string, any>[];
};

export function ExperimentWorkspace({ currentProblem }: { currentProblem: Problem }) {
  const [dataset, setDataset] = useState("current");
  const [problem, setProblem] = useState(currentProblem);
  const [protocol, setProtocol] = useState("steepest_ascent");
  const [objective, setObjective] = useState<Objective>("total_value");
  const [seeds, setSeeds] = useState("42, 137, 2026");
  const [budget, setBudget] = useState(50_000);
  const [populationSize, setPopulationSize] = useState(50);
  const [generations, setGenerations] = useState(100);
  const [matrix, setMatrix] = useState<any>(null);
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState<Job<ExperimentResult> | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (dataset === "current") setProblem(currentProblem); }, [currentProblem, dataset]);
  useEffect(() => {
    if (!jobId) return;
    let stopped = false;
    let timer = 0;
    const poll = async () => {
      try {
        const next = await api.job<ExperimentResult>(jobId);
        if (stopped) return;
        setJob(next);
        if (next.status === "queued" || next.status === "running") timer = window.setTimeout(poll, 900);
      } catch (pollError) {
        if (!stopped) setError(pollError instanceof Error ? pollError.message : "Hasil eksperimen tidak dapat dimuat.");
      }
    };
    poll();
    return () => { stopped = true; window.clearTimeout(timer); };
  }, [jobId]);

  const resetPlan = () => { setMatrix(null); setJobId(""); setJob(null); setError(""); };
  const selectDataset = async (name: string) => {
    setDataset(name); resetPlan();
    if (name === "current") { setProblem(currentProblem); return; }
    try { setProblem(await api.fixture(name)); }
    catch (fixtureError) { setError(fixtureError instanceof Error ? fixtureError.message : "Dataset gagal dimuat."); }
  };
  const payload = () => {
    const parsedSeeds = seeds.split(",").map((item) => Number(item.trim())).filter(Number.isFinite);
    if (!parsedSeeds.length) throw new Error("Masukkan sedikitnya satu seed.");
    return { problem, protocol, objective, seeds: parsedSeeds, max_evaluations: budget, population_size: populationSize, generations };
  };
  const reviewMatrix = async () => {
    setBusy(true); setError(""); setJob(null); setJobId("");
    try { setMatrix(await api.previewExperiment(payload())); }
    catch (previewError) { setError(previewError instanceof Error ? previewError.message : "Kasus uji tidak dapat dibuat."); }
    finally { setBusy(false); }
  };
  const startExperiment = async () => {
    if (!matrix) return;
    setBusy(true); setError("");
    try {
      const { job_id } = await api.startExperiment(payload());
      setJob({ id: job_id, kind: "experiment", status: "queued", progress: 0, message: "Menyiapkan eksperimen…", result: null, error: null });
      setJobId(job_id);
    } catch (startError) { setError(startError instanceof Error ? startError.message : "Eksperimen tidak dapat dimulai."); }
    finally { setBusy(false); }
  };

  const running = job?.status === "queued" || job?.status === "running";
  const result = job?.status === "completed" ? job.result : null;
  const groups = useMemo(() => matrix ? new Set(matrix.runs.map((row: any) => row.group)).size : 0, [matrix]);
  const seedCount = useMemo(() => matrix ? new Set(matrix.runs.map((row: any) => row.seed)).size : 0, [matrix]);
  const step = result || running ? 3 : matrix ? 2 : 1;

  return <section className="experiment-workspace">
    <div className="experiment-flow" aria-label="Alur eksperimen">
      {["Input Algoritma", "Kasus Uji", "Hasil Percobaan"].map((item, index) => <div key={item} className={step >= index + 1 ? "active" : ""}><span>{index + 1}</span><strong>{item}</strong></div>)}
    </div>

    <section className="panel experiment-config-panel">
      <div className="settings-heading"><strong>Input Algoritma</strong></div>
      <div className="settings-body">
        <fieldset className="algorithm-picker" disabled={running}><legend>Algoritma</legend><div className="algorithm-options experiment-algorithm-options">
          {protocols.map((item) => <label key={item.value} className={protocol === item.value ? "active" : ""}><input type="radio" name="experiment-protocol" checked={protocol === item.value} onChange={() => { setProtocol(item.value); resetPlan(); }} /><span>{item.label}</span></label>)}
        </div></fieldset>
        <div className="form-grid four experiment-fields">
          <label><span>Dataset</span><select disabled={running} value={dataset} onChange={(event) => selectDataset(event.target.value)}><option value="current">Data dari Algoritma</option><option value="tiny">Tiny exact</option><option value="single">Single-truck constrained</option><option value="multi">Multi-truck constrained</option></select></label>
          <label><span>Objective</span><select disabled={running} value={objective} onChange={(event) => { setObjective(event.target.value as Objective); resetPlan(); }}><option value="total_value">Total value</option><option value="value_per_urgency">Value / (ETA + 1)</option></select></label>
          <label><span>Seed</span><input disabled={running} value={seeds} onChange={(event) => { setSeeds(event.target.value); resetPlan(); }} /></label>
          <label><span>Budget per run</span><input type="number" min="1" step="1000" disabled={running || protocol === "genetic_algorithm"} value={budget} onChange={(event) => { setBudget(event.currentTarget.valueAsNumber); resetPlan(); }} /></label>
        </div>
        {protocol === "genetic_algorithm" && <div className="form-grid two ga-experiment-fields">
          <label><span>Jumlah populasi</span><input type="number" min="2" step="1" disabled={running} value={populationSize} onChange={(event) => { setPopulationSize(event.currentTarget.valueAsNumber); resetPlan(); }} /></label>
          <label><span>Jumlah generasi</span><input type="number" min="1" step="1" disabled={running} value={generations} onChange={(event) => { setGenerations(event.currentTarget.valueAsNumber); resetPlan(); }} /></label>
        </div>}
        <div className="experiment-action-row"><strong>{problem.trucks.length} truk · {problem.packages.length} paket</strong><button className="button secondary" disabled={busy || running} onClick={reviewMatrix}>{busy ? "Menyiapkan…" : "Buat Kasus Uji"}</button></div>
      </div>
    </section>

    {error && <ErrorNotice message={error} />}

    {matrix && <section className="experiment-stage">
      <div className="stage-heading"><h2>Kasus Uji</h2><button className="button primary" disabled={busy || running} onClick={startExperiment}>{running ? "Eksperimen berjalan…" : "Mulai Eksperimen"}</button></div>
      <section className="panel result-overview"><div className="result-stat-grid three"><ResultStat label="Total run" value={String(matrix.run_count)} /><ResultStat label="Seed" value={String(seedCount)} /><ResultStat label="Grup" value={String(groups)} /></div></section>
      <div className="panel table-wrap matrix-table"><table className="data-table"><thead><tr><th>Kasus</th><th>Algoritma</th><th>Grup</th><th>Seed</th><th>Budget</th></tr></thead><tbody>{matrix.runs.map((row: any) => <tr key={row.case_id}><td>{row.case_id}</td><td>{pretty(row.algorithm)}</td><td>{pretty(row.group)}</td><td>{row.seed}</td><td>{row.budget.toLocaleString("id-ID")}</td></tr>)}</tbody></table></div>
    </section>}

    {running && <section className="panel experiment-progress"><div><span className="spinner" /><strong>Eksperimen sedang berjalan</strong><small>{job?.message}</small></div><div className="progress-track"><span style={{ width: `${(job?.progress ?? 0) * 100}%` }} /></div><small>{Math.round((job?.progress ?? 0) * 100)}%</small></section>}
    {job?.status === "failed" && <ErrorNotice message={job.error?.message ?? "Eksperimen gagal."} />}

    {result && <section className="experiment-result">
      <div className="stage-heading"><h2>Hasil Percobaan</h2><div className="download-row"><button className="button secondary" onClick={() => downloadCsv(`${result.experiment_id}-rekap.csv`, result.summary)}>Unduh CSV</button><button className="button quiet" onClick={() => downloadJson(`${result.experiment_id}-rekap.json`, { summary: result.summary, runs: result.runs })}>Unduh JSON</button></div></div>
      <section className="panel result-overview"><div className="result-stat-grid four"><ResultStat label="Total run" value={String(result.expected_runs)} /><ResultStat label="Berhasil" value={String(result.successful_runs)} /><ResultStat label="Gagal" value={String(result.failed_runs)} /><ResultStat label="Grup" value={String(result.summary.length)} /></div></section>
      <div className="experiment-result-grid">
        <section className="panel output-card experiment-chart"><div className="output-card-heading"><strong>Objective Median</strong></div><ComparisonChart rows={result.summary} metric="best_objective_median" axisLabel="Objective" /></section>
        <section className="panel output-card experiment-chart"><div className="output-card-heading"><strong>Durasi Median</strong></div><ComparisonChart rows={result.summary} metric="elapsed_seconds_median" axisLabel="Detik" color="#149f8c" /></section>
      </div>
      <section className="panel table-wrap result-summary-table"><table className="data-table"><thead><tr><th>Grup</th><th>Run</th><th>Berhasil</th><th>Objective min</th><th>Objective median</th><th>Objective maks</th><th>Evaluasi median</th><th>Durasi median</th></tr></thead><tbody>{result.summary.map((row) => <tr key={row.group_id}><td><strong>{pretty(row.group_label)}</strong></td><td>{row.run_count}</td><td>{row.success_count}</td><td>{number(row.best_objective_min)}</td><td>{number(row.best_objective_median)}</td><td>{number(row.best_objective_max)}</td><td>{integer(row.evaluations_median)}</td><td>{seconds(row.elapsed_seconds_median)}</td></tr>)}</tbody></table></section>
      <details className="panel run-details"><summary>Detail setiap run</summary><div className="table-wrap"><table className="data-table"><thead><tr><th>Status</th><th>Algoritma</th><th>Seed</th><th>Grup</th><th>Best objective</th><th>Evaluasi</th><th>Durasi</th></tr></thead><tbody>{result.runs.map((row) => <tr key={row.case_id}><td><span className={`status-dot ${row.status}`} />{row.status}</td><td>{pretty(row.algorithm)}</td><td>{row.seed}</td><td>{pretty(row.group_label)}</td><td>{number(row.best_objective)}</td><td>{integer(row.evaluations)}</td><td>{seconds(row.elapsed_seconds)}</td></tr>)}</tbody></table></div></details>
      <div className="result-path"><span>Disimpan di</span><code>{result.experiment_dir}</code></div>
    </section>}
  </section>;
}

function ResultStat({ label, value }: { label: string; value: string }) {
  return <div className="result-stat"><span>{label}</span><strong>{value}</strong></div>;
}

function pretty(value: unknown) { return String(value ?? "—").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function number(value: unknown) { return typeof value === "number" ? value.toLocaleString("id-ID", { maximumFractionDigits: 3 }) : "—"; }
function integer(value: unknown) { return typeof value === "number" ? value.toLocaleString("id-ID", { maximumFractionDigits: 0 }) : "—"; }
function seconds(value: unknown) { return typeof value === "number" ? `${value.toLocaleString("id-ID", { maximumFractionDigits: 3 })} s` : "—"; }
