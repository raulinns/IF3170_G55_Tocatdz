import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { StateChart, summarize, TrajectoryChart } from "../components/Charts";
import { ExperimentWorkspace } from "../components/ExperimentWorkspace";
import { ErrorNotice, SectionHeader } from "../components/Shell";
import { ProblemEditor } from "../components/ProblemEditor";
import { downloadJson, loadConfig, loadProblem, saveConfig, saveProblem } from "../storage";
import type { Algorithm, CompletedRun, Job, Problem, RunConfig, State } from "../types";

const algorithms: { value: Algorithm; label: string }[] = [
  { value: "steepest_ascent", label: "HC · Steepest Ascent" },
  { value: "sideways", label: "HC · Sideways" },
  { value: "stochastic", label: "HC · Stochastic" },
  { value: "random_restart", label: "HC · Random Restart" },
  { value: "simulated_annealing", label: "Simulated Annealing" },
  { value: "genetic_algorithm", label: "Genetic Algorithm" },
];

export function SetupPage() {
  const dataDialog = useRef<HTMLDialogElement>(null);
  const [workspaceMode, setWorkspaceMode] = useState<"single" | "experiment">("single");
  const [problem, setProblem] = useState<Problem | null>(() => loadProblem());
  const [config, setConfig] = useState<RunConfig>(() => loadConfig());
  const [preview, setPreview] = useState<any>(null);
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState<Job<CompletedRun> | null>(null);
  const [stateTab, setStateTab] = useState<"best" | "initial" | "final">("best");
  const [reference, setReference] = useState<any>(null);
  const [referenceBusy, setReferenceBusy] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [persist, setPersist] = useState(true);

  useEffect(() => {
    if (!problem) api.example().then((data) => { setProblem(data); saveProblem(data); }).catch((e) => setError(e.message));
  }, [problem]);

  useEffect(() => {
    if (!jobId) return;
    let stopped = false;
    let timer = 0;
    const poll = async () => {
      try {
        const next = await api.job<CompletedRun>(jobId);
        if (stopped) return;
        setJob(next);
        if (next.status === "queued" || next.status === "running") timer = window.setTimeout(poll, 700);
      } catch (pollError) {
        if (!stopped) setError(pollError instanceof Error ? pollError.message : "Hasil run tidak dapat dimuat.");
      }
    };
    poll();
    return () => { stopped = true; window.clearTimeout(timer); };
  }, [jobId]);

  const resetResult = () => { setPreview(null); setJobId(""); setJob(null); setReference(null); setError(""); };
  const changeProblem = (next: Problem) => { setProblem(next); saveProblem(next); resetResult(); };
  const changeConfig = <K extends keyof RunConfig>(key: K, value: RunConfig[K]) => {
    const next = { ...config, [key]: value };
    setConfig(next); saveConfig(next); resetResult();
  };
  const randomizeSeed = () => {
    const values = new Uint32Array(1);
    window.crypto.getRandomValues(values);
    changeConfig("seed", values[0] & 0x7fffffff);
  };
  const validate = async () => {
    if (!problem) return;
    setBusy(true); setError("");
    try { setPreview(await api.validate(problem, config.seed, config.objective)); }
    catch (validationError) { setError(validationError instanceof Error ? validationError.message : "Validasi gagal."); }
    finally { setBusy(false); }
  };
  const start = async () => {
    if (!problem || !preview) return;
    setBusy(true); setError(""); setReference(null); setStateTab("best");
    try {
      const { job_id } = await api.startRun(problem, config, persist);
      setJob({ id: job_id, kind: "run", status: "queued", progress: 0, message: "Menyiapkan run…", result: null, error: null });
      setJobId(job_id);
    } catch (runError) { setError(runError instanceof Error ? runError.message : "Run tidak dapat dimulai."); }
    finally { setBusy(false); }
  };

  const completed = job?.status === "completed" ? job.result : null;
  const emptyState = useMemo<State>(() => ({ placements: (problem?.packages ?? []).map((item) => ({ package_id: item.id, truck_id: null, position: null, orientation: 0 })) }), [problem]);
  const selectedState = useMemo<State>(() => {
    if (!completed) return preview?.state ?? emptyState;
    if (stateTab === "initial") return completed.result.initial_state;
    if (stateTab === "final") return completed.result.final_state;
    return completed.result.best_state;
  }, [completed, emptyState, preview, stateTab]);
  const running = job?.status === "queued" || job?.status === "running";

  const computeReference = async () => {
    if (!completed) return;
    setReferenceBusy(true);
    try { setReference(await api.reference(completed.problem, completed.config.objective, completed.result.best_objective)); }
    finally { setReferenceBusy(false); }
  };

  if (!problem) return <div className="loading-page">Memuat workspace…</div>;
  const outputSummary = summarize(problem, completed?.result.best_state ?? selectedState, config.objective);

  return (
    <>
      <div className="workspace-mode-switch" role="tablist" aria-label="Mode kerja">
        <button role="tab" aria-selected={workspaceMode === "single"} className={workspaceMode === "single" ? "active" : ""} onClick={() => setWorkspaceMode("single")}><strong>Algoritma</strong></button>
        <button role="tab" aria-selected={workspaceMode === "experiment"} className={workspaceMode === "experiment" ? "active" : ""} onClick={() => setWorkspaceMode("experiment")}><strong>Eksperimen</strong></button>
      </div>

      {workspaceMode === "single" ? <>
      <section className="panel algorithm-settings">
        <div className="settings-heading"><strong>Input Algoritma</strong><label className="check-line compact-check" title="Simpan snapshot 3D, diagram objective, trajectory, dan rekap hasil."><input type="checkbox" checked={persist} onChange={(e) => setPersist(e.target.checked)} /><span>Simpan Hasil</span></label></div>
        <div className="settings-body">
          <fieldset className="algorithm-picker">
            <legend>Algoritma</legend>
            <div className="algorithm-options">
              {algorithms.map((item) => <label key={item.value} className={config.algorithm === item.value ? "active" : ""}>
                <input type="radio" name="algorithm" value={item.value} checked={config.algorithm === item.value} onChange={() => changeConfig("algorithm", item.value)} />
                <span>{item.label.replace("HC · ", "")}</span>
              </label>)}
            </div>
          </fieldset>
          <div className="form-grid three common-settings">
            <label><span>Objective</span><select value={config.objective} onChange={(e) => changeConfig("objective", e.target.value as RunConfig["objective"])}><option value="total_value">Total value</option><option value="value_per_urgency">Value / (ETA + 1)</option></select></label>
            <label className="seed-field"><span>Seed</span><div className="input-action"><input type="number" value={config.seed} onChange={(e) => changeConfig("seed", e.currentTarget.valueAsNumber)} /><button type="button" onClick={randomizeSeed}>Acak</button></div></label>
            <label><span>Batas evaluasi</span><input type="number" min="1" step="1000" value={config.max_evaluations} onChange={(e) => changeConfig("max_evaluations", e.currentTarget.valueAsNumber)} /></label>
          </div>
          <div className="specific-settings"><AlgorithmFields config={config} change={changeConfig} /></div>
        </div>
      </section>

      <section className="panel viewer-shell">
        <div className="viewer-toolbar">
          <div className="viewer-title"><span className={preview ? "status-dot ready" : "status-dot"} /><strong>3D Viewer</strong></div>
          <div className="viewer-actions">
            {completed && <div className="segmented-control">{(["best", "initial", "final"] as const).map((tab) => <button key={tab} className={stateTab === tab ? "active" : ""} onClick={() => setStateTab(tab)}>{tab}</button>)}</div>}
            <button className="button quiet" onClick={() => dataDialog.current?.showModal()}>Data</button>
            <button className="button secondary" disabled={busy || running} onClick={validate}>{busy ? "Memeriksa…" : "Validasi"}</button>
            <button className="button primary" disabled={busy || running || !preview} onClick={start}>{running ? "Berjalan…" : "Jalankan"}</button>
          </div>
        </div>
        <StateChart problem={problem} state={selectedState} prominent />
        {running && <div className="viewer-progress"><span style={{ width: `${(job?.progress ?? 0) * 100}%` }} /><small>{job?.message ?? "Menjalankan optimasi…"}</small></div>}
      </section>

      {error && <ErrorNotice message={error} />}

      <section className="output-section">
        <div className="stage-heading"><h2>Hasil Percobaan</h2>{completed && <button className="button quiet" onClick={() => downloadJson(`${completed.run_id}-hasil.json`, completed.result)}>Unduh JSON</button>}</div>
        {job?.status === "failed" && <ErrorNotice message={job.error?.message ?? "Optimasi gagal."} />}
        <section className="panel result-overview">
          <div className="result-overview-header"><div className="result-state"><span className={`status-dot ${completed || preview ? "ready" : ""}`} /><div><strong>{completed ? "Run selesai" : running ? "Run aktif" : preview ? "Data valid" : "Menunggu validasi"}</strong><small>{completed?.run_id ?? `${problem.trucks.length} truk · ${problem.packages.length} paket`}</small></div></div>{completed && <span className="stop-chip">{completed.result.stopped_reason.replaceAll("_", " ")}</span>}</div>
          <div className={`result-stat-grid ${completed ? "six" : "four"}`}>
            <ResultStat label={completed ? "Best objective" : "Objective"} value={(completed?.result.best_objective ?? outputSummary.objective).toFixed(3)} />
            <ResultStat label="Total value" value={outputSummary.total.toFixed(2)} />
            <ResultStat label="Inside Container" value={String(outputSummary.inside)} />
            <ResultStat label="Outside Container" value={String(outputSummary.outside)} />
            {completed && <ResultStat label="Evaluasi" value={completed.result.evaluations_used.toLocaleString("id-ID")} />}
            {completed && <ResultStat label="Durasi" value={`${completed.elapsed_seconds.toFixed(3)} s`} />}
          </div>
        </section>

        {completed && <>
          <div className="two-column results-grid">
            <section className="panel output-card trajectory-card"><div className="output-card-heading"><div><strong>Trajectory</strong><small>Perubahan objective sepanjang pencarian.</small></div></div><TrajectoryChart trace={completed.result.trace} /></section>
            <section className="panel output-card"><div className="output-card-heading"><div><strong>Detail percobaan</strong><small>Konfigurasi dan informasi penyimpanan.</small></div></div><div className="detail-panel"><DefinitionList values={{ Algorithm: label(completed.result.algorithm), Objective: completed.result.objective.replaceAll("_", " "), Seed: completed.result.seed, "Path Hasil Percobaan": completed.artifact_dir ?? "Tidak disimpan", ...completed.metrics.algorithm_metrics }} /></div></section>
          </div>
          <SectionHeader title="Pembanding" meta="Opsional" />
          <section className="panel reference-panel">
            <div><strong>{completed.problem.packages.length <= 6 ? "Exact optimum" : "Knapsack upper bound"}</strong><p>{completed.problem.packages.length <= 6 ? "Nilai terbaik dari pencarian seluruh penempatan feasible (maksimal 6 paket)." : "Batas atas dari relaksasi kapasitas berat seluruh armada."}</p></div>
            {reference ? <div className="reference-result"><span>Nilai <b>{Number(reference.value).toFixed(3)}</b></span>{reference.gap !== undefined && <span>Gap <b>{Number(reference.gap).toFixed(3)}</b></span>}</div> : <button className="button secondary" disabled={referenceBusy} onClick={computeReference}>{referenceBusy ? "Menghitung…" : "Hitung pembanding"}</button>}
          </section>
        </>}
      </section>

      <dialog ref={dataDialog} className="app-dialog wide" onClick={(event) => { if (event.target === event.currentTarget) dataDialog.current?.close(); }}>
        <div className="dialog-surface">
          <header className="dialog-header"><div><span className="eyebrow">Problem data</span><h2>Armada dan paket</h2><p>Perubahan disimpan langsung ke workspace.</p></div><button className="icon-button" aria-label="Tutup dialog" onClick={() => dataDialog.current?.close()}>×</button></header>
          <div className="dialog-body editor-dialog-body"><ProblemEditor value={problem} onChange={changeProblem} /></div>
          <footer className="dialog-footer"><button className="button primary" onClick={() => dataDialog.current?.close()}>Selesai</button></footer>
        </div>
      </dialog>

      </> : <ExperimentWorkspace currentProblem={problem} />}
    </>
  );
}

