import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# =========================================
# 1. KONFIGURASI DASHBOARD
# =========================================
st.set_page_config(
    page_title="Dashboard Harga Rumah Jabodetabek",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Dashboard Harga Rumah Jabodetabek")
st.markdown(
    """
    Dashboard eksplorasi **harga rumah** berdasarkan data listing properti.  
    Fitur utama:
    - Filter berdasarkan kota, harga, luas tanah, kamar, dll.
    - KPI ringkas (jumlah listing, harga rata-rata, luas rata-rata, harga per m²)
    - Grafik perbandingan antar kota, distribusi harga, dan scatter plot
    - Tabel data detail + download CSV hasil filter
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

# Copy untuk diolah
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

# Insight singkat kota termahal
st.markdown("### 💡 Insight Singkat")
city_price = (
    df_filtered.groupby("city")["price"]
    .median()
    .sort_values(ascending=False)
    .reset_index()
)

top_city = city_price.iloc[0]
st.write(
    f"- Kota dengan **median harga tertinggi** saat ini: "
    f"**{top_city['city']}** (~{top_city['price']:,.0f} juta)"
)

# =========================================
# 5. TAB MENU
# =========================================
tab1, tab2, tab3 = st.tabs(
    ["📊 Overview Kota", "📈 Distribusi & Scatter", "📄 Data Detail"]
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
    st.markdown("**Top 10 Listing Termahal (berdasarkan harga)**")
    top_n = st.slider("Tampilkan berapa listing termahal:", 5, 30, 10)
    top_listings = (
        df_filtered.sort_values("price", ascending=False)
        .head(top_n)[["city", "location", "title", "price", "area", "building_area", "bedrooms", "bathrooms", "garage"]]
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
        # Untuk boxplot, batasi kota yang tampil jika terlalu banyak
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
    default_cols = ["city", "location", "title", "price", "area", "building_area", "bedrooms", "bathrooms", "garage", "price_per_m2"]
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

