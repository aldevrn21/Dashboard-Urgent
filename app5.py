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

        # --- RINGKASAN ---
        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Pekerjaan", len(df_filtered))
        c2.metric("Belum Dikerjakan", (df_filtered["status"] == "Belum Dikerjakan").sum())
        c3.metric("Sedang Dikerjakan", (df_filtered["status"] == "Sedang Dikerjakan").sum())
        c4.metric("Sudah Dikerjakan", (df_filtered["status"] == "Sudah Dikerjakan").sum())
        st.divider()

        # --- KOTAK WARNA URGENSI (ditampilkan di judul kartu) ---
        KOTAK_URGENSI = {"Tinggi": "🟥", "Sedang": "🟨", "Rendah": "🟩"}

        # --- TAMPILAN KANBAN (STATUS MENDATAR, KE BAWAH ISI KARTU) ---
        kolom_status = st.columns(len(STATUS_OPTIONS))

        for kolom, status_saat_ini in zip(kolom_status, STATUS_OPTIONS):
            with kolom:
                df_status = df_filtered[df_filtered["status"] == status_saat_ini]

                st.markdown(f"#### {status_saat_ini} ({len(df_status)})")
                st.markdown("---")

                if df_status.empty:
                    st.caption("Tidak ada pekerjaan di status ini.")

                for _, row in df_status.iterrows():
                    kotak = KOTAK_URGENSI.get(row["urgensi"], "⬜")

                    with st.expander(f"{kotak} {row['nama_pekerjaan']}"):
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

        # --- EKSPOR ---
        st.divider()
        csv = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Unduh Data (CSV)",
            data=csv,
            file_name="daftar_pekerjaan.csv",
            mime="text/csv",
        )
