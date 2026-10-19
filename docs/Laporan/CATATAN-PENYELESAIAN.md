# Catatan Penyelesaian Laporan

Berkas ini terpisah dari main.tex dan tidak disertakan dalam PDF laporan.
Status penyusunan, rincian implementasi yang belum tersedia, hasil yang harus
dikumpulkan, dan daftar pemeriksaan dipusatkan di sini. Judul bagian pada laporan
dipertahankan sesuai outline, tanpa tabel hasil kosong atau kotak placeholder.

## Keputusan yang sudah ditetapkan

- ETA digunakan untuk heuristik/bonus, bukan sekadar metadata.
- Fungsi objektif wajib tetap memaksimalkan total nilai paket yang dimuat.
- Rumusan skor ETA, bobot, integrasi ke algoritma, serta hasil evaluasinya harus mengikuti kode aktual.
- Formatting mengikuti main.tex.tpl (11pt, input preamble, isi modular) dan preamble.sty.tpl unggahan.
- Cover mengikuti permintaan awal, dengan margin khusus cover dan logo ITB unggahan.

## Status

- Deskripsi dan formulasi: sudah ditulis berdasarkan spesifikasi dan QnA.
- Rancangan: notasi dan ketentuan tersedia; detail teknis harus diselaraskan dengan kode.
- Implementasi: uraian fungsi/kelas dan potongan kode aktual belum tersedia.
- Eksperimen: prosedur tersedia; angka dan visualisasi belum tersedia.
- Kesimpulan: menunggu hasil dan analisis.
- Identitas, pembagian tugas, dan formulir AI: perlu dilengkapi anggota kelompok.

## Tindak lanjut per bagian

### Klarifikasi dan Asumsi Pemodelan — INTEGRASI ETA

- [ ] Keputusan ETA sudah ditetapkan sebagai heuristik/bonus. Lengkapi bentuk skor atau prioritas, bobot, aturan nilai ETA yang diterima, letak pemakaian dalam algoritma, dan pengujian pengaruhnya.

### Representasi Paket, Truk, dan State — RANCANGAN REPRESENTASI

- [ ] Jelaskan struktur data aktual, aturan koordinat paket di luar, cara menyatakan orientasi, salinan state, dan pemetaan okupansi. Notasi di atas merupakan formulasi, bukan klaim mengenai struktur kode.

### Pembentukan Initial State — RANCANGAN DAN PENGUJIAN

- [ ] Lengkapi algoritma inisialisasi, batas percobaan penempatan, penanganan kegagalan, dan contoh initial state dari program.

### Rotasi Sebuah Paket — KEPUTUSAN OPERATOR

- [ ] Tetapkan sampling neighbor, aturan posisi/orientasi saat swap dan rotasi, serta apakah kandidat tidak valid ditolak, diulang, atau diperbaiki. Bedakan cakupan seluruh neighborhood dengan kandidat yang disampling.

### Kapasitas Berat — IMPLEMENTASI VALIDATOR

- [ ] Jelaskan fungsi pemeriksaan global/lokal, urutan pemeriksaan, dan pengujian perubahan support setelah move.

### Hill-Climbing — PEMILIHAN VARIAN

- [ ] Nyatakan varian yang dipakai, neighborhood yang ditinjau, tie-breaking, batas iterasi, kondisi berhenti, dan parameter tambahan. Untuk sideways, jelaskan cara menghitung serta mereset penghitung sideways; untuk restart, jelaskan makna maksimum restart dan pemilihan hasil akhir.

### Simulated Annealing — PARAMETER DAN DEFINISI STUCK

- [ ] Tetapkan temperatur awal, jadwal pendinginan, kondisi berhenti, dan kebijakan current/best state. Definisikan stuck secara operasional sebelum eksperimen. Stagnasi selama sejumlah iterasi tidak otomatis membuktikan local optimum apabila seluruh neighborhood tidak diperiksa.

### Genetic Algorithm — RANCANGAN GA

- [ ] Tentukan encoding/decoding, fitness, seleksi, crossover, mutasi, replacement, elitisme bila ada, serta penanganan individu tidak valid. Tetapkan parameter di luar populasi/iterasi agar eksperimen terkontrol. Jangan menganggap crossover sebagai neighbor tunggal yang sama dengan move pada hill-climbing/SA; jelaskan hubungannya dengan representasi yang dipilih.

### Format Input dan Syarat Validitas — FORMAT INPUT FINAL

- [ ] Sertakan contoh input aktual, field wajib/opsional, aturan nilai yang diterima, pesan kesalahan, dan kesesuaian dokumentasi README. Domain nilai/berat/ETA harus dinyatakan sebagai kontrak program karena batas angkanya tidak ditentukan secara rinci oleh spesifikasi.

