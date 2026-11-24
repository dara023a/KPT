# Distributed Sorting (Master–Worker) — UAS Komputasi Paralel dan Sistem Terdistribusi

Tema 6. Python 3.10+, `numpy`, `psutil`. Salin **seluruh folder** ke setiap PC (Master dan Worker). Jalankan program sebagai modul dari root repo, mis. `python -m src.master_sort ...`.

| File | Peran |
|---|---|
| `src/common.py` | protokol framing, algoritma sort, merge, checksum |
| `src/worker_sort.py` | dijalankan di 9 PC Worker |
| `src/master_sort.py` | dijalankan di 1 PC Master (seq / local / dist / bench) |
| `src/prepare_dataset.py` | hanya di Master, dijalankan sekali: mengubah data OpenStreetMap Indonesia menjadi `.npy` |

```
python -m pip install -r requirements.txt              # atau: pip install numpy psutil
python -m pip install -r requirements-dataset.txt      # opsional: PBF / CSV / Parquet
```

## Struktur repo
```
.
├── src/                    # implementasi kanonik
│   ├── __init__.py
│   ├── common.py
│   ├── master_sort.py
│   ├── worker_sort.py
│   └── prepare_dataset.py
├── tests/                  # unittest + integrasi loopback
├── config/nodes.example.json
├── results/raw/            # CSV hasil (default --csv)
├── results/figures/        # grafik untuk laporan
├── docs/                   # laporan & bukti node
├── scripts/                # run_master.ps1, run_worker.ps1
├── requirements.txt
├── requirements-dataset.txt
└── data/                   # opsional; .pbf/.npy diabaikan git
```
Jalankan dari root repo agar paket `src` dikenali. Hasil baru ditulis ke `results/raw/results.csv`; `results.csv` di root adalah hasil lama yang dibiarkan.

## Menjalankan tes
```
python -m unittest discover -s tests -v
```

## Persiapan jaringan
- Semua PC satu subnet. Di **Worker**: izinkan inbound **TCP 9998** dan **UDP 9999** (Windows Firewall).
- Worker: `python -m src.worker_sort` (tampil hostname, jumlah core, port). Alternatif PowerShell: `powershell -File scripts\run_worker.ps1 -Port 9998`.
- Master mencari worker lewat UDP broadcast + TCP sweep (seperti kode Bapak). Jika diblokir router, pakai
  `--hosts 192.168.1.11,192.168.1.12,...`. Alternatif: `powershell -File scripts\run_master.ps1 -Mode dist -Size 10m -Hosts 192.168.1.11,192.168.1.12`.
- Contoh inventaris 9 worker ada di `config/nodes.example.json` (referensi untuk `--hosts`, belum dibaca otomatis).

## Menjalankan 1 Master + 9 Worker (perintah lengkap)

Semua perintah dijalankan dari root repo. Setelah `git pull`, **hentikan worker lama (`Ctrl+C`) lalu jalankan ulang** agar kode terbaru dipakai. Pastikan semua node memakai commit yang sama (`git rev-parse --short HEAD`).

### 1. Worker (ulangi di 9 PC)

```powershell
cd C:\path\ke\KPT
git pull origin main
python -m pip install -r requirements.txt

# sekali saja, PowerShell as Administrator:
netsh advfirewall firewall add rule name="KPT-Worker-TCP-9998" dir=in action=allow protocol=TCP localport=9998
netsh advfirewall firewall add rule name="KPT-Worker-UDP-9999" dir=in action=allow protocol=UDP localport=9999

# sisakan 1 core agar thread heartbeat tidak kelaparan CPU
$procs = [Math]::Max(1, [Environment]::ProcessorCount - 1)
python -m src.worker_sort --procs $procs
```

Banner yang benar adalah `HEAVY PARALLEL WORKER NODE (MULTI-CORE READY)`. Pastikan yang dijalankan adalah `python -m src.worker_sort` dari root repo, bukan salinan worker lama.

### 2. Master

```powershell
cd C:\path\ke\KPT
git pull origin main
python -m pip install -r requirements.txt
```

Deteksi worker otomatis sama seperti folder `kpt`: UDP broadcast port `9999` + TCP sweep port `9998`. Kalau semua worker satu subnet, tidak perlu menulis daftar IP. Pastikan saat Master dijalankan muncul `[+] Siap Digunakan 9 Worker Komputasi`.

