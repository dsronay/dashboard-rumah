import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# =========================================
# 1. KONFIGURASI DASHBOARD
# =========================================
st.set_page_config(
    page_title="Dashboard Harga Rumah v2",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Dashboard Harga Rumah Jabodetabek v2")
st.markdown(
    """
    Dashboard eksplorasi **harga rumah** + **simulasi KPR**.  
    Fitur utama:
    - Filter listing berdasarkan kota, harga, luas, jumlah kamar, dll.
    - KPI ringkas (jumlah listing, harga rata-rata, dll).
    - Grafik perbandingan antar kota & distribusi harga.
    - Tabel data detail + download CSV.
    - 🏦 **Simulasi KPR** (pilih dari listing atau input manual).
    """
)

# =========================================
# 2. LOAD DATA
# =========================================
@st.cache_data
def load_data(path: str = "harga_rumah_clean.csv") -> pd.DataFrame:
    df = pd.read_csv(path)

    # Buang kolom index yang tidak perlu jika ada
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    # Pastikan tipe data numerik
    numeric_cols = ["price", "area", "building_area", "bedrooms", "bathrooms", "garage"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Harga per m² tanah (asumsi price dalam juta → hasil = juta/m²)
    df["price_per_m2"] = np.where(
        df["area"] > 0,
        df["price"] / df["area"],
        np.nan
    )

    return df

try:
    data = load_data()
except FileNotFoundError:
    st.error(
        "File `harga_rumah_clean.csv` tidak ditemukan. "
        "Pastikan file berada di folder yang sama dengan file aplikasi ini."
    )
    st.stop()

df = data.copy()

# =========================================
# 3. SIDEBAR FILTER
# =========================================
st.sidebar.header("🔎 Filter Data")

# Kota
kota_options = sorted(df["city"].dropna().unique().tolist())
filter_kota = st.sidebar.multiselect(
    "Pilih Kota:",
    options=kota_options,
    default=kota_options
)

# Range harga
min_price = float(df["price"].min())
max_price = float(df["price"].max())
filter_price = st.sidebar.slider(
    "Range Harga (dalam juta):",
    float(min_price),
    float(max_price),
    (float(min_price), float(max_price))
)

# Range luas tanah
min_area = float(df["area"].min())
max_area = float(df["area"].max())
filter_area = st.sidebar.slider(
    "Range Luas Tanah (m²):",
    float(min_area),
    float(max_area),
    (float(min_area), float(max_area))
)

# Minimal kamar tidur & kamar mandi
min_bedrooms = int(df["bedrooms"].min())
max_bedrooms = int(df["bedrooms"].max())
filter_bedrooms = st.sidebar.slider(
    "Minimal Jumlah Kamar Tidur:",
    min_bedrooms,
    max_bedrooms,
    min_bedrooms
)

min_bathrooms = int(df["bathrooms"].min())
max_bathrooms = int(df["bathrooms"].max())
filter_bathrooms = st.sidebar.slider(
    "Minimal Jumlah Kamar Mandi:",
    min_bathrooms,
    max_bathrooms,
    min_bathrooms
)

# Filter keyword judul/lokasi
keyword = st.sidebar.text_input(
    "Cari kata kunci (judul / lokasi):",
    value="",
    placeholder="contoh: kemang, bintaro, cluster, dll."
)

# Terapkan filter
df_filtered = df[
    (df["city"].isin(filter_kota)) &
    (df["price"].between(filter_price[0], filter_price[1])) &
    (df["area"].between(filter_area[0], filter_area[1])) &
    (df["bedrooms"] >= filter_bedrooms) &
    (df["bathrooms"] >= filter_bathrooms)
]

if keyword.strip():
    kw = keyword.strip().lower()
    df_filtered = df_filtered[
        df_filtered["title"].str.lower().str.contains(kw, na=False) |
        df_filtered["location"].str.lower().str.contains(kw, na=False)
    ]

# Handling jika tidak ada data setelah filter
if df_filtered.empty:
    st.warning("❗ Tidak ada data yang cocok dengan filter. Silakan atur ulang filter di sidebar.")
    st.stop()

# =========================================
# 4. KPI / METRICS
# =========================================
st.subheader("🔢 Ringkasan Utama (KPI)")

total_listing = len(df_filtered)
avg_price = df_filtered["price"].mean()
median_price = df_filtered["price"].median()
avg_area = df_filtered["area"].mean()
avg_price_m2 = df_filtered["price_per_m2"].mean()

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Jumlah Listing", f"{total_listing:,}")
col2.metric("Harga Rata-rata (juta)", f"{avg_price:,.0f}")
col3.metric("Median Harga (juta)", f"{median_price:,.0f}")
col4.metric("Luas Tanah Rata-rata (m²)", f"{avg_area:,.1f}")
col5.metric("Rata-rata Harga per m² (juta/m²)", f"{avg_price_m2:,.2f}")

# Insight singkat kota termahal (median)
st.markdown("### 💡 Insight Singkat")
city_price = (
    df_filtered.groupby("city")["price"]
    .median()
    .sort_values(ascending=False)
    .reset_index()
)
top_city = city_price.iloc[0]
st.write(
    f"- Kota dengan **median harga tertinggi** (data terfilter): "
    f"**{top_city['city']}** (~{top_city['price']:,.0f} juta)"
)

# =========================================
# 5. TAB MENU (tambah tab Simulasi KPR)
# =========================================
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Overview Kota", "📈 Distribusi & Scatter", "📄 Data Detail", "🏦 Simulasi KPR"]
)

# -------------------------------------------------
# TAB 1 - OVERVIEW KOTA
# -------------------------------------------------
with tab1:
    st.subheader("📊 Perbandingan Antar Kota")

    # Median harga per kota
    st.markdown("**Median Harga per Kota (juta)**")
    city_price = (
        df_filtered.groupby("city")["price"]
        .median()
        .sort_values(ascending=False)
        .reset_index()
    )

    fig1, ax1 = plt.subplots(figsize=(8, 4))
    sns.barplot(
        data=city_price,
        x="city",
        y="price",
        ax=ax1
    )
    ax1.set_xlabel("Kota")
    ax1.set_ylabel("Median Harga (juta)")
    ax1.tick_params(axis='x', rotation=45)
    st.pyplot(fig1)

    # Luas rata-rata per kota
    st.markdown("**Luas Tanah Rata-rata per Kota (m²)**")
    city_area = (
        df_filtered.groupby("city")["area"]
        .mean()
        .sort_values(ascending=False)
        .reset_index()
    )

    fig2, ax2 = plt.subplots(figsize=(8, 4))
    sns.barplot(
        data=city_area,
        x="city",
        y="area",
        ax=ax2
    )
    ax2.set_xlabel("Kota")
    ax2.set_ylabel("Luas Tanah Rata-rata (m²)")
    ax2.tick_params(axis='x', rotation=45)
    st.pyplot(fig2)

    # Top N listing termahal
    st.markdown("**Top Listing Termahal (berdasarkan harga)**")
    top_n = st.slider("Tampilkan berapa listing termahal:", 5, 30, 10)
    top_listings = (
        df_filtered.sort_values("price", ascending=False)
        .head(top_n)[
            ["city", "location", "title", "price", "area",
             "building_area", "bedrooms", "bathrooms", "garage"]
        ]
    )
    st.dataframe(top_listings, use_container_width=True)

# -------------------------------------------------
# TAB 2 - DISTRIBUSI & SCATTER
# -------------------------------------------------
with tab2:
    st.subheader("📈 Distribusi Harga & Scatter Plot")

    col_d1, col_d2 = st.columns(2)

    # Histogram harga
    with col_d1:
        st.markdown("**Distribusi Harga (juta)**")
        fig3, ax3 = plt.subplots(figsize=(6, 4))
        sns.histplot(df_filtered["price"], bins=30, kde=True, ax=ax3)
        ax3.set_xlabel("Harga (juta)")
        st.pyplot(fig3)

    # Boxplot harga per kota
    with col_d2:
        st.markdown("**Boxplot Harga per Kota**")
        df_box = df_filtered.copy()
        fig4, ax4 = plt.subplots(figsize=(6, 4))
        sns.boxplot(
            data=df_box,
            x="city",
            y="price",
            ax=ax4
        )
        ax4.set_xlabel("Kota")
        ax4.set_ylabel("Harga (juta)")
        ax4.tick_params(axis='x', rotation=45)
        st.pyplot(fig4)

    st.markdown("**Scatter Plot: Luas Tanah vs Harga (warna berdasarkan kota)**")
    fig5, ax5 = plt.subplots(figsize=(8, 5))
    sns.scatterplot(
        data=df_filtered,
        x="area",
        y="price",
        hue="city",
        alpha=0.7,
        ax=ax5
    )
    ax5.set_xlabel("Luas Tanah (m²)")
    ax5.set_ylabel("Harga (juta)")
    ax5.legend(bbox_to_anchor=(1.05, 1), loc="upper left", borderaxespad=0.)
    st.pyplot(fig5)

# -------------------------------------------------
# TAB 3 - DATA DETAIL
# -------------------------------------------------
with tab3:
    st.subheader("📄 Data Detail Listing (Setelah Filter)")

    # Pilih kolom yang mau ditampilkan
    default_cols = [
        "city", "location", "title", "price", "area", "building_area",
        "bedrooms", "bathrooms", "garage", "price_per_m2"
    ]
    cols_available = [c for c in default_cols if c in df_filtered.columns]

    selected_cols = st.multiselect(
        "Pilih kolom yang ingin ditampilkan:",
        options=df_filtered.columns.tolist(),
        default=cols_available
    )

    st.dataframe(df_filtered[selected_cols], use_container_width=True)

    # Download CSV hasil filter
    st.markdown("### 💾 Download Data")
    csv = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download CSV (data terfilter)",
        data=csv,
        file_name="harga_rumah_filtered.csv",
        mime="text/csv",
    )

    st.markdown(
        "> Catatan: Data yang di-download sudah sesuai dengan semua filter yang dipilih di sidebar."
    )