### Lingkungan dan Struktur Program — STRUKTUR AKTUAL

- [ ] Isi versi Python, sistem operasi, dependensi, struktur modul, entry point, perintah setup/run, dan commit yang dievaluasi. Lengkapi alamat repository pada macro RepoURL di awal berkas.

### Representasi State dan Pemeriksaan Validitas — KODE AKTUAL

- [ ] Sisipkan implementasi model data, okupansi, serta pemeriksaan batas, overlap, support, fragile, dan berat.

### Initial State, Neighbor, dan Fungsi Objektif — KODE AKTUAL

- [ ] Sisipkan fungsi pembentuk initial state, operator move, dan fungsi objektif. Jelaskan pengelolaan seed serta penanganan kandidat tidak valid.

### Implementasi Hill-Climbing — KODE AKTUAL

- [ ] Sisipkan loop pencarian dan pemilihan neighbor sesuai varian aktual, pencatatan histori, kondisi berhenti, serta penghitung iterasi/restart/sideways.

### Implementasi Simulated Annealing — KODE AKTUAL

- [ ] Sisipkan perhitungan delta nilai, penerimaan kandidat, pembaruan temperatur, penyimpanan current/best state, dan penghitung stuck. Pastikan histori memakai konvensi yang sama dengan grafik eksperimen.

### Implementasi Genetic Algorithm — KODE AKTUAL

- [ ] Sisipkan encoding, decoding, seleksi, crossover, mutasi, replacement, validasi/repair, dan perhitungan statistik populasi tiap generasi.

### Visualisasi dan Penyimpanan Hasil — KODE AKTUAL

- [ ] Jelaskan modul visualisasi, format berkas output, penamaan run, legenda orientasi/fragile, dan tampilan ruang kosong atau pemetaan okupansi.

### Komposisi Dataset — DATASET FINAL

- [ ] Isi jumlah kasus, jumlah paket, ukuran truk, kapasitas, rentang atribut, proporsi fragile, rasio volume/berat, cara pembangkitan, seed dataset, dan alasan pemilihan. Simpan input yang sama untuk perbandingan.

### Pengujian Kebenaran Sebelum Eksperimen — PENGUJIAN

- [ ] Catat hasil uji aktual dan perbaikan yang dilakukan. Daftar kasus di atas merupakan rencana pemeriksaan, bukan klaim bahwa uji telah lulus.

### Prosedur Run dan Pencatatan — KONFIGURASI FINAL

- [ ] Isi seed, perangkat, waktu yang diukur, batas pencarian, parameter tetap, dan aturan pemilihan final state. Catat current state dan best-so-far secara terpisah jika keduanya tersedia.

### Hasil Eksperimen Hill-Climbing — RUN HILL-CLIMBING

- [ ] Isi varian dan parameter, state awal/akhir tiap run, nilai objektif akhir, grafik objektif terhadap iterasi, serta durasi. Lampirkan visualisasi seluruh run atau letakkan rincian lengkap di lampiran.

### Hasil Eksperimen Simulated Annealing — RUN SA

- [ ] Isi state awal/akhir, nilai objektif, durasi, histori objektif, ekspresi eksponensial, dan frekuensi stuck untuk setiap run.

### Pengaruh Jumlah Populasi — PARAMETER DAN 18 RUN GA

- [ ] Ganti simbol konfigurasi dengan nilai aktual. Catat state awal/akhir, nilai objektif akhir, populasi, generasi, durasi, serta seed setiap run. Ringkas populasi awal dan tampilkan individu terbaik awal, dengan label bahwa visual tersebut bukan seluruh populasi.

### Kualitas Solusi dan Acuan Optimalitas — ANALISIS HASIL

- [ ] Bandingkan kualitas solusi per dataset dan jelaskan acuan yang tersedia tanpa mengklaim global optimum dari hasil terbaik semata.

### Durasi, Konsistensi, dan Konvergensi — REKAPITULASI

- [ ] Isi tabel perbandingan dan bahas kompromi kualitas-waktu, variasi antarrun, pengaruh neighborhood, serta perbedaan current dan best-so-far.

### Pengaruh Parameter Genetic Algorithm — ANALISIS GA

- [ ] Isi pembahasan kedua seri, identifikasi konfigurasi dengan kompromi yang sesuai, dan jelaskan keterbatasan perbandingannya.

### Implementasi dan Evaluasi Bonus — KEPUTUSAN BONUS

- [ ] Bonus ETA dipertahankan. Lengkapi rumusan, kode, dan hasil evaluasinya. Catat terpisah apakah seluruh varian hill-climbing atau multi-truk ikut dikerjakan; jangan mengklaim fitur yang belum dibuat.

### Kesimpulan — HASIL DAN ANALISIS

