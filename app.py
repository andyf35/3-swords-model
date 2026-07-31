import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 網頁基本設定 
st.set_page_config(page_title="三刀流全能戰情室 (PRO防禦版)", page_icon="⚔️", layout="centered")
st.title("⚔️ 全能操盤戰情室 (個股與ETF雙模)")

# 2. 標的與資產屬性設定
col_input1, col_input2 = st.columns([2, 1])
with col_input1:
    user_input = st.text_input("請輸入台股代碼 (例如：2308 或 00713)", "2308")
with col_input2:
    asset_type = st.selectbox("資產屬性", ["一般個股", "高股息/防禦ETF"])

if not user_input.endswith(".TW") and not user_input.endswith(".TWO"):
    stock_symbol = f"{user_input}.TW"
else:
    stock_symbol = user_input

st.subheader(f"當前監控標的: {stock_symbol} ({asset_type})")

# 3. 抓取歷史數據 
@st.cache_data
def get_data(symbol):
    data = yf.download(symbol, period="1y", interval="1d")
    return data

df = get_data(stock_symbol)

if df.empty:
    st.error("⚠️ 找不到該檔股票的資料，請確認代碼是否正確。")
else:
    # 數據格式化處理
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
    
    # 計算均線與成交量均線
    df['月線_20MA'] = df['Close_1D'].rolling(window=20).mean()
    df['季線_60MA'] = df['Close_1D'].rolling(window=60).mean()
    df['年線_240MA'] = df['Close_1D'].rolling(window=240).mean()
    df['Volume_5MA'] = df['Volume_1D'].rolling(window=5).mean()
    
    # MACD 動態計算 (EMA12 - EMA26)
    exp12 = df['Close_1D'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close_1D'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal']

    # 取得關鍵數值
    last_3_closes = df['Close_1D'].iloc[-3:].tolist()
    current_price = float(last_3_closes[-1])
    yesterday_price = float(last_3_closes[-2])
    
    ma20 = float(df['月線_20MA'].iloc[-1])
    ma60 = float(df['季線_60MA'].iloc[-1])
    ma240 = float(df['年線_240MA'].iloc[-1])
    current_vol = float(df['Volume_1D'].iloc[-1])
    vol_5ma = float(df['Volume_5MA'].iloc[-1])
    current_open = float(df['Open_1D'].iloc[-1])
    macd_hist_val = float(df['MACD_Hist'].iloc[-1])

    bias_60 = ((current_price - ma60) / ma60) * 100
    is_gap_up = (current_open - yesterday_price) / yesterday_price > 0.02
    stable_above_60 = all(price > ma60 for price in last_3_closes)

    # 4. 根據資產屬性設定甜甜價門檻
    if asset_type == "一般個股":
        sweet_threshold = -15.0
        stop_loss_pct = 0.97
    else:
        sweet_threshold = -5.0
        stop_loss_pct = 0.98

    # 5. 戰術訊號判定
    is_downtrend = (current_price < ma60 and ma20 < ma60)
    is_macd_bearish = (macd_hist_val <= 0)

    if stable_above_60 and ma20 > ma60:
        trend = "🟢 多頭格局 (底盤穩固)"
        if is_gap_up:
            action_signal = "🚀【強勢買入】出現向上跳空缺口且站穩季線，主力發動攻擊！"
            signal_color = "success"
        elif current_vol > vol_5ma and not is_macd_bearish:
            action_signal = "🔥【波段買入/抱牢】連續三日站穩季線、量增且 MACD 動能向上，可安心建倉。"
            signal_color = "success"
        else:
            action_signal = "✅【持股續抱】結構健康，多頭排列持續中。"
            signal_color = "success"
            
    elif is_downtrend:
        trend = "🔴 空頭格局 (跌破防線)"
        action_signal = "🛡️【觀望 / 賣出】已跌破季線法人防守區，請保留現金，切勿躁進。"
        signal_color = "error"
    else:
        trend = "⚪ 震盪洗盤 (打底階段)"
        action_signal = "⏳【盤整中】多空拉鋸，耐心等候明確突破。"
        signal_color = "warning"

    # 6. 介面呈現
    st.markdown(f"### 當前狀態: **{trend}**")
    
    if signal_color == "success":
        st.success(action_signal)
        suggested_stop = ma60 * stop_loss_pct
        st.info(f"🛡️ **紀律防護網**：建議防守價位設在 **{suggested_stop:.2f}** 附近。")
    elif signal_color == "error":
        st.error(action_signal)
    else:
        st.warning(action_signal)

    # 7. 【全新防禦鎖】：智慧甜甜價與空頭否決預警
    calculated_sweet_price = ma60 * (1 + sweet_threshold / 100.0)
    
    if bias_60 <= sweet_threshold:
        # 核心防禦邏輯：雖然觸發甜甜價，但如果處於空頭或MACD空方，強制發出強烈警告！
        if is_downtrend or is_macd_bearish:
            st.error(f"🚨 **【甜甜價陷阱警告】** 雖然負乖離達 {bias_60:.1f}%（低於甜甜價門檻 {sweet_threshold}%），但目前畫面顯示為 **「空頭格局」** 且 **「MACD 空方動能主導」**！  \n\n> 🛑 **專家強烈不建議購買**：此為弱勢跌深，極易遇到價值陷阱或繼續下殺，請緊鎖現金切勿接刀！")
        else:
            st.success(f"💎 **【黃金甜甜價觸發】** 負乖離達 {bias_60:.1f}% 且多頭結構與動能健康！估算甜甜價位約在 **{calculated_sweet_price:.2f}** 以下，可考慮分批佈局。")
    elif bias_60 >= (15 if asset_type == "一般個股" else 6):
        st.error(f"🚨 **【短線過熱警告】** 正乖離達 {bias_60:.1f}%，短線過熱，慎防回檔！")
    else:
        st.info(f"🎯 **甜甜價雷達監控中**：當前乖離 {bias_60:.1f}%（觸發門檻：{sweet_threshold}% / 參考價：約 {calculated_sweet_price:.2f}）")

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="月線 (20MA)", value=f"{ma20:.2f}")
    with col2:
        st.metric(label="季線 (60MA)", value=f"{ma60:.2f}")
    with col3:
        st.metric(label="年線 (240MA)", value=f"{ma240:.2f}")

    st.metric(label="最新日收盤價", value=f"{current_price:.2f}", delta=f"距季線: {(current_price - ma60):.2f}")
    
    macd_status = "🟢 多方動能增強" if not is_macd_bearish else "🔴 空方動能主導"
    st.markdown(f"""
    > 📊 **多維度底層數據**  
    > • 三日站穩季線: **{'✅ 達標' if stable_above_60 else '❌ 未達標'}**  
    > • MACD 動能柱: **{macd_status}**  
    > • 資產專屬甜甜價參考線: **{calculated_sweet_price:.2f}**
    """)
