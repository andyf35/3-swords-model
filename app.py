import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 網頁基本設定 
st.set_page_config(page_title="三刀流全能戰情室 (法人旗艦版)", page_icon="⚔️", layout="centered")
st.title("⚔️ 全能操盤戰情室 (法人旗艦旗艦版)")

# ================= 頂層模組：大盤系統性風險濾網 =================
@st.cache_data(ttl=300)
def get_market_trend():
    try:
        df_market = yf.download("^TWII", period="6m", interval="1d", progress=False)
        if not df_market.empty:
            c_market = df_market['Close'].iloc[:, 0] if isinstance(df_market['Close'], pd.DataFrame) else df_market['Close']
            ma60_market = c_market.rolling(window=60).mean().iloc[-1]
            current_market = c_market.iloc[-1]
            is_market_bull = current_market > ma60_market
            return is_market_bull, float(current_market), float(ma60_market)
    except Exception:
        pass
    return True, 0.0, 0.0 # 預設預防性偏多

is_market_healthy, m_price, m_ma60 = get_market_trend()

# 如果大盤破底，在網頁最上方給予系統級紅色警示
if not is_market_healthy:
    st.error(f"🚨 **【大盤系統性風險警告】** 台股大盤指數 ({m_price:.2f}) 已跌破季線 ({m_ma60:.2f})！目前市場處於逆風局，系統已自動提高防禦力，建議全面縮小部位或提高現金比例。")
else:
    st.success(f"✅ **【大盤趨勢正常】** 大盤指數 ({m_price:.2f}) 穩居季線 ({m_ma60:.2f}) 之上，多方環境維持健康。")

# 2. 建立雙分頁架構
tab_single, tab_radar = st.tabs(["🎯 單兵深度偵蒐與決策", "🔥 自訂選股雷達"])

