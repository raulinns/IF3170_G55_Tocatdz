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
dan menampilkan preview penempatan 3D berdasarkan seed. Runner Genetic Algorithm
sudah terintegrasi: upload JSON, pilih **Genetic Algorithm**, klik
**Validasi & buat preview**, lalu **Run algoritma**. Algoritma lain baru dapat
dijalankan setelah runner-nya didaftarkan di
`src/if3170_tubes1/search/dispatch.py`.

## Pembagian Tugas

- **Raulin:** setup repository, domain model, dan Simulated Annealing.
- **Fonzo:** varian Hill Climbing.
- **Juan:** Genetic Algorithm serta reference/bound.
- **Bersama:** integrasi, eksperimen, visualisasi, dan laporan setelah algoritma stabil.
