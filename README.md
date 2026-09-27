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

## Pembagian Tugas

- **Raulin:** setup repository, domain model, dan Simulated Annealing.
- **Fonzo:** varian Hill Climbing.
- **Juan:** Genetic Algorithm serta reference/bound.
- **Bersama:** integrasi, eksperimen, visualisasi, dan laporan setelah algoritma stabil.