# ================= TAB 1: 單兵深度偵蒐與決策 =================
with tab_single:
    col_input1, col_input2 = st.columns([2, 1])
    with col_input1:
        user_input = st.text_input("請輸入台股代碼 (例如：2308 或 2002)", "2308", key="single_input")
    with col_input2:
        asset_type = st.selectbox("資產屬性", ["一般個股", "高股息/防禦ETF"], key="single_asset_type")

    if not user_input.endswith(".TW") and not user_input.endswith(".TWO"):
        stock_symbol = f"{user_input}.TW"
    else:
        stock_symbol = user_input

    st.subheader(f"當前監控標的: {stock_symbol} ({asset_type})")

    @st.cache_data(ttl=300)
    def get_single_data(symbol):
        data = yf.download(symbol, period="1y", interval="1d", progress=False)
        return data

    df = get_single_data(stock_symbol)

    # 試著抓取基本面數據 (本益比 PE)
    ticker_obj = yf.Ticker(stock_symbol)
    try:
        pe_ratio = ticker_obj.info.get('trailingPE', 'N/A')
        div_yield = ticker_obj.info.get('dividendYield', 'N/A')
        if div_yield != 'N/A':
            div_yield = f"{div_yield * 100:.2f}%"
    except Exception:
        pe_ratio = 'N/A'
        div_yield = 'N/A'

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
        stable_above_60 = all(price > ma60 for price in last_3_closes)

        if asset_type == "一般個股":
            sweet_threshold = -15.0
            overheat_threshold = 15.0
        else:
            sweet_threshold = -5.0
            overheat_threshold = 6.0

        is_downtrend = (current_price < ma60 and ma20 < ma60)
        is_macd_bull = (macd_hist_val > 0)
        is_vol_surge = (current_vol > vol_5ma)

        # -------------------------------------------------------------
        # 📋 進場檢核清單 (Checklist)
        # -------------------------------------------------------------
        st.markdown("### 📋 進場檢核清單 (Checklist)")
        
        c1 = "✅ 達成" if stable_above_60 else "❌ 未達標"
        c2 = "✅ 達成" if ma20 > ma60 else "❌ 未達標"
        c3 = "✅ 達成" if is_macd_bull else "❌ 未達標"
        c5 = "✅ 達成" if bias_60 < overheat_threshold else "❌ 過熱"

        if is_vol_surge:
            if current_price < ma60 and not is_macd_bull:
                c4 = "❌ 危險"
                c4_text = "爆量下殺：空頭格局下出量，慎防主力倒貨"
            else:
                c4 = "✅ 達成"
                c4_text = "出量點火：當日成交量 > 5日均量 (大資金進場)"
        else:
            c4 = "❌ 未達標"
            c4_text = "量能平淡：當日成交量未達 5 日均量"

        st.markdown(f"""
        > - **{c1}** ｜ **站穩防線**：連續三日站穩季線
        > - **{c2}** ｜ **多頭排列**：月線 (20MA) 大於季線 (60MA)
        > - **{c3}** ｜ **動能向上**：MACD 動能柱為紅/正數
        > - **{c4}** ｜ **{c4_text}**
        > - **{c5}** ｜ **風險控管**：乖離率未過熱
        """)

        # -------------------------------------------------------------
        # ⚖️ 綜合決策、訊號分級與【資金控管建議】
        # -------------------------------------------------------------
        st.markdown("### ⚖️ 綜合決策與資金配置建議")
        
        grade_title = ""
        grade_desc = ""
        position_advice = ""
        color = "info"

        # 若大盤不健康，強制覆寫部分評級
        if not is_market_healthy and (stable_above_60 or current_price > ma60):
            grade_title = "⚠️【大盤逆風 / 降級保守觀望】"
            grade_desc = "雖然個股結構尚可，但大盤處於空頭破底，系統啟動防護，建議降低操作水位。"
            position_advice = "💡 **建議資金配置**：縮小部位，僅動用 10%~20% 資金短打或暫時觀望。"
            color = "warning"
        else:
            if bias_60 <= sweet_threshold:
                if is_downtrend or not is_macd_bull:
                    grade_title = "🛑【絕對不能買 / 避開陷阱】"
                    grade_desc = f"雖然負乖離達 {bias_60:.1f}%，但趨勢空頭且動能向下，嚴禁盲目接刀。"
                    position_advice = "💡 **建議資金配置**：0% (緊鎖現金，切勿進場)"
                    color = "error"
                else:
                    grade_title = "🌟【強烈買進 / 分批低接】"
                    grade_desc = f"股價跌至黃金甜蜜點（負乖離 {bias_60:.1f}%），且結構健康，具長線價值。"
                    position_advice = "💡 **建議資金配置**：動用 30% 分批低接資金 (例如 2.5 萬元分次佈局)"
                    color = "success"
            elif bias_60 >= overheat_threshold:
                grade_title = "⚠️【減碼 / 觀望勿追】"
                grade_desc = f"正乖離高達 {bias_60:.1f}%，短線漲幅已大，隨時有回檔風險。"
                position_advice = "💡 **建議資金配置**：持股者分批獲利了結，空手者嚴禁追高"
                color = "warning"
            elif current_price > ma60 and ma20 > ma60:
                if is_macd_bull and is_vol_surge:
                    grade_title = "🔥【強烈買進 / 順勢點火】"
                    grade_desc = "所有條件通過！出量且動能強勁，極具短線爆發力。"
                    position_advice = "💡 **建議資金配置**：動用標準主攻部位 (例如 3 萬元滿額打入)"
                    color = "success"
                elif is_macd_bull:
                    grade_title = "✅【偏多操作 / 持股續抱】"
                    grade_desc = "多頭結構穩定且動能向上，適合安穩建倉。"
                    position_advice = "💡 **建議資金配置**：動用 50% 常態資金穩健建倉"
                    color = "success"
                else:
                    grade_title = "⚠️【多頭回檔 / 留意支撐】"
                    grade_desc = f"長線多頭格局不變，但短期動能轉弱。留意下方季線防守價 {ma60:.2f}。"
                    position_advice = "💡 **建議資金配置**：暫緩加碼，等待止跌訊號"
                    color = "warning"
            elif is_downtrend:
                grade_title = "🛑【絕對不能買 / 空頭破底】"
                grade_desc = "全面跌破防守均線，法人主力正在撤退。"
                position_advice = "💡 **建議資金配置**：0% (保留現金至關重要)"
                color = "error"
            else:
                grade_title = "⏳【觀望 / 震盪打底】"
                grade_desc = "均線糾結或多空不明，缺乏明確進場理由。"
                position_advice = "💡 **建議資金配置**：0% 觀望，等待突破"
                color = "warning"

        if color == "success":
            st.success(f"**結論：{grade_title}**\n\n> 💡 {grade_desc}\n\n> {position_advice}")
        elif color == "error":
            st.error(f"**結論：{grade_title}**\n\n> 💡 {grade_desc}\n\n> {position_advice}")
        elif color == "warning":
            st.warning(f"**結論：{grade_title}**\n\n> 💡 {grade_desc}\n\n> {position_advice}")
        else:
            st.info(f"**結論：{grade_title}**\n\n> 💡 {grade_desc}\n\n> {position_advice}")

        st.markdown("---")

        # 三欄均線與基本面指標
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="月線 (20MA)", value=f"{ma20:.2f}")
        with col2:
            st.metric(label="季線 (60MA)", value=f"{ma60:.2f}")
        with col3:
            st.metric(label="本益比 (PE)", value=f"{pe_ratio}")
        with col4:
            st.metric(label="預估殖利率", value=f"{div_yield}")

        st.metric(label="最新日收盤價", value=f"{current_price:.2f}", delta=f"乖離率: {bias_60:.2f}%")
        
