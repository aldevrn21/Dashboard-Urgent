"""
Dashboard Pekerjaan - Streamlit + SQLite
Fitur:
- Tambah pekerjaan baru (nama, urgensi, status, keterangan, foto)
- Lihat daftar pekerjaan dalam bentuk tabel & kartu
- Edit status pekerjaan
- Hapus pekerjaan
- Filter berdasarkan status & urgensi
"""

import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
from PIL import Image

# ---------- KONFIGURASI ----------
DB_PATH = "pekerjaan.db"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

URGENSI_OPTIONS = ["Rendah", "Sedang", "Tinggi"]
STATUS_OPTIONS = ["Belum Dikerjakan", "Sedang Dikerjakan", "Sudah Dikerjakan"]

URGENSI_COLOR = {"Rendah": "🟢", "Sedang": "🟡", "Tinggi": "🔴"}
STATUS_COLOR = {
    "Belum Dikerjakan": "⚪",
    "Sedang Dikerjakan": "🔵",
    "Sudah Dikerjakan": "✅",
}


# ---------- DATABASE ----------
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pekerjaan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_pekerjaan TEXT NOT NULL,
            urgensi TEXT NOT NULL,
            status TEXT NOT NULL,
            keterangan TEXT,
            foto_path TEXT,
            dibuat_pada TEXT,
            diubah_pada TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def tambah_pekerjaan(nama, urgensi, status, keterangan, foto_path):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """
        INSERT INTO pekerjaan (nama_pekerjaan, urgensi, status, keterangan, foto_path, dibuat_pada, diubah_pada)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (nama, urgensi, status, keterangan, foto_path, now, now),
    )
    conn.commit()
    conn.close()


def ambil_semua_pekerjaan():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM pekerjaan ORDER BY id DESC", conn)
    conn.close()
    return df


def update_status(id_pekerjaan, status_baru):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "UPDATE pekerjaan SET status = ?, diubah_pada = ? WHERE id = ?",
        (status_baru, now, id_pekerjaan),
    )
    conn.commit()
    conn.close()


def hapus_pekerjaan(id_pekerjaan):
    # ambil path foto dulu untuk dihapus juga filenya
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT foto_path FROM pekerjaan WHERE id = ?", (id_pekerjaan,))
    row = cur.fetchone()
    if row and row[0] and os.path.exists(row[0]):
        os.remove(row[0])
    cur.execute("DELETE FROM pekerjaan WHERE id = ?", (id_pekerjaan,))
    conn.commit()
    conn.close()


# ---------- HELPER ----------
def simpan_foto(uploaded_file):
    if uploaded_file is None:
        return None
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    ext = os.path.splitext(uploaded_file.name)[1]
    filename = f"{timestamp}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    image = Image.open(uploaded_file)
    image.save(filepath)
    return filepath


# ---------- APLIKASI ----------
st.set_page_config(page_title="Dashboard Pekerjaan", page_icon="📋", layout="wide")


# ---------- LOGIN / PROTEKSI PASSWORD ----------
def cek_password():
    """Menampilkan form password. Return True kalau sudah login, False kalau belum."""

    def password_dimasukkan():
        password_benar = st.secrets.get("APP_PASSWORD", None)
        if password_benar is None:
            st.session_state["password_ok"] = True  # kalau belum di-set, jangan kunci total
            return
        if st.session_state.get("input_password") == password_benar:
            st.session_state["password_ok"] = True
        else:
            st.session_state["password_ok"] = False

    if st.session_state.get("password_ok", False):
        return True

    st.title("📋 Dashboard Pekerjaan")
    st.markdown("Masukkan password untuk mengakses dashboard.")
    st.text_input(
        "Password",
        type="password",
        key="input_password",
        on_change=password_dimasukkan,
    )

    if "password_ok" in st.session_state and not st.session_state["password_ok"]:
        st.error("Password salah, coba lagi.")

    if st.secrets.get("APP_PASSWORD", None) is None:
        st.warning(
            "⚠️ Password belum di-set di Secrets. Tambahkan APP_PASSWORD di menu "
            "Settings > Secrets aplikasi Streamlit Anda, lalu refresh halaman ini."
        )

    return False


if not cek_password():
    st.stop()


init_db()

st.title("📋 Dashboard Pekerjaan")
st.caption("Kelola dan pantau status pekerjaan tim secara real-time")

tab_tambah, tab_daftar = st.tabs(["➕ Tambah Pekerjaan", "📑 Daftar Pekerjaan"])

# ===== TAB TAMBAH =====
with tab_tambah:
    st.subheader("Tambah Pekerjaan Baru")
    with st.form("form_tambah", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nama = st.text_input("Pekerjaan *")
            urgensi = st.selectbox("Tingkat Urgensi *", URGENSI_OPTIONS)
        with col2:
            status = st.selectbox("Status *", STATUS_OPTIONS)
            foto = st.file_uploader("Foto Pekerjaan", type=["png", "jpg", "jpeg"])

        keterangan = st.text_area("Keterangan")

        submitted = st.form_submit_button("Simpan Pekerjaan", use_container_width=True)
        if submitted:
            if not nama:
                st.error("Nama pekerjaan wajib diisi.")
            else:
                foto_path = simpan_foto(foto)
                tambah_pekerjaan(nama, urgensi, status, keterangan, foto_path)
                st.success(f"Pekerjaan '{nama}' berhasil ditambahkan.")

# ===== TAB DAFTAR =====
with tab_daftar:
    df = ambil_semua_pekerjaan()

    if df.empty:
        st.info("Belum ada data pekerjaan. Tambahkan lewat tab 'Tambah Pekerjaan'.")
    else:
        # --- FILTER ---
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            filter_urgensi = st.multiselect("Filter Urgensi", URGENSI_OPTIONS, default=URGENSI_OPTIONS)
        with col_f2:
            cari = st.text_input("Cari nama pekerjaan")

        df_filtered = df if not filter_urgensi else df[df["urgensi"].isin(filter_urgensi)]
        if cari:
            df_filtered = df_filtered[df_filtered["nama_pekerjaan"].str.contains(cari, case=False, na=False)]

        # --- WARNA LATAR BELAKANG PER KOLOM STATUS ---
        # Dipilih sengaja beda dari warna urgensi (merah/kuning/hijau) supaya tidak membingungkan:
        # abu-abu (netral, belum mulai) -> biru (sedang berjalan) -> ungu tua (selesai/final)
        KEY_KOLOM = {
            "Belum Dikerjakan": "kolom-belum",
            "Sedang Dikerjakan": "kolom-sedang",
            "Sudah Dikerjakan": "kolom-sudah",
        }
        WARNA_KOLOM = {
            "Belum Dikerjakan": "#4a4a4a",   # abu-abu gelap
            "Sedang Dikerjakan": "#2f6f9f",  # biru
            "Sudah Dikerjakan": "#2f6b4a",   # hijau tua gelap (beda shade dari badge urgensi hijau terang)
        }
        WARNA_TOTAL = "#3a3a4a"  # warna netral khusus kotak "Total Pekerjaan"

        css_kolom = "".join(
            f".st-key-{KEY_KOLOM[s]} {{ background-color: {WARNA_KOLOM[s]}; "
            f"border-radius: 12px; padding: 16px; }}"
            for s in STATUS_OPTIONS
        )
        css_kolom += "".join(
            f".st-key-metrik-{KEY_KOLOM[s]} {{ background-color: {WARNA_KOLOM[s]}; "
            f"border-radius: 10px; padding: 12px; }}"
            for s in STATUS_OPTIONS
        )
        css_kolom += (
            f".st-key-metrik-total {{ background-color: {WARNA_TOTAL}; "
            f"border-radius: 10px; padding: 12px; }}"
        )
        css_kolom += """
            .st-key-metrik-total [data-testid="stMetricLabel"],
            .st-key-metrik-total [data-testid="stMetricValue"],
            [class*="st-key-metrik-kolom-"] [data-testid="stMetricLabel"],
            [class*="st-key-metrik-kolom-"] [data-testid="stMetricValue"] {
                color: #ffffff !important;
            }
            [class*="st-key-kolom-"] h4 {
                color: #ffffff !important;
            }
            [class*="st-key-kolom-"],
            [class*="st-key-kolom-"] > div,
            [class*="st-key-kolom-"] [data-testid="stVerticalBlock"] {
                gap: 0.35rem !important;
            }
            [class*="st-key-kolom-"] .element-container {
                margin-bottom: 0.35rem !important;
            }
        """
        st.markdown(f"<style>{css_kolom}</style>", unsafe_allow_html=True)

        # --- RINGKASAN (kotak angka diwarnai sesuai kolom masing-masing) ---
        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        with c1, st.container(key="metrik-total"):
            st.metric("Total Pekerjaan", len(df_filtered))
        with c2, st.container(key=f"metrik-{KEY_KOLOM['Belum Dikerjakan']}"):
            st.metric("Belum Dikerjakan", (df_filtered["status"] == "Belum Dikerjakan").sum())
        with c3, st.container(key=f"metrik-{KEY_KOLOM['Sedang Dikerjakan']}"):
            st.metric("Sedang Dikerjakan", (df_filtered["status"] == "Sedang Dikerjakan").sum())
        with c4, st.container(key=f"metrik-{KEY_KOLOM['Sudah Dikerjakan']}"):
            st.metric("Sudah Dikerjakan", (df_filtered["status"] == "Sudah Dikerjakan").sum())
        st.divider()

        # --- WARNA BADGE URGENSI ---
        WARNA_URGENSI = {
            "Tinggi": "#e05555",   # merah
            "Sedang": "#e0c040",  # kuning
            "Rendah": "#4caf7d",   # hijau
        }

        # --- TAMPILAN KANBAN (STATUS MENDATAR) ---
        kolom_status = st.columns(len(STATUS_OPTIONS))

        for kolom, status_saat_ini in zip(kolom_status, STATUS_OPTIONS):
            with kolom, st.container(key=KEY_KOLOM[status_saat_ini]):
                df_status = df_filtered[df_filtered["status"] == status_saat_ini]

                st.markdown(f"#### {STATUS_COLOR[status_saat_ini]} {status_saat_ini} ({len(df_status)})")
                st.markdown("---")

                if df_status.empty:
                    st.caption("Tidak ada pekerjaan di status ini.")

                for _, row in df_status.iterrows():
                    warna = WARNA_URGENSI.get(row["urgensi"], "#888888")

                    kunci_buka = f"buka_{row['id']}"
                    if kunci_buka not in st.session_state:
                        st.session_state[kunci_buka] = False

                    kunci_tombol = f"btn_{row['id']}"
                    ikon = "▴" if st.session_state[kunci_buka] else "▾"
                    radius_tombol = "8px 8px 0 0" if st.session_state[kunci_buka] else "8px"

                    st.markdown(
                        f"""
                        <style>
                        .st-key-{kunci_tombol} button {{
                            background-color: {warna} !important;
                            color: #ffffff !important;
                            font-weight: 600;
                            text-shadow: 0 1px 2px rgba(0,0,0,0.4);
                            border: none;
                            border-radius: {radius_tombol} !important;
                            text-align: left !important;
                            position: relative;
                            padding-right: 34px !important;
                        }}
                        .st-key-{kunci_tombol} button p {{
                            text-align: left !important;
                        }}
                        .st-key-{kunci_tombol} button::after {{
                            content: "{ikon}";
                            position: absolute;
                            right: 14px;
                            top: 50%;
                            transform: translateY(-50%);
                        }}
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

                    if st.button(
                        row["nama_pekerjaan"],
                        key=kunci_tombol,
                        use_container_width=True,
                    ):
                        st.session_state[kunci_buka] = not st.session_state[kunci_buka]
                        st.rerun()

                    if st.session_state[kunci_buka]:
                        kunci_detail = f"detail_{row['id']}"
                        st.markdown(
                            f"""
                            <style>
                            .st-key-{kunci_detail} {{
                                background-color: {warna}2b;
                                border: 1px solid {warna};
                                border-top: none;
                                border-radius: 0 0 10px 10px;
                                padding: 14px;
                                margin-top: -12px !important;
                            }}
                            .st-key-{kunci_detail} [data-testid="stCaptionContainer"],
                            .st-key-{kunci_detail} small {{
                                color: #f0f0f0 !important;
                            }}
                            </style>
                            """,
                            unsafe_allow_html=True,
                        )
                        with st.container(key=kunci_detail):
                            ada_foto = pd.notna(row["foto_path"]) and os.path.exists(str(row["foto_path"]))
                            if ada_foto:
                                lihat_foto = st.checkbox("📷 Lihat Foto", key=f"foto_{row['id']}")
                                if lihat_foto:
                                    st.image(row["foto_path"], use_container_width=True)

                            if pd.notna(row["keterangan"]) and str(row["keterangan"]).strip():
                                st.caption(row["keterangan"])
                            st.caption(f"Diubah: {row['diubah_pada']}")

                            status_baru = st.selectbox(
                                "Pindahkan ke",
                                STATUS_OPTIONS,
                                index=STATUS_OPTIONS.index(row["status"]),
                                key=f"status_{row['id']}",
                                label_visibility="collapsed",
                            )
                            if status_baru != row["status"]:
                                update_status(row["id"], status_baru)
                                st.rerun()

                            if st.button(
                                "🗑️ Hapus", key=f"hapus_{row['id']}", use_container_width=True
                            ):
                                hapus_pekerjaan(row["id"])
                                st.rerun()

                    st.write("")

        # --- EKSPOR ---
        st.divider()
        csv = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Unduh Data (CSV)",
            data=csv,
            file_name="daftar_pekerjaan.csv",
            mime="text/csv",
        )
