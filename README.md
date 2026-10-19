# IF3170 Tugas Besar 1

Implementasi local search untuk optimasi penempatan paket tiga dimensi pada armada truk.

## Prasyarat

- Python 3.12 atau lebih baru
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync --dev
```

## Verifikasi

```bash
uv run if3170
uv run pytest -q
```

## GUI

Jalankan antarmuka Streamlit:

```bash
uv run streamlit run src/if3170_tubes1/gui/app.py
```

GUI dapat mengedit data truk/paket, upload atau download JSON, memvalidasi input,
dan menampilkan preview penempatan 3D berdasarkan seed. Seluruh runner Hill
Climbing, Simulated Annealing, dan Genetic Algorithm sudah terintegrasi. Pilih
algoritma dan objective, klik **Validasi & buat preview**, lalu **Mulai
pencarian**.

Jika opsi penyimpanan artefak aktif, hasil run ditulis ke `output/runs/<run-id>/`
dalam bentuk JSON state/metrics, CSV trajectory, dan PNG objective.

## Pembagian Tugas

- **Raulin:** setup repository, domain model, dan Simulated Annealing.
- **Fonzo:** varian Hill Climbing.
- **Juan:** Genetic Algorithm serta reference/bound.
- **Bersama:** integrasi, eksperimen, visualisasi, dan laporan setelah algoritma stabil.
