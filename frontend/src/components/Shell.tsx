import { Outlet } from "react-router-dom";

export function Shell() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <span className="brand-mark">1</span>
            <span>Tugas Besar 1 IF3170: Algoritma Local Search</span>
          </div>
        </div>
      </header>
      <main className="page"><Outlet /></main>
    </div>
  );
}

export function PageHeader({ title, description, eyebrow }: { title: string; description: string; eyebrow?: string }) {
  return (
    <div className="page-header">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  );
}

export function SectionHeader({ title, meta }: { title: string; meta?: string }) {
  return (
    <div className="section-header">
      <h2>{title}</h2>
      {meta && <span>{meta}</span>}
    </div>
  );
}

export function ErrorNotice({ message }: { message: string }) {
  return <div className="notice error" role="alert">{message}</div>;
}
