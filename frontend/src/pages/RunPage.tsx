import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { StateChart, summarize, TrajectoryChart } from "../components/Charts";
import { ErrorNotice, PageHeader, SectionHeader } from "../components/Shell";
import { downloadJson } from "../storage";
import type { CompletedRun, Job, State } from "../types";
import { Metric } from "./SetupPage";

export function RunPage() {
  const { id = "" } = useParams();
  const [job, setJob] = useState<Job<CompletedRun> | null>(null);
  const [stateTab, setStateTab] = useState<"best" | "initial" | "final">("best");
  const [reference, setReference] = useState<any>(null);
  const [referenceBusy, setReferenceBusy] = useState(false);

  useEffect(() => {
    let stopped = false;
    const poll = async () => {
      try {
        const next = await api.job<CompletedRun>(id);
        if (stopped) return;
        setJob(next);
        if (next.status === "queued" || next.status === "running") window.setTimeout(poll, 700);
      } catch (error) {
        if (!stopped) setJob({ id, kind: "run", status: "failed", progress: 0, message: "", result: null, error: { type: "RequestError", message: error instanceof Error ? error.message : "Hasil tidak ditemukan." } });
      }
    };
    poll();
    return () => { stopped = true; };
  }, [id]);

  const completed = job?.result ?? null;
  const selected: State | null = useMemo(() => {
    if (!completed) return null;
    if (stateTab === "initial") return completed.result.initial_state;
    if (stateTab === "final") return completed.result.final_state;
    return completed.result.best_state;
  }, [completed, stateTab]);
  const summary = completed && selected ? summarize(completed.problem, selected, completed.config.objective) : null;

  if (!job || job.status === "queued" || job.status === "running") return (
    <div className="center-stage">
      <div className="run-status">
        <span className="spinner" />
        <p className="eyebrow">Run aktif</p>
        <h1>Optimasi sedang berjalan.</h1>
        <p>{job?.message ?? "Menghubungkan ke server…"}</p>
        <div className="progress-track"><span style={{ width: `${(job?.progress ?? 0) * 100}%` }} /></div>
        <small>{Math.round((job?.progress ?? 0) * 100)}%</small>
      </div>
    </div>
  );
  if (job.status === "failed" || !completed) return (
    <><PageHeader eyebrow="Run gagal" title="Hasil tidak tersedia." description="Periksa pesan berikut sebelum mencoba lagi." /><ErrorNotice message={job.error?.message ?? "Terjadi kesalahan."} /><Link className="button secondary" to="/">Kembali ke setup</Link></>
  );

  const result = completed.result;
  const computeReference = async () => {
    setReferenceBusy(true);
    try { setReference(await api.reference(completed.problem, completed.config.objective, result.best_objective)); }
    finally { setReferenceBusy(false); }
  };

  return (
    <>
      <div className="result-heading">
        <PageHeader eyebrow="Run selesai" title="Hasil optimasi" description={`${label(result.algorithm)} · seed ${result.seed}`} />
        <Link className="button secondary" to="/">Run baru</Link>
      </div>
      <div className="metric-row">
        <Metric label="Best objective" value={result.best_objective.toFixed(3)} />
        <Metric label="Evaluasi" value={result.evaluations_used.toLocaleString("id-ID")} />
        <Metric label="Durasi" value={`${completed.elapsed_seconds.toFixed(3)} s`} />
        <Metric label="Stop" value={result.stopped_reason.replaceAll("_", " ")} />
      </div>

      <SectionHeader title="Solusi" meta={completed.run_id} />
      <section className="panel result-panel">
        <div className="panel-toolbar">
          <div className="tabs">
            {(["best", "initial", "final"] as const).map((tab) => <button key={tab} className={stateTab === tab ? "active" : ""} onClick={() => setStateTab(tab)}>{tab[0].toUpperCase() + tab.slice(1)} state</button>)}
          </div>
          <button className="button ghost small" onClick={() => downloadJson(`${completed.run_id}-result.json`, result)}>Unduh JSON</button>
        </div>
        {summary && <div className="metric-row compact embedded"><Metric label="Objective" value={summary.objective.toFixed(2)} /><Metric label="Total value" value={summary.total.toFixed(2)} /><Metric label="Inside Container" value={String(summary.inside)} /><Metric label="Outside Container" value={String(summary.outside)} /></div>}
        {selected && <StateChart problem={completed.problem} state={selected} />}
      </section>

      <div className="two-column results-grid">
        <section><SectionHeader title="Trajectory" /><div className="panel chart-panel"><TrajectoryChart trace={result.trace} /></div></section>
        <section><SectionHeader title="Detail run" /><div className="panel detail-panel"><DefinitionList values={{ Algorithm: label(result.algorithm), Objective: result.objective.replaceAll("_", " "), Seed: result.seed, "Path Hasil Percobaan": completed.artifact_dir ?? "Tidak disimpan", ...completed.metrics.algorithm_metrics }} /></div></section>
      </div>

      <SectionHeader title="Pembanding" meta="Opsional" />
      <section className="panel reference-panel">
        <div><strong>{completed.problem.packages.length <= 6 ? "Exact optimum" : "Knapsack upper bound"}</strong><p>Gunakan sebagai acuan kualitas solusi.</p></div>
        {reference ? <div className="reference-result"><span>Nilai <b>{Number(reference.value).toFixed(3)}</b></span>{reference.gap !== undefined && <span>Gap <b>{Number(reference.gap).toFixed(3)}</b></span>}</div> : <button className="button secondary" disabled={referenceBusy} onClick={computeReference}>{referenceBusy ? "Menghitung…" : "Hitung pembanding"}</button>}
      </section>
    </>
  );
}

function label(value: string) { return value.split("_").map((word) => word[0].toUpperCase() + word.slice(1)).join(" "); }
function DefinitionList({ values }: { values: Record<string, any> }) {
  return <dl>{Object.entries(values).filter(([, value]) => value !== null && value !== undefined && typeof value !== "object").map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{typeof value === "number" ? value.toLocaleString("id-ID", { maximumFractionDigits: 4 }) : String(value)}</dd></div>)}</dl>;
}
