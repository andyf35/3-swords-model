import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 網頁基本設定 
st.set_page_config(page_title="三刀流全能戰情室", page_icon="⚔️", layout="centered")
st.title("⚔️ 全能操盤戰情室 (個股與ETF雙模)")

# 2. 建立雙分頁架構
tab_single, tab_radar = st.tabs(["🎯 單兵深度診蒐", "🔥 戰略選股雷達"])

# ================= TAB 1: 單兵深度診蒐 (完全還原原本版面) =================
with tab_single:
    col_input1, col_input2 = st.columns([2, 1])
    with col_input1:
        user_input = st.text_input("請輸入台股代碼 (例如：2308 或 00713)", "2308", key="single_input")
    with col_input2:
        asset_type = st.selectbox("資產屬性", ["一般個股", "高股息/防禦ETF"], key="single_asset_type")

    if not user_input.endswith(".TW") and not user_input.endswith(".TWO"):
        stock_symbol = f"{user_input}.TW"
    else:
        stock_symbol = user_input

    st.subheader(f"當前監控標的: {stock_symbol} ({asset_type})")

    @st.cache_data(ttl=1800)
    def get_single_data(symbol):
        data = yf.download(symbol, period="1y", interval="1d")
        return data

    df = get_single_data(stock_symbol)

    if df.empty:
        st.error("⚠️ 找不到該檔股票的資料，請確認代碼是否正確。")
    else:
        # 資料處理
        close_series = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
        vol_series = df['Volume'].iloc[:, 0] if isinstance(df['Volume'], pd.DataFrame) else df['Volume']
        open_series = df['Open'].iloc[:, 0] if isinstance(df['Open'], pd.DataFrame) else df['Open']
            
        df['Close_1D'] = close_series
        df['Volume_1D'] = vol_series
        df['Open_1D'] = open_series
        
        # 計算均線
        df['月線_20MA'] = df['Close_1D'].rolling(window=20).mean()
        df['季線_60MA'] = df['Close_1D'].rolling(window=60).mean()
        df['年線_240MA'] = df['Close_1D'].rolling(window=240).mean()
        df['Volume_5MA'] = df['Volume_1D'].rolling(window=5).mean()
        
        # MACD 計算
        exp12 = df['Close_1D'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close_1D'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['Signal']

        # 數值擷取
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

        if asset_type == "一般個股":
            sweet_threshold = -15.0
            stop_loss_pct = 0.97
        else:
            sweet_threshold = -5.0
            stop_loss_pct = 0.98

        is_downtrend = (current_price < ma60 and ma20 < ma60)
        is_macd_bearish = (macd_hist_val <= 0)

        # 戰術訊號判定
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

        # 呈現當前狀態與主要戰術提示
        st.markdown(f"### 當前狀態: **{trend}**")
        
        if signal_color == "success":
            st.success(action_signal)
            suggested_stop = ma60 * stop_loss_pct
            st.info(f"🛡️ **紀律防護網**：建議防守價位設在 **{suggested_stop:.2f}** 附近。")
        elif signal_color == "error":
            st.error(action_signal)
        else:
            st.warning(action_signal)

        # 甜甜價與風險防護鎖
        calculated_sweet_price = ma60 * (1 + sweet_threshold / 100.0)
        
        if bias_60 <= sweet_threshold:
            if is_downtrend or is_macd_bearish:
                st.error(f"🚨 **【甜甜價陷阱警告】** 雖然負乖離達 {bias_60:.1f}%（低於甜甜價門檻 {sweet_threshold}%），但目前畫面顯示為 **「空頭格局」** 且 **「MACD 空方動能主導」**！  \n\n> 🛑 **專家強烈不建議購買**：此為弱勢跌深，極易遇到價值陷阱或繼續下殺，請緊鎖現金切勿接刀！")
            else:
                st.success(f"💎 **【黃金甜甜價觸發】** 負乖離達 {bias_60:.1f}% 且多頭結構與動能健康！估算甜甜價位約在 **{calculated_sweet_price:.2f}** 以下，可考慮分批佈局。")
        elif bias_60 >= (15 if asset_type == "一般個股" else 6):
            st.error(f"🚨 **【短線過熱警告】** 正乖離達 {bias_60:.1f}%，短線過熱，慎防回檔！")
        else:
            st.info(f"🎯 **甜甜價雷達監控中**：當前乖離 {bias_60:.1f}%（觸發門檻：{sweet_threshold}% / 參考價：約 {calculated_sweet_price:.2f}）")

        st.markdown("---")

        # 完全還原三欄均線數據
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="月線 (20MA)", value=f"{ma20:.2f}")
        with col2:
            st.metric(label="季線 (60MA)", value=f"{ma60:.2f}")
        with col3:
            st.metric(label="年線 (240MA)", value=f"{ma240:.2f}")

        st.metric(label="最新日收盤價", value=f"{current_price:.2f}", delta=f"距季線: {(current_price - ma60):.2f}")
        
        # 完全還原多維度底層數據
        macd_status = "🟢 多方動能增強" if not is_macd_bearish else "🔴 空方動能主導"
        st.markdown(f"""
        > 📊 **多維度底層數據**  
        > • 三日站穩季線: **{'✅ 達標' if stable_above_60 else '❌ 未達標'}**  
        > • MACD 動能柱: **{macd_status}**  
        > • 資產專屬甜甜價參考線: **{calculated_sweet_price:.2f}**
        """)