function AlgorithmFields({ config, change }: { config: RunConfig; change: <K extends keyof RunConfig>(key: K, value: RunConfig[K]) => void }) {
  const field = (fieldLabel: string, key: keyof RunConfig, step = 1, min = 0) => (
    <label><span>{fieldLabel}</span><input type="number" min={min} step={step} value={config[key] ?? ""} onChange={(e) => change(key, e.currentTarget.valueAsNumber as never)} /></label>
  );
  if (config.algorithm === "sideways") return <div className="form-grid slim">{field("Maksimum sideways", "max_sideways")}</div>;
  if (config.algorithm === "stochastic") return <div className="form-grid slim">{field("Maksimum iterasi", "max_iterations")}</div>;
  if (config.algorithm === "random_restart") return <div className="form-grid slim">{field("Jumlah restart", "num_restarts")}</div>;
  if (config.algorithm === "simulated_annealing") return <div className="form-grid three">{field("Maksimum iterasi", "max_iterations")}{field("Temperatur minimum", "t_min", .001, .000001)}{field("Sampel kalibrasi", "calibration_samples")}</div>;
  if (config.algorithm === "genetic_algorithm") return <div className="form-grid four">{field("Populasi", "population_size", 1, 1)}{field("Generasi", "generations", 1, 1)}{field("Peluang crossover", "crossover_prob", .05, 0)}<label><span>Peluang mutasi</span><input placeholder="Default" type="number" min="0" max="1" step=".01" value={config.mutation_prob ?? ""} onChange={(e) => change("mutation_prob", e.target.value === "" ? null : e.currentTarget.valueAsNumber)} /></label></div>;
  return <p className="no-specific-settings">Tidak ada parameter tambahan untuk algoritma ini.</p>;
}

export function Metric({ label: metricLabel, value }: { label: string; value: string }) {
  return <div className="metric"><span>{metricLabel}</span><strong>{value}</strong></div>;
}

function ResultStat({ label: statLabel, value }: { label: string; value: string }) {
  return <div className="result-stat"><span>{statLabel}</span><strong>{value}</strong></div>;
}

function label(value: string) { return value.split("_").map((word) => word[0].toUpperCase() + word.slice(1)).join(" "); }
function DefinitionList({ values }: { values: Record<string, any> }) {
  return <dl>{Object.entries(values).filter(([, value]) => value !== null && value !== undefined && typeof value !== "object").map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{typeof value === "number" ? value.toLocaleString("id-ID", { maximumFractionDigits: 4 }) : String(value)}</dd></div>)}</dl>;
}
