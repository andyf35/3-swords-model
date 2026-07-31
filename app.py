
import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 網頁基本設定 
st.set_page_config(page_title="三刀流戰情室", page_icon="⚔️", layout="centered")
st.title("⚔️ 三國名將均線監控")

# 2. 新增：動態股票代碼輸入框
# 預設為 2308，使用者可以直接刪除並輸入其他代碼
user_input = st.text_input("請輸入台股代碼 (例如：2308 或 00713)", "2308")

# 系統自動防呆：幫使用者加上 yfinance 台股專用的 .TW 尾碼
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

# 4. 判斷是否有抓到資料與運算大腦
if df.empty:
    st.error("⚠️ 找不到該檔股票的資料，請確認代碼是否正確（上櫃股票請手動輸入 代碼.TWO，例如 3529.TWO）。")
else:
    # 計算 三刀流 MA
    df['張飛_20MA'] = df['Close'].rolling(window=20).mean()
    df['關羽_60MA'] = df['Close'].rolling(window=60).mean()
    df['劉備_240MA'] = df['Close'].rolling(window=240).mean()
    
    # 取得最新一筆收盤數據
    latest = df.iloc[-1]
    current_price = latest['Close']
    ma20 = latest['張飛_20MA']
    ma60 = latest['關羽_60MA']
    ma240 = latest['劉備_240MA']

    # 5. 判斷多空趨勢邏輯
    if current_price > ma60 and ma20 > ma60:
        trend = "🟢 偏多 (多頭排列或轉強)"
    elif current_price < ma60 and ma20 < ma60:
        trend = "🔴 偏空 (空頭排列或轉弱)"
    else:
        trend = "⚪ 盤整 (夾在均線之間)"

    # 6. 手機版 UI 呈現 
    st.markdown(f"### 當前狀態: **{trend}**")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="張飛 20MA", value=f"{ma20:.2f}")
    with col2:
        st.metric(label="關羽 60MA", value=f"{ma60:.2f}")
    with col3:
        st.metric(label="劉備 240MA", value=f"{ma240:.2f}")

    st.metric(label="最新收盤價", value=f"{current_price:.2f}", delta=f"距關羽: {(current_price - ma60):.2f}")