# -------------------------------------------------
# TAB 4 - SIMULASI KPR
# -------------------------------------------------
with tab4:
    st.subheader("🏦 Simulasi KPR")

    st.markdown(
        """
        Simulasi ini menggunakan skema cicilan **anuitas** (cicilan tetap per bulan).  
        Asumsi: kolom `price` di data = **harga rumah dalam juta rupiah**.
        """
    )

    # Pilih mode: dari listing atau manual
    mode = st.radio(
        "Pilih sumber harga rumah:",
        options=["Pilih dari listing terfilter", "Input manual"],
        horizontal=True
    )

    # Tentukan harga rumah (dalam juta)
    harga_juta = None
    info_listing = ""

    if mode == "Pilih dari listing terfilter":
        # Buat opsi selectbox dari df_filtered
        # Tampilkan city - location - (harga juta)
        df_sel = df_filtered.copy()
        df_sel = df_sel.reset_index(drop=True)

        def make_label(row):
            return f"[{row['city']}] {str(row['location'])[:25]}... | {row['price']:,.0f} jt"

        options = [make_label(row) for _, row in df_sel.iterrows()]
        idx = st.selectbox(
            "Pilih listing:",
            options=range(len(df_sel)),
            format_func=lambda i: options[i]
        )

        selected_row = df_sel.iloc[idx]
        harga_juta = float(selected_row["price"])
        info_listing = (
            f"Listing terpilih: **{selected_row['title']}** "
            f"di **{selected_row['location']} ({selected_row['city']})**"
        )
        st.info(info_listing)

    else:
        harga_juta = st.number_input(
            "Masukkan harga rumah (dalam juta rupiah):",
            min_value=50.0,
            max_value=50_000.0,
            value=1_000.0,
            step=50.0
        )

    st.markdown("---")

    # Parameter KPR
    col_k1, col_k2, col_k3 = st.columns(3)

    with col_k1:
        dp_persen = st.slider("DP (%)", 0, 90, 20)

    with col_k2:
        bunga_tahunan = st.slider("Bunga Tahunan (%)", 1.0, 20.0, 8.0, step=0.1)

    with col_k3:
        tenor_tahun = st.slider("Tenor (tahun)", 1, 30, 15)

    # Tombol hitung
    if st.button("💰 Hitung Simulasi KPR"):
        if harga_juta is None or harga_juta <= 0:
            st.error("Harga rumah tidak valid.")
        else:
            # Konversi ke rupiah
            harga_rumah_rp = harga_juta * 1_000_000

            # Hitung DP & pinjaman
            dp_rp = harga_rumah_rp * dp_persen / 100
            pokok_pinjaman = harga_rumah_rp - dp_rp

            # Parameter anuitas
            i_bulanan = bunga_tahunan / 12 / 100
            n_bulan = tenor_tahun * 12

            if i_bulanan > 0:
                cicilan_bulanan = pokok_pinjaman * i_bulanan / (1 - (1 + i_bulanan) ** (-n_bulan))
            else:
                cicilan_bulanan = pokok_pinjaman / n_bulan

            total_bayar = cicilan_bulanan * n_bulan
            total_bunga = total_bayar - pokok_pinjaman

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Harga Rumah", f"Rp {harga_rumah_rp:,.0f}")
            col_m2.metric("DP", f"Rp {dp_rp:,.0f} ({dp_persen}%)")
            col_m3.metric("Pokok Pinjaman", f"Rp {pokok_pinjaman:,.0f}")
            col_m4.metric("Cicilan / bulan", f"Rp {cicilan_bulanan:,.0f}")

            st.markdown("### 📊 Ringkasan Simulasi")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.write(f"- Tenor: **{tenor_tahun} tahun** ({n_bulan} bulan)")
                st.write(f"- Bunga tahunan: **{bunga_tahunan:.2f}%**")
                st.write(f"- Bunga efektif per bulan: **{i_bulanan*100:.3f}%**")
            with col_s2:
                st.write(f"- Total yang dibayar ke bank: **Rp {total_bayar:,.0f}**")
                st.write(f"- Total bunga selama tenor: **Rp {total_bunga:,.0f}**")
                st.write(f"- Rasio total bunga / pokok: **{total_bunga/pokok_pinjaman:.2f}x pokok**")

            st.markdown(
                "> Catatan: Simulasi ini hanya ilustrasi kasar (flat anuitas), belum "
                "memperhitungkan biaya lain seperti provisi, administrasi, asuransi, dll."
            )

