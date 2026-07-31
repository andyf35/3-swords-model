import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="個股專用戰情室", page_icon="📈", layout="centered")
st.title("📈 均線與籌碼監控 (個股專用版)")

user_input = st.text_input("請輸入台股個股代碼 (例如：2308)", "2308")

if not user_input.endswith(".TW") and not user_input.endswith(".TWO"):
    stock_symbol = f"{user_input}.TW"
else:
    stock_symbol = user_input

st.subheader(f"當前監控標的: {stock_symbol}")

@st.cache_data
def get_data(symbol):
    # 【個股修正 1】：改抓 1 年的「日線(1d)」資料，而非小時線
    data = yf.download(symbol, period="1y", interval="1d")
    return data

df = get_data(stock_symbol)

if df.empty:
    st.error("⚠️ 找不到該檔股票的資料，請確認代碼是否正確。")
else:
    close_series = df['Close']
    if isinstance(close_series, pd.DataFrame):
        close_series = close_series.iloc[:, 0]
        
    vol_series = df['Volume']
    if isinstance(vol_series, pd.DataFrame):
        vol_series = vol_series.iloc[:, 0]
        
    open_series = df['Open']
    if isinstance(open_series, pd.DataFrame):
        open_series = open_series.iloc[:, 0]
        
    df['Close_1D'] = close_series
    df['Volume_1D'] = vol_series
    df['Open_1D'] = open_series
    
    # 計算日線層級的 20、60、240 均線 (真實的月線、季線、年線)
    df['月線_20MA'] = df['Close_1D'].rolling(window=20).mean()
    df['季線_60MA'] = df['Close_1D'].rolling(window=60).mean()
    df['年線_240MA'] = df['Close_1D'].rolling(window=240).mean()
    df['Volume_5MA'] = df['Volume_1D'].rolling(window=5).mean()
    
    # 取得近三日的收盤價，用於「三日站穩法則」
    last_3_closes = df['Close_1D'].iloc[-3:].tolist()
    current_price = float(last_3_closes[-1])
    yesterday_price = float(last_3_closes[-2])
    
    # 取得最新一筆指標
    ma20 = float(df['月線_20MA'].iloc[-1])
    ma60 = float(df['季線_60MA'].iloc[-1])
    ma240 = float(df['年線_240MA'].iloc[-1])
    current_vol = float(df['Volume_1D'].iloc[-1])
    vol_5ma = float(df['Volume_5MA'].iloc[-1])
    current_open = float(df['Open_1D'].iloc[-1])

    bias_60 = ((current_price - ma60) / ma60) * 100

    # 【個股修正 3】：跳空缺口偵測 (今日開盤直接大於昨日收盤 2% 以上)
    is_gap_up = (current_open - yesterday_price) / yesterday_price > 0.02

    # 【個股修正 2】：三日不破法則與個股戰術訊號
    # 判斷是否連續三天都大於季線
    stable_above_60 = all(price > ma60 for price in last_3_closes)
    
    if stable_above_60 and ma20 > ma60:
        trend = "🟢 多頭格局 (底盤穩固)"
        if is_gap_up:
            action_signal = "🚀【強勢買入】出現向上跳空缺口且站穩季線，主力發動攻擊！"
            signal_color = "success"
        elif current_vol > vol_5ma:
            action_signal = "🔥【波段買入/抱牢】連續三日站穩季線且量增，基本盤極穩，可安心建倉。"
            signal_color = "success"
        else:
            action_signal = "✅【持股續抱】股價穩定在季線之上，雖然量縮但結構健康，抱緊即可。"
            signal_color = "success"
            
    elif current_price < ma60 and ma20 < ma60:
        trend = "🔴 空頭格局 (跌破防線)"
        action_signal = "🛡️【觀望 / 賣出】已跌破季線法人防守區，個股基本面或籌碼轉弱，請保留現金。"
        signal_color = "error"
    else:
        trend = "⚪ 震盪洗盤 (打底階段)"
        if current_price > ma60 and not stable_above_60:
            action_signal = "👀【假突破警戒】今天剛站上季線，但尚未經過「三日測試」，勿急躁追高，觀察明後天是否軟腳。"
            signal_color = "warning"
        else:
            action_signal = "⏳【盤整中】個股在均線間反覆測試支撐，請耐心等候明確的突破訊號。"
            signal_color = "warning"

    st.markdown(f"### 當前狀態: **{trend}**")
    
    if signal_color == "success":
        st.success(action_signal)
    elif signal_color == "error":
        st.error(action_signal)
    else:
        st.warning(action_signal)

    if bias_60 >= 15:
        st.error(f"🚨 **追高警告**：正乖離達 {bias_60:.1f}%，隨時面臨獲利了結賣壓！")
    elif bias_60 <= -15:
        st.success(f"💎 **價值投資浮現**：負乖離達 {bias_60:.1f}%，股價遭錯殺，可規劃分批買進！")

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="月線 (原張飛)", value=f"{ma20:.2f}")
    with col2:
        st.metric(label="季線 (原關羽)", value=f"{ma60:.2f}")
    with col3:
        st.metric(label="年線 (原劉備)", value=f"{ma240:.2f}")

    st.metric(label="最新日收盤價", value=f"{current_price:.2f}", delta=f"距季線: {(current_price - ma60):.2f}")
    st.markdown(f"> 📊 **籌碼與技術面底層數據**  \n> • 連續站穩季線天數: **{'✅ 達標 (>=3天)' if stable_above_60 else '❌ 未達標'}**  \n> • 跳空缺口偵測: **{'🔥 出現向上缺口' if is_gap_up else '無明顯缺口'}**")