```powershell
python -m src.master_sort dist --dataset osm_java_lat.npy --shuffle --size 10m --timeout 10 --chunks-per-worker 8 --csv results/raw/demo_dist.csv
```

Jika ada worker yang tidak terdeteksi (beda subnet atau broadcast diblokir), baru pakai `--hosts`:

```powershell
$hosts = "IP_W1:9998,IP_W2:9998,IP_W3:9998,IP_W4:9998,IP_W5:9998,IP_W6:9998,IP_W7:9998,IP_W8:9998,IP_W9:9998"
python -m src.master_sort dist --dataset osm_java_lat.npy --shuffle --size 10m --hosts $hosts --workers 9 --timeout 10 --chunks-per-worker 8 --csv results/raw/demo_dist.csv
```

### 3. Perintah demo video (maks 5 menit)

Gunakan dataset dan `--size` yang sama di semua uji. Dataset hanya perlu ada di Master. Jika `osm_java_lat.npy` belum ada, ganti `--dataset osm_java_lat.npy --shuffle` dengan `--size 10m` (data sintetis).

```powershell
# a. Sequential baseline
python -m src.master_sort seq --dataset osm_java_lat.npy --shuffle --size 10m --repeat 1 --csv results/raw/demo_seq.csv

# b. Local parallel
python -m src.master_sort local --dataset osm_java_lat.npy --shuffle --size 10m --procs 1,2,4,8 --repeat 1 --csv results/raw/demo_local.csv

# c. Distributed 9 worker (auto-discovery seperti kpt)
python -m src.master_sort dist --dataset osm_java_lat.npy --shuffle --size 10m --workers 9 --timeout 10 --chunks-per-worker 8 --csv results/raw/demo_dist.csv
```

Dynamic load balancing: hentikan satu worker, jalankan ulang dengan `--slowdown 3`, lalu jalankan benchmark di Master.

```powershell
# di satu worker (hitung ulang jika terminal baru)
$procs = [Math]::Max(1, [Environment]::ProcessorCount - 1)
python -m src.worker_sort --procs $procs --slowdown 3

# di Master
python -m src.master_sort bench --suite schedule --dataset osm_java_lat.npy --shuffle --size 5m --timeout 10 --repeat 1 --csv results/raw/demo_schedule.csv

# setelah demo, kembalikan worker tanpa slowdown
python -m src.worker_sort --procs $procs
```

Fault tolerance: jalankan satu worker dengan `--crash-after`, lalu hidupkan lagi saat job masih berjalan.

```powershell
# di satu worker (hitung ulang jika terminal baru)
$procs = [Math]::Max(1, [Environment]::ProcessorCount - 1)
python -m src.worker_sort --procs $procs --crash-after 2 --crash-delay 2

# di Master
python -m src.master_sort dist --dataset osm_java_lat.npy --shuffle --size 10m --workers 9 --timeout 10 --chunks-per-worker 8 --csv results/raw/demo_ft.csv

# saat worker mati, jalankan lagi di PC tersebut
python -m src.worker_sort --procs $procs
```

Scalability untuk laporan:

```powershell
python -m src.master_sort bench --suite scalability --dataset osm_java_lat.npy --shuffle --size 5m --workers-list 1,2,4,6,9 --timeout 10 --repeat 1 --csv results/raw/demo_scalability.csv
```

Untuk laporan, ulangi `seq`, `local`, `dist`, `bench --suite schedule`, dan `bench --suite scalability` dengan `--size 20m --repeat 3`.

### 4. Urutan rekaman video

1. **0:00-0:30** topologi 10 PC: tampilkan `hostname` dan `ipconfig` di Master + beberapa Worker.
2. **0:30-1:00** banner 9 Worker (`HEAVY PARALLEL WORKER NODE ...`).
3. **1:00-1:20** Master menampilkan daftar 9 Worker hasil auto-discovery.
4. **1:20-2:20** `dist` 9 Worker: rekam `[DISPATCH]`, `[✓] TASK`, `[FASE 3: GATHER ...]`, dan `VERIFIKASI LULUS`.
5. **2:20-3:20** `bench --suite schedule` dengan satu Worker `--slowdown 3`.
6. **3:20-4:30** fault tolerance: Worker `--crash-after 2`, rekam `[DOWN] -> [REQUEUE] -> [RECOVERED]`, lalu restart Worker untuk `[REJOIN]`.
7. **4:30-5:00** tunjukkan CSV hasil di `results/raw/demo_*.csv`.

