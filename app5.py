"""
Dashboard Pekerjaan - Streamlit + Supabase (PostgreSQL + Storage)
Fitur:
- Tambah pekerjaan baru (nama, urgensi, status, keterangan, foto)
- Lihat daftar pekerjaan dalam bentuk kanban 3 kolom
- Edit status pekerjaan
- Hapus pekerjaan
- Filter berdasarkan urgensi & pencarian nama
- Data & foto tersimpan permanen di Supabase (tidak hilang saat aplikasi sleep/restart)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import io
from supabase import create_client

# ---------- KONFIGURASI ----------
URGENSI_OPTIONS = ["Rendah", "Sedang", "Tinggi"]
STATUS_OPTIONS = ["Belum Dikerjakan", "Sedang Dikerjakan", "Sudah Dikerjakan"]

URGENSI_COLOR = {"Rendah": "🟢", "Sedang": "🟡", "Tinggi": "🔴"}
STATUS_COLOR = {
    "Belum Dikerjakan": " ",
    "Sedang Dikerjakan": " ",
    "Sudah Dikerjakan": " ",
}

NAMA_TABEL = "pekerjaan"
NAMA_BUCKET = "foto-pekerjaan"


# ---------- KONEKSI SUPABASE ----------
@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


supabase = get_supabase()


# ---------- DATABASE ----------
def tambah_pekerjaan(nama, urgensi, status, keterangan, foto_url):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    supabase.table(NAMA_TABEL).insert(
        {
            "nama_pekerjaan": nama,
            "urgensi": urgensi,
            "status": status,
            "keterangan": keterangan,
            "foto_path": foto_url,
            "dibuat_pada": now,
            "diubah_pada": now,
        }
    ).execute()


def ambil_semua_pekerjaan():
    res = supabase.table(NAMA_TABEL).select("*").order("id", desc=True).execute()
    kolom = [
        "id", "nama_pekerjaan", "urgensi", "status",
        "keterangan", "foto_path", "dibuat_pada", "diubah_pada",
    ]
    if not res.data:
        return pd.DataFrame(columns=kolom)
    return pd.DataFrame(res.data)


def update_status(id_pekerjaan, status_baru):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    supabase.table(NAMA_TABEL).update(
        {"status": status_baru, "diubah_pada": now}
    ).eq("id", id_pekerjaan).execute()


def hapus_pekerjaan(id_pekerjaan):
    supabase.table(NAMA_TABEL).delete().eq("id", id_pekerjaan).execute()


# ---------- HELPER ----------
def simpan_foto(uploaded_file):
    """Upload foto ke Supabase Storage, kembalikan URL publiknya."""
    if uploaded_file is None:
        return None

    image = Image.open(uploaded_file)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)

    nama_file = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}.jpg"
    supabase.storage.from_(NAMA_BUCKET).upload(
        nama_file,
        buffer.getvalue(),
        {"content-type": "image/jpeg"},
    )
    return supabase.storage.from_(NAMA_BUCKET).get_public_url(nama_file)

# ---------- APLIKASI ----------
st.set_page_config(page_title="Dashboard Pekerjaan", page_icon="📋", layout="wide")

# ---------- MODE MAINTENANCE ----------
# Diatur lewat Streamlit Secrets: MAINTENANCE_MODE = true / false
# Ubah nilainya kapan saja tanpa perlu ubah kode atau upload ulang ke GitHub.
if st.secrets.get("MAINTENANCE_MODE", False):
    st.title("🛠️ Sedang Maintenance")
    st.info(
        "Dashboard sedang dalam perbaikan/pemeliharaan. "
        "Silakan coba akses lagi beberapa saat lagi."
    )
    st.stop()

st.title("📋 Dashboard Pekerjaan")

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
                foto_url = simpan_foto(foto)
                tambah_pekerjaan(nama, urgensi, status, keterangan, foto_url)
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
            filter_urgensi = st.multiselect("Filter Urgensi", URGENSI_OPTIONS)
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
                            ada_foto = pd.notna(row["foto_path"]) and str(row["foto_path"]).strip() != ""
                            if ada_foto:
                                lihat_foto = st.checkbox("Lihat Foto", key=f"foto_{row['id']}")
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
