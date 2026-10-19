import { useRef, useState } from "react";
import type { Package, Problem, Truck } from "../types";
import { downloadJson } from "../storage";

type Props = { value: Problem; onChange: (problem: Problem) => void };
type NumberField = HTMLInputElement & { valueAsNumber: number };

const blankTruck = (index: number): Truck => ({
  id: `T${index}`,
  dimensions: { width: 6, length: 5, height: 4 },
  max_capacity: 25,
});
const blankPackage = (index: number): Package => ({
  id: `P${index}`,
  dimensions: { width: 2, length: 2, height: 1 },
  value: 10,
  weight: 5,
  is_fragile: false,
  eta: 0,
});

export function ProblemEditor({ value, onChange }: Props) {
  const [tab, setTab] = useState<"trucks" | "packages">("trucks");
  const [fileError, setFileError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const updateTruck = (index: number, patch: Partial<Truck>) => {
    const trucks = value.trucks.map((truck, i) => i === index ? { ...truck, ...patch } : truck);
    onChange({ ...value, trucks });
  };
  const updateTruckDimension = (index: number, key: keyof Truck["dimensions"], number: number) => {
    const truck = value.trucks[index];
    updateTruck(index, { dimensions: { ...truck.dimensions, [key]: number } });
  };
  const updatePackage = (index: number, patch: Partial<Package>) => {
    const packages = value.packages.map((item, i) => i === index ? { ...item, ...patch } : item);
    onChange({ ...value, packages });
  };
  const updatePackageDimension = (index: number, key: keyof Package["dimensions"], number: number) => {
    const item = value.packages[index];
    updatePackage(index, { dimensions: { ...item.dimensions, [key]: number } });
  };
  const number = (event: React.ChangeEvent<HTMLInputElement>) => (event.currentTarget as NumberField).valueAsNumber;

  const importFile = async (file?: File) => {
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text());
      if (!Array.isArray(parsed.trucks) || !Array.isArray(parsed.packages)) throw new Error("Struktur JSON tidak sesuai.");
      onChange(parsed);
      setFileError("");
    } catch (error) {
      setFileError(error instanceof Error ? error.message : "JSON tidak dapat dibaca.");
    }
  };

  return (
    <section className="panel editor-panel">
      <div className="panel-toolbar">
        <div className="tabs" role="tablist">
          <button className={tab === "trucks" ? "active" : ""} onClick={() => setTab("trucks")}>
            Truk <span>{value.trucks.length}</span>
          </button>
          <button className={tab === "packages" ? "active" : ""} onClick={() => setTab("packages")}>
            Paket <span>{value.packages.length}</span>
          </button>
        </div>
        <div className="toolbar-actions">
          <input ref={fileRef} hidden type="file" accept="application/json,.json" onChange={(event) => importFile(event.target.files?.[0])} />
          <button className="button ghost small" onClick={() => fileRef.current?.click()}>Impor JSON</button>
          <button className="button ghost small" onClick={() => downloadJson("problem.json", value)}>Ekspor</button>
        </div>
      </div>
      {fileError && <div className="inline-error">{fileError}</div>}

      {tab === "trucks" ? (
        <div className="table-wrap">
          <table className="editor-table">
            <thead><tr><th>ID</th><th>Lebar</th><th>Panjang</th><th>Tinggi</th><th>Kapasitas</th><th aria-label="Aksi" /></tr></thead>
            <tbody>{value.trucks.map((truck, index) => (
              <tr key={index}>
                <td><input aria-label={`ID truk ${index + 1}`} value={truck.id} onChange={(e) => updateTruck(index, { id: e.target.value })} /></td>
                {(["width", "length", "height"] as const).map((key) => <td key={key}><input aria-label={`${key} truk ${truck.id}`} type="number" min="1" value={truck.dimensions[key]} onChange={(e) => updateTruckDimension(index, key, number(e))} /></td>)}
                <td><input aria-label={`Kapasitas truk ${truck.id}`} type="number" min="0.01" step="0.1" value={truck.max_capacity} onChange={(e) => updateTruck(index, { max_capacity: number(e) })} /></td>
                <td><button className="icon-button" aria-label={`Hapus ${truck.id}`} disabled={value.trucks.length === 1} onClick={() => onChange({ ...value, trucks: value.trucks.filter((_, i) => i !== index) })}>×</button></td>
              </tr>
            ))}</tbody>
          </table>
          <button className="add-row" onClick={() => onChange({ ...value, trucks: [...value.trucks, blankTruck(value.trucks.length + 1)] })}>+ Tambah truk</button>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="editor-table package-table">
            <thead><tr><th>ID</th><th>Lebar</th><th>Panjang</th><th>Tinggi</th><th>Value</th><th>Berat</th><th>Fragile</th><th>ETA</th><th aria-label="Aksi" /></tr></thead>
            <tbody>{value.packages.map((item, index) => (
              <tr key={index}>
                <td><input aria-label={`ID paket ${index + 1}`} value={item.id} onChange={(e) => updatePackage(index, { id: e.target.value })} /></td>
                {(["width", "length", "height"] as const).map((key) => <td key={key}><input aria-label={`${key} paket ${item.id}`} type="number" min="1" value={item.dimensions[key]} onChange={(e) => updatePackageDimension(index, key, number(e))} /></td>)}
                <td><input aria-label={`Value ${item.id}`} type="number" min="0" step="0.1" value={item.value} onChange={(e) => updatePackage(index, { value: number(e) })} /></td>
                <td><input aria-label={`Berat ${item.id}`} type="number" min="0" step="0.1" value={item.weight} onChange={(e) => updatePackage(index, { weight: number(e) })} /></td>
                <td className="check-cell"><input aria-label={`Fragile ${item.id}`} type="checkbox" checked={item.is_fragile} onChange={(e) => updatePackage(index, { is_fragile: e.target.checked })} /></td>
                <td><input aria-label={`ETA ${item.id}`} type="number" min="0" value={item.eta} onChange={(e) => updatePackage(index, { eta: number(e) })} /></td>
                <td><button className="icon-button" aria-label={`Hapus ${item.id}`} disabled={value.packages.length === 1} onClick={() => onChange({ ...value, packages: value.packages.filter((_, i) => i !== index) })}>×</button></td>
              </tr>
            ))}</tbody>
          </table>
          <button className="add-row" onClick={() => onChange({ ...value, packages: [...value.packages, blankPackage(value.packages.length + 1)] })}>+ Tambah paket</button>
        </div>
      )}
    </section>
  );
}
