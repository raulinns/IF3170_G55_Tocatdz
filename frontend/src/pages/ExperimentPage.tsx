import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { ErrorNotice, PageHeader } from "../components/Shell";
import { loadProblem, saveProblem } from "../storage";
import type { Objective, Problem } from "../types";
import { Metric } from "./SetupPage";

const protocols = [
  ["specification", "Non-GA · 15 run"],
  ["hc_comparison", "Perbandingan HC · 12 run"],
  ["ga_population_sweep", "GA · variasi populasi · 9 run"],
  ["ga_generation_sweep", "GA · variasi generasi · 9 run"],
  ["fairness", "Fairness · HC, SA, GA · 9 run"],
] as const;

export function ExperimentPage() {
  const navigate = useNavigate();
  const configDialog = useRef<HTMLDialogElement>(null);
  const [problem, setProblem] = useState<Problem | null>(() => loadProblem());
  const [dataset, setDataset] = useState("current");
  const [protocol, setProtocol] = useState("specification");
  const [objective, setObjective] = useState<Objective>("total_value");
  const [seeds, setSeeds] = useState("42, 137, 2026");
  const [budget, setBudget] = useState(50_000);
  const [matrix, setMatrix] = useState<any>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!problem) api.example().then((data) => { setProblem(data); saveProblem(data); }).catch((e) => setError(e.message));
  }, [problem]);

  const selectDataset = async (name: string) => {
    setDataset(name); setMatrix(null); setError("");
    if (name === "current") { setProblem(loadProblem()); return; }
    try { setProblem(await api.fixture(name)); }
    catch (e) { setError(e instanceof Error ? e.message : "Dataset gagal dimuat."); }
  };
  const payload = () => {
    if (!problem) throw new Error("Problem belum tersedia.");
    const parsedSeeds = seeds.split(",").map((item) => Number(item.trim())).filter(Number.isFinite);
    if (!parsedSeeds.length) throw new Error("Masukkan sedikitnya satu seed.");
    return { problem, protocol, objective, seeds: parsedSeeds, max_evaluations: budget };
  };
  const preview = async () => {
    setBusy(true); setError("");
    try { setMatrix(await api.previewExperiment(payload())); }
    catch (e) { setError(e instanceof Error ? e.message : "Matriks run tidak dapat dibuat."); }
    finally { setBusy(false); }
  };
  const start = async () => {
    setBusy(true); setError("");
    try { const { job_id } = await api.startExperiment(payload()); navigate(`/experiments/${job_id}`); }
    catch (e) { setError(e instanceof Error ? e.message : "Eksperimen tidak dapat dimulai."); setBusy(false); }
  };
  const protocolLabel = protocols.find(([value]) => value === protocol)?.[1] ?? protocol;

  return (
    <>
      <PageHeader eyebrow="Batch run" title="Bandingkan dengan tenang." description="Satu protokol, beberapa run, hasil yang dapat dibandingkan." />
      <section className="panel setup-console">
        <div className="summary-item">
          <div><span className="summary-label">Eksperimen</span><strong>{protocolLabel}</strong><small>{dataset === "current" ? "Data dari setup" : `Fixture ${dataset}`} · {seeds.split(",").filter((item) => item.trim()).length} seed</small></div>
          <button className="button quiet" onClick={() => configDialog.current?.showModal()}>Atur eksperimen</button>
        </div>
        <div className="run-actions">
          <div className="validation-status"><span className={matrix ? "status-dot ready" : "status-dot"} /><div><strong>{matrix ? `${matrix.run_count} run siap` : "Matriks belum ditinjau"}</strong><small>{problem ? `${problem.trucks.length} truk · ${problem.packages.length} paket` : "Memuat dataset…"}</small></div></div>
          <div className="action-buttons"><button className="button secondary" disabled={busy || !problem} onClick={preview}>Lihat matriks</button><button className="button primary" disabled={busy || !problem} onClick={start}>Mulai eksperimen</button></div>
        </div>
      </section>
      {error && <ErrorNotice message={error} />}
      {matrix && <section className="matrix-section"><div className="metric-row compact"><Metric label="Total run" value={String(matrix.run_count)} /><Metric label="Seed" value={String(new Set(matrix.runs.map((r: any) => r.seed)).size)} /><Metric label="Grup" value={String(new Set(matrix.runs.map((r: any) => r.group)).size)} /></div><div className="panel table-wrap"><table className="data-table"><thead><tr><th>Case</th><th>Algoritma</th><th>Grup</th><th>Seed</th><th>Budget</th></tr></thead><tbody>{matrix.runs.map((row: any) => <tr key={row.case_id}><td>{row.case_id}</td><td>{row.algorithm.replaceAll("_", " ")}</td><td>{row.group}</td><td>{row.seed}</td><td>{row.budget.toLocaleString("id-ID")}</td></tr>)}</tbody></table></div></section>}

      <dialog ref={configDialog} className="app-dialog" onClick={(event) => { if (event.target === event.currentTarget) configDialog.current?.close(); }}>
        <div className="dialog-surface">
          <header className="dialog-header"><div><span className="eyebrow">Batch settings</span><h2>Konfigurasi eksperimen</h2><p>Tentukan dataset dan protokol pengujian.</p></div><button className="icon-button" aria-label="Tutup dialog" onClick={() => configDialog.current?.close()}>×</button></header>
          <div className="dialog-body"><div className="form-grid two">
            <label><span>Dataset</span><select value={dataset} onChange={(e) => selectDataset(e.target.value)}><option value="current">Data dari setup</option><option value="tiny">Tiny exact</option><option value="single">Single-truck constrained</option><option value="multi">Multi-truck constrained</option></select></label>
            <label><span>Protokol</span><select value={protocol} onChange={(e) => { setProtocol(e.target.value); setMatrix(null); }}>{protocols.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label><span>Objective</span><select value={objective} onChange={(e) => { setObjective(e.target.value as Objective); setMatrix(null); }}><option value="total_value">Total value</option><option value="value_per_urgency">Value / (ETA + 1)</option></select></label>
            <label><span>Seeds</span><input value={seeds} onChange={(e) => { setSeeds(e.target.value); setMatrix(null); }} /></label>
            <label><span>Budget per run</span><input type="number" min="1" step="1000" disabled={protocol === "fairness"} value={budget} onChange={(e) => { setBudget(e.currentTarget.valueAsNumber); setMatrix(null); }} /></label>
          </div></div>
          <footer className="dialog-footer"><button className="button primary" onClick={() => configDialog.current?.close()}>Selesai</button></footer>
        </div>
      </dialog>
    </>
  );
}
