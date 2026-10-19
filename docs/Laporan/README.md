# Laporan Tugas Besar 1 IF3170

Kompilasi dari folder ini:

```sh
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Hasil: `main.pdf`. Kompilasi satu kali lagi bila LaTeX meminta pembaruan referensi.
Upload seluruh folder, bukan main.tex saja, bila memakai Overleaf.

## Struktur

- `main.tex`: kerangka 11pt dari main.tex.tpl, metadata, daftar isi, input bab.
- `preamble.sty`: salinan persis preamble.sty.tpl unggahan, termasuk geometri badan laporan, tabel, warna, dan gaya kode Atom One Light.
- `report-settings.sty`: tambahan khusus laporan dan macro identitas.
- `cover.tex` dan `itb.png`: cover sesuai permintaan awal, memakai logo unggahan.
- `section/`: isi laporan yang dipisahkan per bab.

ETA ditetapkan sebagai heuristik/bonus. Fungsi objektif wajib tetap total nilai muatan.

Paket preamble template mencakup physics, svg, tikz, circuitikz, tkz-euclide,
tikz-network, tcolorbox, dan minitoc. Gunakan instalasi TeX Live yang menyediakan
paket tersebut. Tidak memerlukan shell-escape untuk isi laporan saat ini.

Letakkan formulir AI terisi sebagai `form-penggunaan-ai.pdf` agar disisipkan otomatis.
Kode sumber repository dapat dirujuk dari sini menggunakan `../../src/...`.
