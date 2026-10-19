# Tugas Besar 1 IF3170 — Algoritma Local Search

Implementasi optimasi pemuatan paket ke dalam armada truk menggunakan beberapa algoritma *local search*. Aplikasi menyediakan antarmuka web untuk menyusun kasus, menjalankan algoritma, memeriksa solusi dalam visualisasi 3D, serta membandingkan performa algoritma melalui eksperimen berulang.

## Deskripsi Aplikasi

Aplikasi menggunakan antarmuka web satu halaman dengan dua mode utama:

- **Algoritma** untuk menjalankan satu algoritma pada satu kasus pemuatan. Pengguna dapat mengatur data truk dan paket, parameter algoritma, serta *seed* percobaan. Hasilnya mencakup visualisasi 3D, nilai objektif, paket di dalam dan di luar kontainer, jumlah evaluasi, durasi, serta grafik perkembangan nilai objektif.
- **Eksperimen** untuk menjalankan beberapa kombinasi algoritma, kasus uji, dan *seed*. Hasil percobaan disajikan dalam tabel dan diagram agar kualitas solusi serta biaya komputasinya dapat dibandingkan.

Input kasus dapat dimasukkan melalui formulir web atau berkas JSON. Sebelum dijalankan, aplikasi memvalidasi struktur data dan batasan dasar kasus. Visualisasi 3D menyediakan tampilan *initial state*, *best state*, dan *final state*, dengan label paket serta detail paket ketika disorot.

Jika opsi **Simpan Hasil** diaktifkan, setiap *run* disimpan menggunakan *timestamp* ke dalam `output/runs/<timestamp>/`. Artefak utama yang dihasilkan adalah:

- hasil lengkap dalam JSON;
- riwayat nilai objektif dalam CSV;
- diagram perkembangan nilai objektif;
- tangkapan visualisasi 3D solusi.

Eksperimen juga menghasilkan rekap CSV dan JSON, diagram perbandingan nilai objektif, durasi, dan jumlah evaluasi, serta artefak untuk setiap *run*. Direktori `output/` dibuat otomatis ketika hasil pertama kali disimpan.

## Deskripsi Persoalan Singkat

Permasalahan yang diselesaikan adalah pemuatan paket tiga dimensi ke dalam satu atau lebih peti kemas pada truk. Setiap truk memiliki dimensi ruang muat dan kapasitas berat, sedangkan setiap paket memiliki dimensi, berat, nilai, ETA, sifat *fragile*, orientasi, serta posisi.

Tujuan utama optimasi adalah memaksimalkan kualitas paket yang berhasil dimasukkan ke dalam truk. Aplikasi menyediakan dua fungsi objektif: **Total Value** untuk memaksimalkan jumlah nilai paket dan **Value / (ETA + 1)** untuk menggunakan ETA sebagai heuristik atau bonus. Objektif kedua memprioritaskan paket bernilai tinggi dengan ETA lebih kecil.

Solusi harus mematuhi batasan berikut:

- paket berada sepenuhnya di dalam salah satu kontainer atau dinyatakan berada di luar kontainer;
- tidak ada dua paket yang saling bertumpang tindih;
- paket dapat menggunakan enam orientasi hasil rotasi pada sumbu koordinat;
- posisi paket menggunakan koordinat bilangan bulat;
- paket tidak boleh melayang; sedikitnya satu titik pada alas paket harus memperoleh penopang;
- paket *fragile* tidak boleh menopang paket lain;
- total berat paket di setiap truk tidak boleh melebihi kapasitas berat truk tersebut.

Sebuah *state* menyimpan penempatan, orientasi, dan status masuk/keluar setiap paket. *Neighbor* dibentuk melalui operasi pemindahan posisi, rotasi, pemindahan paket ke dalam atau ke luar truk, dan perpindahan paket antarkontainer. Algoritma kemudian mencari *state* dengan nilai objektif terbaik yang tetap valid.

Untuk kasus kecil hingga enam paket, aplikasi dapat menghitung **exact optimum** sebagai acuan kualitas solusi. Untuk kasus yang lebih besar, aplikasi menyediakan **knapsack upper bound**, yaitu batas atas berdasarkan relaksasi kapasitas berat armada dan bukan jaminan solusi yang dapat diwujudkan secara geometris.

## Algoritma yang Didukung

1. **Steepest Ascent Hill Climbing**  
   Mengevaluasi seluruh tetangga pada setiap iterasi dan memilih tetangga dengan peningkatan nilai terbesar.

