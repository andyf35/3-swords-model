import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 網頁基本設定 
st.set_page_config(page_title="三刀流戰情室 (PRO版)", page_icon="⚔️", layout="centered")
st.title("⚔️ 三國名將均線監控 (PRO版)")

# 2. 動態股票代碼輸入框
user_input = st.text_input("請輸入台股代碼 (例如：2308 或 00713)", "2308")

if not user_input.endswith(".TW") and not user_input.endswith(".TWO"):
    stock_symbol = f"{user_input}.TW"
else:
    stock_symbol = user_input

st.subheader(f"當前監控標的: {stock_symbol}")

# 3. 透過 API 獲取歷史數據 
@st.cache_data
def get_data(symbol):
    data = yf.download(symbol, period="6mo", interval="1h")
    return data

df = get_data(stock_symbol)

if df.empty:
    st.error("⚠️ 找不到該檔股票的資料，請確認代碼是否正確。")
else:
    # 4. 處理 yfinance 資料格式 (包含收盤價與成交量)
    close_series = df['Close']
    if isinstance(close_series, pd.DataFrame):
        close_series = close_series.iloc[:, 0]
        
    vol_series = df['Volume']
    if isinstance(vol_series, pd.DataFrame):
        vol_series = vol_series.iloc[:, 0]
        
    df['Close_1D'] = close_series
    df['Volume_1D'] = vol_series
    
    # 計算均線
    df['張飛_20MA'] = df['Close_1D'].rolling(window=20).mean()
    df['關羽_60MA'] = df['Close_1D'].rolling(window=60).mean()
    df['劉備_240MA'] = df['Close_1D'].rolling(window=240).mean()
    
    # 增加：計算近期平均成交量 (5期均量) 作為動能濾網
    df['Volume_5MA'] = df['Volume_1D'].rolling(window=5).mean()
    
    # 取得最新一筆數據
    current_price = float(df['Close_1D'].iloc[-1])
    ma20 = float(df['張飛_20MA'].iloc[-1])
    ma60 = float(df['關羽_60MA'].iloc[-1])
    ma240 = float(df['劉備_240MA'].iloc[-1])
    current_vol = float(df['Volume_1D'].iloc[-1])
    vol_5ma = float(df['Volume_5MA'].iloc[-1])

    # 增加：計算乖離率 (Bias)
    bias_60 = ((current_price - ma60) / ma60) * 100

    # 5. 【專家濾網升級】：趨勢與買賣戰術訊號判定
    if current_price > ma60 and ma20 > ma60:
        trend = "🟢 偏多 (多頭排列或轉強)"
        # 濾網 1：成交量防護網
        if current_vol > vol_5ma:
            action_signal = "🔥【買入 / 抱牢】帶量突破！主力真金白銀進場，順風局可伺機建倉。"
            signal_color = "success"
        else:
            action_signal = "⚠️【留意假突破】價格雖站上季線但「量能萎縮」，請先觀望，提防主力騙線誘多。"
            signal_color = "warning"
            
    elif current_price < ma60 and ma20 < ma60:
        trend = "🔴 偏空 (空頭排列或轉弱)"
        action_signal = "🛡️【賣出 / 空手】跌破法人防守線，建議獲利了結或持幣觀望，切勿接刀。"
        signal_color = "error"
    else:
        trend = "⚪ 盤整 (夾在均線之間)"
        action_signal = "⏳【觀望 / 扣緊現金】多空交戰中，請按兵不動等待明確突破方向。"
        signal_color = "warning"

    # 6. 手機版 UI 呈現與警示燈號
    st.markdown(f"### 當前狀態: **{trend}**")
    
    # 顯示主戰術訊號
    if signal_color == "success":
        st.success(action_signal)
        # 濾網 3：買進時自動顯示停損防護價 (容錯 2%)
        stop_loss_price = ma60 * 0.98
        st.info(f"🛡️ **紀律防護網**：若進場，請設定停損價為 **{stop_loss_price:.2f}** (關羽防線往下 2%)，跌破則無條件出場。")
    elif signal_color == "error":
        st.error(action_signal)
    else:
        st.warning(action_signal)

    # 濾網 2：乖離率過熱/超跌警示 (獨立亮燈)
    if bias_60 >= 15:
        st.error(f"🚨 **乖離率過熱警告**：正乖離達 {bias_60:.1f}%，短線極度過熱，股價容易回檔，切勿追高！")
    elif bias_60 <= -15:
        st.success(f"💎 **終極甜甜價訊號**：負乖離達 {bias_60:.1f}%，股價嚴重超跌，可準備用零股左側分批建倉！")

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="張飛 20MA", value=f"{ma20:.2f}")
    with col2:
        st.metric(label="關羽 60MA", value=f"{ma60:.2f}")
    with col3:
        st.metric(label="劉備 240MA", value=f"{ma240:.2f}")

    # 顯示詳細數據儀表板
    st.metric(label="最新收盤價", value=f"{current_price:.2f}", delta=f"距關羽: {(current_price - ma60):.2f}")
    st.markdown(f"> 📊 **底層數據監控**  \n> • 當前季線乖離率: **{bias_60:.2f}%**  \n> • 最新一期成交量: **{int(current_vol):,}** (均量標準: {int(vol_5ma):,})")