- [ ] Tuliskan ketercapaian tujuan, kualitas solusi, durasi, konsistensi, serta pengaruh parameter GA berdasarkan eksperimen. Belum ada dasar untuk menyatakan algoritma terbaik pada draf ini.

### Keterbatasan — EVALUASI AKTUAL

- [ ] Tambahkan keterbatasan representasi, neighborhood, parameter, skala input, visualisasi, dan pengukuran yang ditemukan selama pengerjaan.

### Saran Pengembangan — KESIMPULAN EKSPERIMEN

- [ ] Pilih saran yang didukung bukti dan jelaskan manfaat yang diharapkan; jangan menyatakan fitur telah tersedia jika belum dibuat.

### Form Penggunaan Generative AI — FORMULIR RESMI

- [ ] Lengkapi formulir yang dirujuk spesifikasi, lakukan pemeriksaan oleh anggota kelompok, dan simpan sebagai form-penggunaan-ai.pdf pada folder laporan.

### Hasil Lengkap Eksperimen — OUTPUT EKSPERIMEN

- [ ] Lampirkan state awal/akhir dan visualisasi setiap run, tabel hasil mentah, histori objektif, grafik, dan lokasi berkas output. Untuk random restart, tambahkan rincian iterasi per restart apabila digunakan.

### Dataset dan Konfigurasi Pengujian — INPUT DAN KONFIGURASI FINAL

- [ ] Lampirkan contoh input valid, karakteristik seluruh dataset, seed dataset/run, parameter algoritma, versi program, serta perintah reproduksi eksperimen.

## Visualisasi yang harus dihasilkan

- [ ] `figures/hc-states.png`: visualisasi initial dan final state hill-climbing. Label LaTeX: `fig:hc-state`.
- [ ] `figures/hc-objective.png`: grafik objektif hill-climbing terhadap iterasi untuk tiga run. Label LaTeX: `fig:hc-plot`.
- [ ] `figures/sa-states.png`: visualisasi initial dan final state SA. Label LaTeX: `fig:sa-state`.
- [ ] `figures/sa-objective.png`: grafik objektif SA terhadap iterasi untuk tiga run. Label LaTeX: `fig:sa-plot`.
- [ ] `figures/sa-exponential.png`: grafik ekspresi eksponensial SA terhadap iterasi. Label LaTeX: `fig:sa-exp`.
- [ ] `figures/ga-states.png`: visualisasi individu awal dan final GA beserta ringkasan populasi. Label LaTeX: `fig:ga-state`.
- [ ] `figures/ga-generations.png`: grafik maksimum dan rata-rata objektif untuk variasi generasi GA. Label LaTeX: `fig:ga-gen`.
- [ ] `figures/ga-populations.png`: grafik maksimum dan rata-rata objektif untuk variasi populasi GA. Label LaTeX: `fig:ga-pop`.

Setiap run HC dan SA harus mempunyai state awal/akhir, nilai objektif akhir,
grafik objektif terhadap iterasi, dan durasi. Tambahkan metrik khusus varian HC.
SA juga memerlukan grafik ekspresi eksponensial dan frekuensi stuck.
GA membutuhkan tabel per run pada kedua seri eksperimen (18 run per dataset),
state/populasi awal dan akhir, populasi, generasi, durasi, serta grafik maksimum
dan rata-rata objektif. Tidak ada angka hasil yang boleh diisi tanpa pengukuran.

## Pengisian dokumen dan lampiran

- [ ] Isi macro identitas dan repository pada report-settings.sty.
- [ ] Tambahkan tabel kontribusi aktual pada section/06-pembagian-tugas.tex.
- [ ] Lengkapi pengungkapan penggunaan AI termasuk versi model bila diminta,
  penggunaan AI pada kode/debugging, dan verifikasi manusia.
- [ ] Sisipkan formulir resmi terisi sebagai form-penggunaan-ai.pdf.
- [ ] Tambahkan referensi metode adaptasi pada laporan dan komentar program.
- [ ] Lengkapi isi subbab implementasi dan hasil yang saat ini hanya berupa judul outline.
- [ ] Hapus/ganti narasi rancangan bila keputusan akhir berbeda dengan formulasi draf.
- [ ] Kompilasi ulang dan periksa layout setelah menyisipkan tabel, kode, dan gambar.

## Lokasi tujuan

Lokasi yang diminta pengguna adalah docs/Laporan/ di repository:
/home/raulin/Documents/Endra/02_Areas/A003_Learning/Semester-5/IF3170_Inteligensi-Artifisial/Tugas-Besar/

Direktori repository tersebut terdeteksi read-only pada sesi ini. Revisi disiapkan
di direktori proyek ChatGPT yang dapat ditulis sampai akses lokasi tujuan tersedia.
