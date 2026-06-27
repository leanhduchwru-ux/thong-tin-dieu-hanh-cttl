import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as ob
import datetime
import os
import threading
import time

# Import các hàm cào dữ liệu từ scraper
import scraper

st.set_page_config(
    page_title="Công ty TNHH MTV Khai thác công trình Thủy lợi Hải Dương",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Khởi động luồng scheduler ngầm nếu chưa khởi động
if "scheduler_started" not in st.session_state:
    scraper.init_db()
    scraper.start_scheduler()
    st.session_state["scheduler_started"] = True

# --- CẤU HÌNH GIAO DIỆN SÁNG / TỐI (DAY / NIGHT MODE) ---
if "theme" not in st.session_state:
    st.session_state["theme"] = "Ban ngày ☀️"

# Thanh bên (Sidebar) cài đặt
with st.sidebar:
    st.image("https://thuyloihaiduong.evina.vn/upload/images/logos/thuyloihaiduong_logo.png", width=150)
    st.header("Cài đặt hệ thống")
    st.markdown("---")
    
    # Nút chuyển đổi giao diện sáng tối
    app_theme = st.radio(
        "Chế độ hiển thị",
        ["Ban ngày ☀️", "Ban đêm 🌙"],
        index=0 if st.session_state["theme"] == "Ban ngày ☀️" else 1
    )
    st.session_state["theme"] = app_theme
    
    st.markdown("---")

# Định nghĩa bảng màu chuyên nghiệp độ tương phản cao tùy thuộc vào Chế độ hiển thị
if st.session_state["theme"] == "Ban đêm 🌙":
    bg_color = "#0f172a"          # slate-900 (Nền tối sâu)
    text_color = "#f8fafc"        # slate-50 (Chữ trắng sáng rõ)
    card_bg = "#1e293b"           # slate-800 (Nền thẻ tối)
    card_border = "#3b82f6"       # Màu viền xanh dương nổi bật để nhìn rõ sắc nét ban đêm
    metric_color = "#38bdf8"      # Màu chỉ số chính xanh dương sáng
    sec_text_color = "#cbd5e1"    # slate-300
    plotly_template = "plotly_dark"
    plotly_bg = "#1e293b"
    plotly_text = "#f8fafc"
    grid_color = "#334155"
    axis_color = "#94a3b8"
else:
    bg_color = "#ffffff"          # Nền sáng
    text_color = "#0f172a"        # slate-900 (Chữ đen sẫm tương phản tốt)
    card_bg = "#f1f5f9"           # slate-100 (Nền thẻ xám nhạt)
    card_border = "#1e40af"       # Viền xanh đậm sắc nét ban ngày
    metric_color = "#1d4ed8"      # Màu chỉ số chính xanh đậm
    sec_text_color = "#475569"    # slate-600
    plotly_template = "plotly_white"
    plotly_bg = "#ffffff"
    plotly_text = "#0f172a"
    grid_color = "#e2e8f0"
    axis_color = "#475569"

# Nhúng CSS tùy chỉnh để định hình Times New Roman và phối màu tương phản cao
st.markdown(f"""
<style>
    /* Chuyển toàn bộ font chữ sang Times New Roman */
    html, body, [class*="css"], .stApp, p, span, label, h1, h2, h3, h4, h5, h6, input, button, select, textarea, div {{
        font-family: 'Times New Roman', Times, serif !important;
    }}
    
    /* Đồng bộ nền trang sáng / tối */
    .stApp {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}
    
    /* Màu chữ chính cho tiêu đề và nội dung */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stText, span {{
        color: {text_color} !important;
    }}

    /* Định dạng thanh bên (Sidebar) */
    section[data-testid="stSidebar"] {{
        background-color: {card_bg} !important;
        border-right: 2px solid {card_border} !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: {text_color} !important;
    }}
    
    /* Hộp thẻ hiển thị thông số (Metric Card) độ tương phản cao, sắc nét */
    .metric-card {{
        background-color: {card_bg} !important;
        border: 2px solid {card_border} !important;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
        color: {text_color} !important;
    }}
    .metric-value {{
        font-size: 26px;
        font-weight: 700;
        color: {metric_color} !important;
        margin-bottom: 5px;
    }}
    .metric-label {{
        font-size: 15px;
        color: {sec_text_color} !important;
        font-weight: 500;
    }}
    .warning-text {{
        color: #ef4444 !important;
        font-weight: bold;
    }}
    .success-text {{
        color: #22c55e !important;
        font-weight: bold;
    }}
</style>
""", unsafe_allow_html=True)

def get_db_connection():
    return sqlite3.connect(scraper.DB_PATH)

def load_data():
    conn = get_db_connection()
    df_rain = pd.read_sql_query("SELECT * FROM rainfall ORDER BY timestamp DESC", conn)
    df_struct = pd.read_sql_query("SELECT * FROM structures ORDER BY timestamp DESC", conn)
    df_salinity = pd.read_sql_query("SELECT * FROM salinity ORDER BY timestamp DESC", conn)
    df_weather = pd.read_sql_query("SELECT * FROM weather ORDER BY timestamp DESC", conn)
    conn.close()
    return df_rain, df_struct, df_salinity, df_weather

# --- TRANG CHỦ & TIÊU ĐỀ ---
st.title("🏢 Công ty TNHH MTV Khai thác công trình Thủy lợi Hải Dương")
st.markdown("Hệ thống tự động thu thập và phân tích dữ liệu mực nước, lượng mưa và độ mặn định kỳ mỗi **2 giờ**.")

# Cài đặt thanh bên với các liên kết nguồn dữ liệu chính thức
with st.sidebar:
    last_update_info = scraper.get_last_update()
    if last_update_info:
        st.subheader("Trạng thái cập nhật")
        st.caption(f"**Lần cuối:** {last_update_info['timestamp']}")
        st.caption(f"**Trạng thái:** {last_update_info['status']}")
        st.info(last_update_info['message'])
    
    st.markdown("---")
    # Thay thế nút Cập nhật thủ công thành "Xem dữ liệu thời gian thực"
    if st.button("Xem dữ liệu thời gian thực", width="stretch"):
        with st.spinner("Đang kết nối và tải dữ liệu mới..."):
            msg = scraper.run_all_scrapers()
            st.success("Đã hoàn tất tải dữ liệu mới nhất!")
            st.rerun()
            
    st.markdown("---")
    st.markdown("**Nguồn dữ liệu:**")
    st.markdown("1. [https://thuyloihaiduong.evina.vn/](https://thuyloihaiduong.evina.vn/)")
    st.markdown("2. [https://www.vrain.vn/landing](https://www.vrain.vn/landing)")
    st.markdown("3. [https://vnbaolut.net/thoi-tiet-hai-duong](https://vnbaolut.net/thoi-tiet-hai-duong)")
    st.markdown("4. [https://bhh.com.vn/](https://bhh.com.vn/)")

# Tải dữ liệu từ database
df_rain, df_struct, df_salinity, df_weather = load_data()

# ----------------- PHẦN 1: THÔNG TIN TỔNG QUAN (KPIs) -----------------
st.subheader("📌 Chỉ số giám sát tức thời")
col1, col2, col3, col4 = st.columns(4)

# 1. Nhiệt độ thời tiết hiện tại
if not df_weather.empty:
    latest_w = df_weather.iloc[0]
    col1.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{latest_w['temperature']:.1f} °C</div>
        <div class="metric-label">Thời tiết Hải Dương (Cảm giác: {latest_w['feel_temperature']:.1f}°C)</div>
    </div>
    """, unsafe_allow_html=True)
else:
    col1.markdown('<div class="metric-card"><div class="metric-label">Chưa có dữ liệu thời tiết</div></div>', unsafe_allow_html=True)

# 2. Chất lượng không khí (AQI)
if not df_weather.empty:
    latest_w = df_weather.iloc[0]
    aqi_class = "warning-text" if latest_w['aqi_status'] in ["Kém", "Rất kém"] else "success-text"
    col2.markdown(f"""
    <div class="metric-card">
        <div class="metric-value {aqi_class}">{latest_w['aqi_status']}</div>
        <div class="metric-label">Chất lượng không khí (Bụi mịn: {latest_w['pm25']:.1f} µg/m³)</div>
    </div>
    """, unsafe_allow_html=True)
else:
    col2.markdown('<div class="metric-card"><div class="metric-label">Chưa có dữ liệu không khí</div></div>', unsafe_allow_html=True)

# 3. Độ mặn tại cống An Thổ
df_an_tho = df_salinity[df_salinity['gate_name'].str.contains("An Thổ|AN THỔ", case=False, na=False)]
if not df_an_tho.empty:
    latest_an_tho = df_an_tho.iloc[0]
    val = latest_an_tho['value']
    class_name = "warning-text" if val > 1.0 else "success-text"
    col3.markdown(f"""
    <div class="metric-card">
        <div class="metric-value {class_name}">{val:.2f} ‰</div>
        <div class="metric-label">Độ mặn cống An Thổ (Đo lúc: {latest_an_tho['timestamp'].split()[1]})</div>
    </div>
    """, unsafe_allow_html=True)
else:
    col3.markdown('<div class="metric-card"><div class="metric-label">Chưa có dữ liệu độ mặn An Thổ</div></div>', unsafe_allow_html=True)

# 4. Độ mặn tại cống Cầu Xe
df_cau_xe = df_salinity[df_salinity['gate_name'].str.contains("Cầu Xe|CẦU XE", case=False, na=False)]
if not df_cau_xe.empty:
    latest_cau_xe = df_cau_xe.iloc[0]
    val = latest_cau_xe['value']
    class_name = "warning-text" if val > 1.0 else "success-text"
    col4.markdown(f"""
    <div class="metric-card">
        <div class="metric-value {class_name}">{val:.2f} ‰</div>
        <div class="metric-label">Độ mặn cống Cầu Xe (Đo lúc: {latest_cau_xe['timestamp'].split()[1]})</div>
    </div>
    """, unsafe_allow_html=True)
else:
    col4.markdown('<div class="metric-card"><div class="metric-label">Chưa có dữ liệu độ mặn Cầu Xe</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ----------------- PHẦN 2: BIỂU ĐỒ TRỰC QUAN HÓA -----------------
tab1, tab2, tab3 = st.tabs(["📉 Mực nước tại các cống", "📈 Biến động độ mặn", "🌧️ Lượng mưa tại các trạm"])

with tab1:
    st.markdown("### So sánh mực nước thượng lưu và hạ lưu tại các cống vận hành")
    if not df_struct.empty:
        df_levels = df_struct[df_struct['parameter_name'].isin(['TL', 'HL', 'HTL', 'HHL'])]
        df_levels_latest = df_levels.sort_values('timestamp').groupby(['structure_name', 'parameter_name']).last().reset_index()
        
        df_levels_latest['parameter_name'] = df_levels_latest['parameter_name'].replace({
            'TL': 'Thượng lưu', 'HTL': 'Thượng lưu',
            'HL': 'Hạ lưu', 'HHL': 'Hạ lưu'
        })
        
        fig = px.bar(
            df_levels_latest,
            x="structure_name",
            y="value",
            color="parameter_name",
            barmode="group",
            labels={"structure_name": "Tên cống / công trình", "value": "Mực nước (cm)", "parameter_name": "Vị trí đo"},
            color_discrete_map={"Thượng lưu": "#3b82f6", "Hạ lưu": "#f97316"},
            height=450,
            template=plotly_template
        )
        fig.update_layout(
            font_family="Times New Roman",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=plotly_text,
            xaxis_tickangle=-45,
            xaxis=dict(gridcolor=grid_color, linecolor=axis_color),
            yaxis=dict(gridcolor=grid_color, linecolor=axis_color)
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.warning("Không có dữ liệu mực nước để hiển thị.")

with tab2:
    st.markdown("### Lịch sử thay đổi độ mặn tại khu vực cửa sông (An Thổ và Cầu Xe)")
    if not df_salinity.empty:
        df_sal_sorted = df_salinity.sort_values('timestamp')
        
        fig_sal = px.line(
            df_sal_sorted,
            x="timestamp",
            y="value",
            color="gate_name",
            labels={"timestamp": "Thời gian", "value": "Độ mặn (‰ hoặc ppt)", "gate_name": "Trạm đo"},
            markers=True,
            color_discrete_sequence=["#ef4444", "#22c55e"],
            height=450,
            template=plotly_template
        )
        fig_sal.update_layout(
            font_family="Times New Roman",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=plotly_text,
            hovermode="x unified",
            xaxis=dict(gridcolor=grid_color, linecolor=axis_color),
            yaxis=dict(gridcolor=grid_color, linecolor=axis_color)
        )
        st.plotly_chart(fig_sal, width="stretch")
    else:
        st.warning("Không có dữ liệu lịch sử độ mặn.")

with tab3:
    st.markdown("### Lượng mưa tích lũy đo được tại các trạm đo ở Hải Dương")
    if not df_rain.empty:
        df_rain_latest = df_rain.sort_values('timestamp').groupby('station_name').last().reset_index()
        df_rain_latest = df_rain_latest.sort_values('rain_amount', ascending=False)
        
        fig_rain = px.bar(
            df_rain_latest,
            x="station_name",
            y="rain_amount",
            labels={"station_name": "Trạm đo lượng mưa", "rain_amount": "Lượng mưa tích lũy (mm)"},
            color="rain_amount",
            color_continuous_scale="Blues" if st.session_state["theme"] == "Ban ngày ☀️" else "Cividis",
            height=450,
            template=plotly_template
        )
        fig_rain.update_layout(
            font_family="Times New Roman",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=plotly_text,
            xaxis_tickangle=-45,
            xaxis=dict(gridcolor=grid_color, linecolor=axis_color),
            yaxis=dict(gridcolor=grid_color, linecolor=axis_color)
        )
        st.plotly_chart(fig_rain, width="stretch")
    else:
        st.warning("Không có dữ liệu lượng mưa để hiển thị.")

# ----------------- PHẦN 3: BẢNG NHẬT KÝ ĐIỀU HÀNH & CHI TIẾT -----------------
st.markdown("---")
st.subheader("📋 Nhật ký và bảng số liệu chi tiết")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### Trạng thái hoạt động và vận hành của công trình")
    if not df_struct.empty:
        df_ops = df_struct[df_struct['parameter_name'].isin(['DoMo', 'LuuLuong'])]
        if not df_ops.empty:
            df_ops_latest = df_ops.sort_values('timestamp').groupby(['structure_name', 'parameter_name']).last().reset_index()
            df_ops_pivot = df_ops_latest.pivot(index='structure_name', columns='parameter_name', values='value_str').reset_index()
            df_ops_pivot.columns = ['Tên công trình', 'Độ mở cống (cm)', 'Lưu lượng xả (m3/s)']
            df_ops_pivot = df_ops_pivot.fillna("-")
            
            st.dataframe(df_ops_pivot, width="stretch", hide_index=True)
        else:
            st.info("Chưa ghi nhận hoạt động đóng mở cống trong ngày.")
    else:
        st.info("Không tìm thấy dữ liệu vận hành.")

with col_right:
    st.markdown("#### Dự báo thời tiết và chất lượng không khí")
    if not df_weather.empty:
        st.dataframe(
            df_weather[['timestamp', 'temperature', 'humidity', 'wind_speed', 'aqi_status', 'pm25']].head(10),
            column_config={
                "timestamp": "Thời gian",
                "temperature": st.column_config.NumberColumn("Nhiệt độ (°C)", format="%.1f"),
                "humidity": st.column_config.NumberColumn("Độ ẩm (%)", format="%.0f"),
                "wind_speed": st.column_config.NumberColumn("Tốc độ gió (m/s)", format="%.1f"),
                "aqi_status": "Chất lượng không khí",
                "pm25": st.column_config.NumberColumn("Bụi mịn (µg/m³)", format="%.1f")
            },
            width="stretch",
            hide_index=True
        )
    else:
        st.info("Chưa có thông tin thời tiết lịch sử.")