# ================= TAB 2: 戰略選股雷達 (批次一鍵掃描) =================
with tab_radar:
    st.markdown("### 🔍 專家嚴選：十大高階智造與 AI 股雷達")
    st.write("點擊下方按鈕，系統將自動掃描 10 檔口袋名單，找出今日突破與甜甜價標的。")
    
    watch_list = {
        "2308.TW": "台達電",
        "2330.TW": "台積電",
        "1590.TW": "亞德客-KY",
        "2317.TW": "鴻海",
        "2360.TW": "致茂",
        "2382.TW": "廣達",
        "2059.TW": "川湖",
        "3017.TW": "奇鋐",
        "2395.TW": "研華",
        "1519.TW": "華城"
    }
    
    if st.button("🚀 啟動 10 檔精選股雷達掃描"):
        with st.spinner('雷達掃描中，請稍候...'):
            results = []
            for symbol, name in watch_list.items():
                try:
                    df_r = yf.download(symbol, period="1y", interval="1d", progress=False)
                    if not df_r.empty:
                        c_series = df_r['Close'].iloc[:, 0] if isinstance(df_r['Close'], pd.DataFrame) else df_r['Close']
                        v_series = df_r['Volume'].iloc[:, 0] if isinstance(df_r['Volume'], pd.DataFrame) else df_r['Volume']
                        
                        c_price = float(c_series.iloc[-1])
                        ma20_r = float(c_series.rolling(20).mean().iloc[-1])
                        ma60_r = float(c_series.rolling(60).mean().iloc[-1])
                        vol_5ma_r = float(v_series.rolling(5).mean().iloc[-1])
                        cur_vol_r = float(v_series.iloc[-1])
                        
                        exp12_r = c_series.ewm(span=12, adjust=False).mean()
                        exp26_r = c_series.ewm(span=26, adjust=False).mean()
                        macd_h = (exp12_r - exp26_r - (exp12_r - exp26_r).ewm(span=9, adjust=False).mean()).iloc[-1]
                        
                        last_3 = c_series.iloc[-3:].tolist()
                        stable_60 = all(p > ma60_r for p in last_3)
                        bias_60_r = ((c_price - ma60_r) / ma60_r) * 100
                        
                        is_down = (c_price < ma60_r and ma20_r < ma60_r)
                        is_macd_bear = (macd_h <= 0)
                        
                        if stable_60 and ma20_r > ma60_r:
                            tr = "🟢 多頭"
                            sig = "🔥 強勢波段" if cur_vol_r > vol_5ma_r and not is_macd_bear else "✅ 多頭續抱"
                        elif is_down:
                            tr = "🔴 空頭"
                            sig = "🛡️ 跌破觀望"
                        else:
                            tr = "⚪ 盤整"
                            sig = "⏳ 震盪洗盤"
                            
                        if bias_60_r <= -15.0:
                            sig = "🛑 陷阱觀望" if (is_down or is_macd_bear) else "💎 甜甜價"
                            
                        results.append({
                            "代碼": symbol.replace(".TW", ""),
                            "名稱": name,
                            "最新價": round(c_price, 2),
                            "季線": round(ma60_r, 2),
                            "乖離率(%)": round(bias_60_r, 2),
                            "趨勢": tr,
                            "戰術建議": sig
                        })
                except Exception:
                    pass
            
            if results:
                st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
                st.success("✅ 掃描完成！請優先關注戰術建議為「🚀、🔥、💎」的標的。")