## Alur sistem
1. Master memuat dataset publik (`--dataset`, lihat bagian Dataset) atau, bila tidak diberikan, membangkitkan data sintetis (`numpy.random.default_rng(seed)`).
2. **Task decomposition**: data dipecah menjadi `workers × 4` chunk (dynamic) atau 1 chunk per worker sebanding jumlah core (static).
3. **Dynamic load balancing**: tiap worker *menarik* chunk berikutnya begitu selesai (pull). Worker cepat otomatis mengerjakan lebih banyak chunk.
4. Worker membagi chunk ke semua core (`ProcessPoolExecutor`), sort paralel, merge lokal, kirim balik.
5. **Fault tolerance**: worker mengirim heartbeat 1 detik sekali. Tidak ada data/heartbeat > 5 detik atau koneksi putus → worker ditandai mati, chunk-nya masuk antrian lagi (maks 3 retry). Worker yang hidup kembali otomatis bergabung (`[REJOIN]`).
6. **Merge**: `--merge master` (Master menggabungkan semua) atau `--merge tiered` (chunk digabung dulu di worker, Master hanya merge terakhir).
7. **Verifikasi** otomatis: hasil terurut + jumlah elemen + checksum (sum dan sum kuadrat) sama dengan data asli.

## Penjelasan: apa yang diurutkan dan bagaimana caranya
**Tugas.** Mengurutkan jutaan angka dari kecil ke besar. Pada proyek ini angkanya adalah *latitude* node peta OpenStreetMap Indonesia. Cara membandingkannya sama seperti mengurutkan angka biasa (8, 4, 3, 7, 5 menjadi 3, 4, 5, 7, 8).

**Latitude sebagai kunci sort.** Latitude disimpan sebagai bilangan bulat (derajat x 10.000.000) agar lebih cepat diurutkan dan hemat memori; urutannya tidak berubah. Sebagian besar wilayah Indonesia berada di selatan khatulistiwa, sehingga nilainya negatif (-7 lebih kecil dari -6). Urutan kecil ke besar berarti dari titik paling selatan ke paling utara.

| Kota (perkiraan, ilustrasi) | Latitude | Disimpan sebagai |
|---|---|---|
| Yogyakarta | -7,7956 | -77.956.000 |
| Surabaya | -7,2575 | -72.575.000 |
| Semarang | -6,9932 | -69.932.000 |
| Bandung | -6,9175 | -69.175.000 |
| Jakarta | -6,2088 | -62.088.000 |

**Cara kerja (merge sort terdistribusi).** Contoh 8 angka dan 2 Worker:
```
Data asli       : [9, 3, 7, 1, 8, 2, 6, 4]
1. Master membagi data (task decomposition)
   Chunk A      : [9, 3, 7, 1]  -> Worker 1
   Chunk B      : [8, 2, 6, 4]  -> Worker 2
2. Worker mengurutkan chunk masing-masing secara bersamaan (fase paralel)
   Worker 1     : [1, 3, 7, 9]
   Worker 2     : [2, 4, 6, 8]
3. Master menggabungkan dua daftar terurut (merge, fase serial)
   Hasil akhir  : [1, 2, 3, 4, 6, 7, 8, 9]
```
Merge cepat karena kedua daftar sudah terurut: bandingkan angka terdepan tiap daftar, ambil yang lebih kecil, ulangi.

**Dua fase dan kaitannya dengan analisis kinerja.**
- Fase 1 (sort chunk) berjalan paralel di semua Worker dan semua core. Di sinilah speedup didapat.
- Fase 2 (merge akhir di Master) bersifat serial. Bagian ini membatasi speedup (Hukum Amdahl, Pertemuan 7). Opsi `--merge tiered` menggabungkan hasil bertingkat di Worker untuk memperkecil bagian serial ini.

**Letak logika sorting di kode.**