# ================= TAB 2: 自訂選股雷達 =================
with tab_radar:
    st.markdown("### 🔍 批次自訂選股雷達")
    st.write("輸入股票代碼（多檔用半形逗號 `,` 隔開），系統將自動化套用檢核清單、大盤濾網與資金配置建議。")
    
    default_tickers = "2308, 2330, 2059, 2395, 2002"
    custom_input = st.text_input("📝 填寫自選股名單：", value=default_tickers)
    
    short_term_filter = st.checkbox("⚡ 開啟【短線爆發力】快篩 (嚴格篩選：出量 + MACD翻紅)")

    if st.button("🚀 啟動自選雷達掃描"):
        if not custom_input.strip():
            st.warning("⚠️ 請先輸入至少一檔股票代碼！")
        else:
            with st.spinner('機台運轉與法人級數據掃描中，請稍候...'):
                results = []
                raw_symbols = [s.strip() for s in custom_input.split(',')]
                
                for raw_sym in raw_symbols:
                    if not raw_sym: 
                        continue
                        
                    if not raw_sym.endswith(".TW") and not raw_sym.endswith(".TWO"):
                        symbol = f"{raw_sym}.TW"
                    else:
                        symbol = raw_sym
                        
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
                            
                            bias_60_r = ((c_price - ma60_r) / ma60_r) * 100
                            is_down = (c_price < ma60_r and ma20_r < ma60_r)
                            is_macd_bull = (macd_h > 0)
                            is_vol_surge = (cur_vol_r > vol_5ma_r)
                            
                            # 訊號分級
                            if not is_market_healthy and (c_price > ma60_r):
                                eval_res = "⚠️ 大盤逆風(保守)"
                            elif bias_60_r <= -15.0:
                                eval_res = "🛑 絕對不能買" if (is_down or not is_macd_bull) else "🌟 分批低接"
                            elif bias_60_r >= 15.0:
                                eval_res = "⚠️ 減碼/勿追"
                            elif c_price > ma60_r and ma20_r > ma60_r:
                                if is_macd_bull and is_vol_surge:
                                    eval_res = "🔥 強烈買進"
                                elif is_macd_bull:
                                    eval_res = "✅ 偏多續抱"
                                else:
                                    eval_res = "⚠️ 多頭回檔"
                            elif is_down:
                                eval_res = "🛑 空頭避開"
                            else:
                                eval_res = "⏳ 觀望打底"

                            # 短線動能判斷
                            if is_vol_surge and is_macd_bull:
                                short_term_signal = "⚡ 出量點火"
                            elif is_vol_surge and not is_macd_bull:
                                short_term_signal = "📉 爆量下殺"
                            else:
                                short_term_signal = "💤 量縮整理"
                                
                            results.append({
                                "代碼": raw_sym,
                                "最新價": round(c_price, 2),
                                "乖離率(%)": round(bias_60_r, 2),
                                "綜合訊號": eval_res,
                                "短線動能": short_term_signal
                            })
                    except Exception:
                        pass
                
                if results:
                    df_results = pd.DataFrame(results)
                    
                    if short_term_filter:
                        df_results = df_results[df_results["短線動能"] == "⚡ 出量點火"]
                        
                    # 高價優先排序
                    df_results = df_results.sort_values(by="最新價", ascending=False)
                    
                    st.dataframe(df_results, use_container_width=True, hide_index=True)
                    
                    if short_term_filter and df_results.empty:
                        st.warning("👀 掃描名單中，今日無「出量點火」之高價股。建議保留資金，耐心等待。")
                    elif short_term_filter:
                        st.success("🎯 篩選成功！清單已依照股價由高至低排列。")
                    else:
                        st.success("✅ 掃描完成！已結合大盤濾網與技術分級。")
