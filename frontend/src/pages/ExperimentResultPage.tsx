import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { ComparisonChart } from "../components/Charts";
import { ErrorNotice, PageHeader, SectionHeader } from "../components/Shell";
import { downloadJson } from "../storage";
import type { Job } from "../types";
import { Metric } from "./SetupPage";

type ExperimentResult = { experiment_id: string; experiment_dir: string; expected_runs: number; successful_runs: number; failed_runs: number; runs: Record<string, any>[]; summary: Record<string, any>[] };

export function ExperimentResultPage() {
  const { id = "" } = useParams();
  const [job, setJob] = useState<Job<ExperimentResult> | null>(null);
  useEffect(() => {
    let stopped = false;
    const poll = async () => {
      try {
        const next = await api.job<ExperimentResult>(id);
        if (stopped) return;
        setJob(next);
        if (["queued", "running"].includes(next.status)) window.setTimeout(poll, 900);
      } catch (error) {
        if (!stopped) setJob({ id, kind: "experiment", status: "failed", progress: 0, message: "", result: null, error: { type: "RequestError", message: error instanceof Error ? error.message : "Eksperimen tidak ditemukan." } });
      }
    };
    poll(); return () => { stopped = true; };
  }, [id]);

  if (!job || job.status === "queued" || job.status === "running") return <div className="center-stage"><div className="run-status"><span className="spinner" /><p className="eyebrow">Eksperimen aktif</p><h1>Menjalankan rangkaian pencarian.</h1><p>{job?.message ?? "Menghubungkan ke server…"}</p><div className="progress-track"><span style={{ width: `${(job?.progress ?? 0) * 100}%` }} /></div><small>{Math.round((job?.progress ?? 0) * 100)}%</small></div></div>;
  if (job.status === "failed" || !job.result) return <><PageHeader eyebrow="Eksperimen gagal" title="Hasil tidak tersedia." description="Periksa konfigurasi dan jalankan kembali." /><ErrorNotice message={job.error?.message ?? "Terjadi kesalahan."} /><Link className="button secondary" to="/experiments">Kembali</Link></>;
  const result = job.result;
  return (
    <>
      <div className="result-heading"><PageHeader eyebrow="Eksperimen selesai" title="Perbandingan hasil" description={result.experiment_id} /><Link className="button secondary" to="/experiments">Eksperimen baru</Link></div>
      <div className="metric-row"><Metric label="Total run" value={String(result.expected_runs)} /><Metric label="Berhasil" value={String(result.successful_runs)} /><Metric label="Gagal" value={String(result.failed_runs)} /><Metric label="Grup" value={String(result.summary.length)} /></div>
      <SectionHeader title="Ringkasan" meta="Median best objective" /><div className="panel chart-panel"><ComparisonChart rows={result.summary} /></div>
      <SectionHeader title="Detail run" meta={result.experiment_dir} />
      <div className="panel table-wrap"><table className="data-table"><thead><tr><th>Status</th><th>Algoritma</th><th>Seed</th><th>Grup</th><th>Best objective</th><th>Evaluasi</th><th>Durasi</th></tr></thead><tbody>{result.runs.map((row) => <tr key={row.case_id}><td><span className={`status-dot ${row.status}`} />{row.status}</td><td>{row.algorithm?.replaceAll("_", " ")}</td><td>{row.seed}</td><td>{row.group_label}</td><td>{row.best_objective?.toFixed?.(3) ?? "—"}</td><td>{row.evaluations?.toLocaleString?.("id-ID") ?? "—"}</td><td>{row.elapsed_seconds?.toFixed?.(3) ?? "—"} s</td></tr>)}</tbody></table></div>
      <div className="download-row"><button className="button secondary" onClick={() => downloadJson(`${result.experiment_id}-runs.json`, result.runs)}>Unduh detail</button><button className="button secondary" onClick={() => downloadJson(`${result.experiment_id}-summary.json`, result.summary)}>Unduh ringkasan</button></div>
    </>
  );
}