| Bagian | File dan fungsi |
|---|---|
| Pembagian data menjadi chunk | `src/master_sort.py`: `build_sort_tasks` |
| Penjadwalan, deteksi Worker mati, requeue | `src/master_sort.py`: `Runner` |
| Alur satu job dan merge akhir | `src/master_sort.py`: `run_dist` |
| Sort satu potongan data (`--algo`) | `src/common.py`: `sort_part` |
| Menggabungkan dua / banyak daftar terurut | `src/common.py`: `merge_two`, `merge_many` |
| Sort paralel di satu komputer | `src/common.py`: `parallel_sort_local` |
| Sort chunk di Worker (bagi per core lalu merge lokal) | `src/worker_sort.py`: `do_sort` |
| Baseline sequential | `src/master_sort.py`: `cmd_seq` |

**Alur satu job.**
```
Master: data -> pecah jadi chunk -> kirim ke Worker
Worker: chunk -> bagi per core -> sort paralel -> merge lokal -> kirim balik
Master: kumpulkan chunk terurut -> merge akhir -> verifikasi (terurut, jumlah dan checksum sama)
```

## Dataset publik (Indonesia)
Sumber: **OpenStreetMap Indonesia dari Geofabrik** (https://download.geofabrik.de/asia/indonesia.html).
Tersedia per pulau (java, sumatra, kalimantan, sulawesi, ...) dalam format `.osm.pbf`. Lisensi ODbL:
cantumkan "(c) OpenStreetMap contributors" di laporan. Kunci sort: latitude node x 1e7 (int32).

```bash
pip install osmium numpy                       # hanya di Master
# 1) unduh file .osm.pbf (mis. java-latest.osm.pbf) dari halaman Geofabrik di atas
# 2) uji kecil dulu (1 juta node), lalu data penuh
python -m src.prepare_dataset --pbf java-latest.osm.pbf --key lat --limit 1000000 --out tes.npy
python -m src.prepare_dataset --pbf java-latest.osm.pbf --key lat --out osm_java_lat.npy
# 3) pakai di semua pengujian (acak urutan agar tidak terurut berdasarkan ID)
python -m src.master_sort seq  --dataset osm_java_lat.npy --shuffle --size 20m
python -m src.master_sort dist --dataset osm_java_lat.npy --shuffle --size 20m
```
- `--size` memotong dataset (mis. 20m); tanpa `--size` seluruh dataset dipakai. Gunakan **nilai yang sama** di semua uji.
- Dataset juga bisa dari `.csv` / `.parquet`: `--dataset file.parquet --column nama_kolom` (butuh pandas, pyarrow). Kolom float dikali 1e6 lalu dibulatkan ke int64.
- Dataset hanya dibutuhkan di **Master**; Worker menerima chunk lewat jaringan.
- Catat di BAB III: nama file, tanggal unduh, jumlah elemen, dtype, kunci sort, dan apakah `--shuffle` dipakai.
- Status: `src/prepare_dataset.py` belum diuji dengan file PBF asli (sandbox tanpa internet dan tanpa paket osmium). Jalankan uji `--limit 1000000` dulu. Bagian loader `.npy`/`.csv`/`.parquet` di Master sudah diuji.

## Parameter tambahan
- `--timeout N` (min 2): detik tanpa heartbeat sebelum Worker dianggap mati (default 5). Untuk membahas false positive/negative dan kecepatan recovery (Pertemuan 13 slide 16), ulangi uji fault tolerance dengan `--timeout 2`, `5`, dan `10`.
- `bench --suite granularity --cpw-list 1,2,4,8,16`: menguji jumlah chunk per worker. Ukuran chunk minimal 100.000 elemen, jadi pada data kecil jumlah chunk bisa lebih sedikit dari yang diminta (lihat kolom `chunk`).

## Catatan Windows dan Termux
- **Windows (Master/Worker)**: izinkan Python di Windows Firewall (TCP 9998, UDP 9999). Jalankan di terminal biasa; `multiprocessing` butuh skrip dijalankan sebagai file (sudah memakai `if __name__ == "__main__"`).
- **Termux (HP, Worker)**: `pkg install python python-numpy`; `psutil` bersifat opsional (tanpa psutil, kolom CPU/memori Worker kosong). Gunakan `--procs` sesuai jumlah core HP, dan matikan mode hemat baterai atau aktifkan wake lock agar proses tidak dibekukan.
- Hotspot atau jaringan Wi-Fi sering memblokir UDP broadcast: jalankan Master dengan `--hosts IP_WORKER1,IP_WORKER2` (atau `ip:port`).
- Python dan versi NumPy tidak harus sama, tetapi `src/common.py` harus identik di semua perangkat.

## Pilih algoritma (`--algo`) — tulis alasannya di BAB III
| Algo | Sifat | Dipakai untuk |
|---|---|---|
| `timsort` (default) | `sorted()` Python, CPU-bound | demo manfaat paralelisme |
| `mergesort` | merge sort Python murni, paling berat | analisis algoritma |
| `numpy` | `np.sort` di C, sangat cepat | **communication-bound**: speedup bisa < 1 karena waktu transfer data > waktu sort. Jangan dibuang; ini bahan analisis yang bagus (Pertemuan 7 & 8) |

## Pengujian sesuai soal (bagian 3)
Gunakan `--size` dan `--dataset` yang sama di semua uji (mis. `20m`; tambah jika sort terlalu cepat). Semua run tersimpan di `results.csv` (termasuk kolom `dataset`, `timeout_s`, `cpw`).

```bash
# a. Sequential (baseline)
python -m src.master_sort seq --size 10m --repeat 3

# b. Local parallel (1 komputer)
python -m src.master_sort local --size 10m --procs 1,2,4,8 --repeat 3

# c. Distributed
python -m src.master_sort dist --size 10m

# d. Dynamic load balancing: jalankan SATU worker dengan  python -m src.worker_sort --slowdown 3
python -m src.master_sort bench --suite schedule --size 10m --repeat 3      # static vs dynamic

# e. Fault tolerance (pilih salah satu cara membuat worker gagal)
#    1) python -m src.worker_sort --crash-after 2     (crash otomatis saat task ke-2)
#    2) tutup worker (Ctrl+C / kill) atau cabut kabel saat job berjalan
python -m src.master_sort dist --size 10m           # lihat [DOWN] [REQUEUE] [RECOVERED] [REJOIN]

# f. Scalability
python -m src.master_sort bench --suite scalability --workers-list 1,2,4,6,9 --repeat 3

# tambahan analisis: merge di Master vs bertingkat
python -m src.master_sort bench --suite merge --size 10m --repeat 3
```

## Metrik dan definisi (untuk BAB III/IV)
- **Execution time**: dari data siap di Master sampai array terurut penuh di Master (di luar pembangkitan data & verifikasi). Dilaporkan sebagai **median** dari `--repeat` run.
- **Speedup**: `S vs seq = T_seq / T(W)`; `S vs 1W = T(1 worker) / T(W)`. **Efficiency** = `(S vs 1W) / W`. Gunakan `S vs 1W` untuk efficiency karena satu worker sudah memakai banyak core.
- **Throughput**: juta elemen/detik. **CPU/Memory**: Master (psutil, sampling 0.5 s) dan Worker (dilaporkan per task).
- **Recovery time**: sejak kegagalan *terdeteksi* sampai task yang di-requeue selesai di worker lain. **Detection time**: sejak task dikirim sampai kegagalan terdeteksi (≈ 0 s jika koneksi putus, ≈ 5 s jika senyap/kabel dicabut). Total delay = detection + recovery.
- **Imbalance** = busy terbesar / rata-rata busy (1.00 = seimbang). **merge%** = porsi merge serial di Master → hubungkan dengan **Amdahl**; transfer data → **communication overhead** (Pertemuan 8).

## Catatan untuk laporan
- **Baseline fair**: jalankan `seq` dan `local` pada PC dengan spesifikasi sama dengan worker (atau di master jika spesifikasinya setara), dan catat spesifikasi tiap node di BAB III.
- Cantumkan sumber aset: dataset = OpenStreetMap (Geofabrik) lengkap dengan URL, tanggal unduh, lisensi ODbL; rumus = Amdahl/Gustafson (Hennessy & Patterson; Gustafson 1988); `seed`, `size`, `dtype` untuk `--shuffle`.
- Batasan sistem: Master adalah single point of failure (kegagalan Master menghentikan job dan harus diulang dari awal); Byzantine fault tidak ditangani (hanya crash dan timing failure); beban sorting relatif homogen sehingga keunggulan dynamic baru terlihat pada Worker heterogen/lambat.
- Video: tampilkan 10 node, `dist` berjalan, lalu satu worker dimatikan.
- Batasan jujur: kode diuji pada localhost (3 worker); pengujian 10 node fisik dilakukan kelompok. Data dikirim lewat TCP dan diverifikasi, tetapi tanpa enkripsi (jaringan lab tertutup).
