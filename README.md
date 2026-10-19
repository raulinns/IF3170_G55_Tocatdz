# IF3170 Tugas Besar 1

Implementasi local search untuk optimasi penempatan paket tiga dimensi pada armada truk.

## Prasyarat

- Python 3.12 atau lebih baru
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
```

## GUI

Jalankan antarmuka Streamlit:

```bash
uv run streamlit run src/gui/app.py
```

GUI menyediakan alur data, pencarian, dan eksplorasi hasil yang terpisah. Preview
3D menampilkan seluruh armada dalam satu kanvas; tombol `Semua` atau ID truk pada
grafik dapat digunakan untuk mengubah fokus. Seluruh runner Hill Climbing,
Simulated Annealing, dan Genetic Algorithm sudah terintegrasi. Pilih algoritma dan
objective, klik **Validasi test case & buat preview**, lalu **Mulai pencarian**.

Tombol reference digunakan sebagai pembanding kualitas solusi. Test case dengan
maksimal enam paket dapat dihitung exact optimum-nya; test case yang lebih besar
menggunakan knapsack upper bound.

Jika opsi penyimpanan artefak aktif, hasil run ditulis ke `output/runs/<run-id>/`
dalam bentuk JSON state/metrics, CSV trajectory, dan PNG objective.

## Test Case

Test case eksperimen berada di `tests/` dan menggunakan format JSON canonical
dengan field `trucks` dan `packages`. Dataset yang disediakan adalah:

- `tiny_exact.json` untuk pembanding exact optimum;
- `single_truck_constrained.json` untuk eksperimen utama;
- `multi_truck_constrained.json` untuk bonus multi-truck;
- `invalid_duplicate_package_id.json` untuk menguji penolakan ID paket duplikat.

Untuk kasus invalid, upload file lalu klik **Muat ke editor** dan
**Validasi test case & buat preview**. GUI harus menampilkan error `duplicate package id`
dan tidak membuat preview.

Mode **Experiments** pada GUI menyediakan protokol tiga seed untuk HC/SA,
perbandingan seluruh HC, fairness, serta dua variasi parameter GA. Hasilnya
disimpan di `output/experiments/<experiment-id>/`.

## Pembagian Tugas

- **Raulin:** setup repository, domain model, dan Simulated Annealing.
- **Fonzo:** varian Hill Climbing.
- **Juan:** Genetic Algorithm serta reference/bound.
- **Bersama:** integrasi, eksperimen, visualisasi, dan laporan setelah algoritma stabil.
