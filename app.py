import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 網頁基本設定 
st.set_page_config(page_title="三刀流戰情室", page_icon="⚔️", layout="centered")
st.title("⚔️ 三國名將均線監控")

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
    # 4. 處理 yfinance 資料格式
    close_series = df['Close']
    if isinstance(close_series, pd.DataFrame):
        close_series = close_series.iloc[:, 0]
        
    df['Close_1D'] = close_series
    df['張飛_20MA'] = df['Close_1D'].rolling(window=20).mean()
    df['關羽_60MA'] = df['Close_1D'].rolling(window=60).mean()
    df['劉備_240MA'] = df['Close_1D'].rolling(window=240).mean()
    
    current_price = float(df['Close_1D'].iloc[-1])
    ma20 = float(df['張飛_20MA'].iloc[-1])
    ma60 = float(df['關羽_60MA'].iloc[-1])
    ma240 = float(df['劉備_240MA'].iloc[-1])

    # 5. 【全新升級】：買賣戰術訊號判定邏輯
    if current_price > ma60 and ma20 > ma60:
        trend = "🟢 偏多 (多頭排列或轉強)"
        action_signal = "🔥【買入 / 抱牢】主力已站上季線，順風局可伺機建立部位或抱牢。"
        signal_color = "success" # 綠色提示框
    elif current_price < ma60 and ma20 < ma60:
        trend = "🔴 偏空 (空頭排列或轉弱)"
        action_signal = "🛡️【賣出 / 空手】跌破法人防守線，建議獲利了結或持幣觀望，切勿接刀。"
        signal_color = "error" # 紅色提示框
    else:
        trend = "⚪ 盤整 (夾在均線之間)"
        action_signal = "⏳【觀望 / 扣緊現金】多空交戰中，請按兵不動等待明確突破方向。"
        signal_color = "warning" # 黃色提示框

    # 6. 手機版 UI 呈現 
    st.markdown(f"### 當前狀態: **{trend}**")
    
    # 動態顯示買賣戰術指示燈
    if signal_color == "success":
        st.success(action_signal)
    elif signal_color == "error":
        st.error(action_signal)
    else:
        st.warning(action_signal)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="張飛 20MA", value=f"{ma20:.2f}")
    with col2:
        st.metric(label="關羽 60MA", value=f"{ma60:.2f}")
    with col3:
        st.metric(label="劉備 240MA", value=f"{ma240:.2f}")

    st.metric(label="最新收盤價", value=f"{current_price:.2f}", delta=f"距關羽: {(current_price - ma60):.2f}")