2. **Hill Climbing with Sideways Move**  
   Mengizinkan perpindahan ke solusi bernilai sama dalam jumlah terbatas untuk membantu keluar dari area datar (*plateau*).

3. **Stochastic Hill Climbing**  
   Memilih langkah dari kandidat tetangga yang lebih baik secara stokastik.

4. **Random Restart Hill Climbing**  
   Menjalankan hill climbing dari beberapa *initial state* dan mengambil solusi terbaik dari seluruh *restart*.

5. **Simulated Annealing**  
   Dapat menerima solusi yang lebih buruk berdasarkan temperatur dan probabilitas tertentu, sehingga pencarian memiliki peluang keluar dari optimum lokal.

6. **Genetic Algorithm**  
   Mengembangkan populasi solusi melalui seleksi, *crossover*, mutasi, dan elitisme. Mode eksperimen mendukung pengujian beberapa ukuran populasi dan jumlah generasi.

Parameter yang tersedia bergantung pada algoritma yang dipilih, antara lain jumlah iterasi, batas *sideways move*, jumlah *restart*, temperatur awal, *cooling rate*, ukuran populasi, jumlah generasi, probabilitas *crossover*, probabilitas mutasi, dan jumlah individu elit.

*Seed* digunakan oleh proses acak pada pembentukan *initial state* dan pada algoritma stokastik. Menggunakan kasus, konfigurasi, dan *seed* yang sama membantu menghasilkan percobaan yang dapat diulang.

## Tech Stack

### Backend dan algoritma

- Python 3.12 atau lebih baru
- FastAPI sebagai REST API
- Pydantic untuk validasi dan serialisasi data
- Uvicorn sebagai server ASGI
- Matplotlib dan Pandas untuk rekap serta ekspor hasil eksperimen

### Frontend

- React 19
- TypeScript
- Vite
- Plotly.js yang dibundel di frontend untuk grafik dan visualisasi interaktif
- CSS kustom untuk antarmuka responsif bergaya *glassmorphism*

Dependensi Python `Streamlit` dan `Plotly` masih tersedia untuk modul antarmuka lama, tetapi antarmuka utama aplikasi saat ini menggunakan React dan FastAPI.

### Manajemen dependensi

- `uv` untuk lingkungan dan dependensi Python
- `npm` untuk dependensi frontend

## Cara Menjalankan

### Prasyarat

Pastikan perangkat telah memiliki:

- Python 3.12 atau lebih baru;
- [`uv`](https://docs.astral.sh/uv/);
- Node.js 20 atau lebih baru beserta `npm`.

### Mode pengembangan

Dari direktori utama repositori, instal dependensi Python dan frontend:

```bash
uv sync
cd frontend
npm ci
```

Jalankan frontend dan backend secara bersamaan:

```bash
npm run dev
```

Perintah tersebut menjalankan:

- frontend Vite di `http://127.0.0.1:5173`;
- backend FastAPI di `http://127.0.0.1:8000`.

Permintaan dengan awalan `/api` dari frontend akan diteruskan ke backend oleh Vite.

### Mode build

Bangun frontend terlebih dahulu:

```bash
cd frontend
npm run build
cd ..
```

Kemudian jalankan server aplikasi:

```bash
uv run uvicorn webapi.main:app --host 127.0.0.1 --port 8000
```

Buka `http://127.0.0.1:8000`. FastAPI akan menyajikan hasil build frontend dari direktori `frontend/dist`.

### Memeriksa frontend

Untuk memeriksa tipe TypeScript dan memastikan frontend dapat dibangun:

```bash
cd frontend
npm run typecheck
npm run build
```

## Struktur Direktori Utama

```text
.
├── frontend/       # Antarmuka React, TypeScript, dan Vite
├── src/
│   ├── algorithms/ # Implementasi algoritma pencarian
│   ├── domain/     # Model persoalan, constraint, dan fungsi objektif
│   ├── experiments/# Protokol serta rekap eksperimen
│   └── webapi/     # REST API FastAPI
├── tests/          # Dataset contoh dan kasus validasi
├── docs/           # Laporan dan dokumentasi tugas besar
└── output/         # Hasil run dan eksperimen yang disimpan
```

## Author

Kelompok **G55 — Tocatdz**:

| Nama | NIM |
|---|---:|
| Juan Oloando Simanungkalit | 13524032 |
| Narendra Dharma Wistara M. | 13524044 |
| Reinhard Alfonzo Hutabarat | 13524056 |

Program Studi Teknik Informatika, Sekolah Teknik Elektro dan Informatika, Institut Teknologi Bandung — IF3170 Inteligensi Artifisial.
