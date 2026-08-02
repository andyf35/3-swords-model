import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 網頁基本設定 
st.set_page_config(page_title="三刀流全能戰情室 (回測增強版)", page_icon="⚔️", layout="centered")
st.title("⚔️ 全能操盤戰情室 (回測增強版)")

# 2. 建立三分頁架構 (加入回測專區)
tab_single, tab_radar, tab_backtest = st.tabs(["🎯 單兵深度偵蒐與決策", "🔥 自動化戰略選股雷達", "📊 歷史回測與勝率統計"])

# ================= TAB 1: 單兵深度偵蒐與決策 =================
with tab_single:
    col_input1, col_input2 = st.columns([2, 1])
    with col_input1:
        user_input = st.text_input("請輸入台股代碼 (例如：00878 或 2308)", "2308", key="single_input")
    with col_input2:
        asset_type = st.selectbox("資產屬性", ["一般個股", "高股息/防禦ETF"], key="single_asset_type")

    if not user_input.endswith(".TW") and not user_input.endswith(".TWO"):
        stock_symbol = f"{user_input}.TW"
    else:
        stock_symbol = user_input

    st.subheader(f"當前監控標的: {stock_symbol} ({asset_type})")

    @st.cache_data(ttl=300)
    def get_single_data(symbol):
        data = yf.download(symbol, period="2y", interval="1d", progress=False)
        if not data.empty:
            data = data.ffill() 
        return data

    df = get_single_data(stock_symbol)

    ticker_obj = yf.Ticker(stock_symbol)
    try:
        pe_ratio = ticker_obj.info.get('trailingPE', 'N/A')
    except Exception:
        pe_ratio = 'N/A'

    if df.empty:
        st.error("⚠️ 找不到該檔股票的資料，請確認代碼是否正確。")
    else:
        close_series = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
        vol_series = df['Volume'].iloc[:, 0] if isinstance(df['Volume'], pd.DataFrame) else df['Volume']
        open_series = df['Open'].iloc[:, 0] if isinstance(df['Open'], pd.DataFrame) else df['Open']
            
        df['Close_1D'] = close_series
        df['Volume_1D'] = vol_series
        df['Open_1D'] = open_series
        
        df['月線_20MA'] = df['Close_1D'].rolling(window=20).mean()
        df['季線_60MA'] = df['Close_1D'].rolling(window=60).mean()
        df['年線_240MA'] = df['Close_1D'].rolling(window=240).mean()
        df['Volume_5MA'] = df['Volume_1D'].rolling(window=5).mean()
        
        exp12 = df['Close_1D'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close_1D'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['Signal']

        last_3_closes = df['Close_1D'].iloc[-3:].tolist()
        current_price = float(last_3_closes[-1])
        
        ma20 = float(df['月線_20MA'].iloc[-1])
        ma60 = float(df['季線_60MA'].iloc[-1])
        ma240 = float(df['年線_240MA'].iloc[-1])
        current_vol = float(df['Volume_1D'].iloc[-1])
        vol_5ma = float(df['Volume_5MA'].iloc[-1])
        macd_hist_val = float(df['MACD_Hist'].iloc[-1])

        bias_60 = ((current_price - ma60) / ma60) * 100
        stable_above_60 = all(price > ma60 for price in last_3_closes)

        sweet_threshold = -15.0 if asset_type == "一般個股" else -5.0
        overheat_threshold = 15.0 if asset_type == "一般個股" else 6.0

        is_downtrend = (current_price < ma60 and ma20 < ma60)
        is_macd_bull = (macd_hist_val > 0)
        is_vol_surge = (current_vol > vol_5ma)
        is_below_240ma = (current_price < ma240)

        st.markdown("### 📋 進場檢核清單 (Checklist)")
        c1 = "✅ 達成" if stable_above_60 else "❌ 未達標"
        c2 = "✅ 達成" if ma20 > ma60 else "❌ 未達標"
        c3 = "✅ 達成" if is_macd_bull else "❌ 未達標"
        c5 = "✅ 達成" if bias_60 < overheat_threshold else "❌ 過熱"
        c4 = "✅ 達成" if is_vol_surge and not (current_price < ma60 and not is_macd_bull) else ("❌ 危險" if is_vol_surge else "❌ 未達標")
        c6 = "❌ 跌破" if is_below_240ma else "✅ 達成"

        st.markdown(f"""
        > - **{c1}** ｜ **站穩防線**：連續三日站穩季線
        > - **{c2}** ｜ **多頭排列**：月線 (20MA) 大於季線 (60MA)
        > - **{c3}** ｜ **動能向上**：MACD 動能柱為紅/正數
        > - **{c4}** ｜ **量能狀態**：成交量與點火狀態判定
        > - **{c5}** ｜ **風險控管**：乖離率未過熱
        > - **{c6}** ｜ **長線保護**：股價維持在年線 (240MA) 之上
        """)

        st.markdown("### ⚖️ 綜合決策與資金配置建議")
        if bias_60 <= sweet_threshold and not (is_downtrend or not is_macd_bull):
            st.success("🌟 **【強烈買進 / 分批低接】**：跌至黃金甜蜜點且結構健康。")
        elif bias_60 >= overheat_threshold:
            st.warning("⚠️ **【減碼 / 觀望勿追】**：正乖離過大，慎防短線回檔。")
        elif current_price > ma60 and ma20 > ma60 and is_macd_bull:
            st.success("🔥 **【強烈買進 / 順勢點火】**：多頭排列且動能強勁。")
        elif is_downtrend and is_below_240ma:
            st.error("🛑 **【絕對不能買 / 下行趨勢確認】**：跌破季與年線，空頭成形。")
        else:
            st.info("⏳ **【觀望 / 震盪打底】**：等待明確突破訊號。")

        st.markdown("---")
        display_pe = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else "N/A"
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("月線 (20MA)", f"{ma20:.2f}")
        col2.metric("季線 (60MA)", f"{ma60:.2f}")
        col3.metric("年線 (240MA)", f"{ma240:.2f}")
        col4.metric("本益比 (PE)", display_pe)
        col5.metric("預估殖利率", "N/A")
        st.metric("最新日收盤價", f"{current_price:.2f}", delta=f"乖離率: {bias_60:.2f}%")

# ================= TAB 2: 自動化戰略選股雷達 =================
with tab_radar:
    st.markdown("### 🔍 自動化選股與戰略池雷達")
    pool_tech = st.checkbox("🔥 AI 與高階智造核心 (10檔)", value=True)
    pool_tw50 = st.checkbox("👑 台灣 50 權值大隊 (完整50檔)", value=False)
    pool_etf = st.checkbox("🛡️ 高股息與大型 ETF (10檔)", value=False)

    list_tech = ["2308", "2330", "1590", "2317", "2360", "2382", "2059", "3017", "2395", "1519"]
    list_tw50 = ["2330", "2317", "2454", "2308", "2382", "2881", "2882", "2303", "3711", "2891", "2886", "1301", "1303", "2002", "1216", "2884", "2885", "3008", "2357", "2892", "5880", "2880", "2883", "2887", "1101", "3034", "2327", "4904", "1326", "2912", "2890", "5871", "1590", "3037", "2395", "2379", "3231", "6669", "2345", "1402", "2408", "2801", "6505", "1102", "3045", "2301", "9910", "3661", "2603", "2609"]
    list_etf = ["0050", "006208", "00878", "00919", "0056", "00713", "00929", "00940", "0051", "00733"]

    target_symbols = []
    if pool_tech: target_symbols.extend(list_tech)
    if pool_tw50: target_symbols.extend(list_tw50)
    if pool_etf: target_symbols.extend(list_etf)
    target_symbols = list(set(target_symbols))

    only_recommend = st.checkbox("🌟 【僅顯示進攻與推薦標的】", value=False)

    if st.button("🚀 啟動自動化推薦雷達"):
        with st.spinner('雷達掃描中...'):
            results = []
            for raw_sym in target_symbols:
                symbol = f"{raw_sym}.TW"
                try:
                    df_r = yf.download(symbol, period="2y", interval="1d", progress=False).ffill()
                    if not df_r.empty:
                        c_s = df_r['Close'].iloc[:, 0] if isinstance(df_r['Close'], pd.DataFrame) else df_r['Close']
                        v_s = df_r['Volume'].iloc[:, 0] if isinstance(df_r['Volume'], pd.DataFrame) else df_r['Volume']
                        cp = float(c_s.iloc[-1])
                        m60 = float(c_s.rolling(60).mean().iloc[-1])
                        m20 = float(c_s.rolling(20).mean().iloc[-1])
                        v5 = float(v_s.rolling(5).mean().iloc[-1])
                        cv = float(v_s.iloc[-1])
                        
                        b60 = ((cp - m60) / m60) * 100
                        eval_res = "🔥 強烈買進" if (cp > m60 and m20 > m60 and cv > v5) else "⏳ 觀望打底"
                        results.append({"代碼": raw_sym, "最新價": round(cp, 2), "乖離率(%)": round(b60, 2), "綜合訊號": eval_res})
                except Exception:
                    pass
            if results:
                dfr = pd.DataFrame(results)
                if only_recommend: dfr = dfr[dfr["綜合訊號"] == "🔥 強烈買進"]
                st.dataframe(dfr, use_container_width=True, hide_index=True)

# ================= TAB 3: 歷史回測與勝率統計 =================
with tab_backtest:
    st.markdown("### 📊 策略歷史回測與勝率統計引擎")
    st.write("模擬過去 1 年內，當股票出現 **【出量點火 + 站穩季線】** 訊號時，持走特定天數後的歷史勝率與績效。")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        backtest_symbol = st.text_input("輸入回測股票代碼", "2308", key="bt_symbol")
    with col_b2:
        holding_days = st.selectbox("設定持有天數 (目標隔日沖或短波段)", [1, 2, 3, 5, 10], index=1)

    sym_str = f"{backtest_symbol}.TW" if not backtest_symbol.endswith(".TW") else backtest_symbol

    if st.button("📈 執行歷史回測分析"):
        with st.spinner("正在進行回測模擬運算..."):
            try:
                df_bt = yf.download(sym_str, period="1y", interval="1d", progress=False).ffill()
                if df_bt.empty:
                    st.error("⚠️ 查無歷史數據。")
                else:
                    c_s = df_bt['Close'].iloc[:, 0] if isinstance(df_bt['Close'], pd.DataFrame) else df_bt['Close']
                    v_s = df_bt['Volume'].iloc[:, 0] if isinstance(df_bt['Volume'], pd.DataFrame) else df_bt['Volume']
                    
                    m60_s = c_s.rolling(60).mean()
                    m20_s = c_s.rolling(20).mean()
                    v5_s = v_s.rolling(5).mean()
                    
                    trades = []
                    # 從第 60 天開始跑回測，避免均線 NaN
                    for i in range(60, len(c_s) - holding_days):
                        p_now = float(c_s.iloc[i])
                        m60_val = float(m60_s.iloc[i])
                        m20_val = float(m20_s.iloc[i])
                        v_now = float(v_s.iloc[i])
                        v5_val = float(v5_s.iloc[i])
                        
                        # 觸發條件：站穩季線 + 多頭排列 + 當日出量
                        if p_now > m60_val and m20_val > m60_val and v_now > v5_val:
                            p_future = float(c_s.iloc[i + holding_days])
                            ret = ((p_future - p_now) / p_now) * 100
                            trades.append({
                                "進場日期": str(df_bt.index[i].date()),
                                "進場價": round(p_now, 2),
                                f"持有{holding_days}天後賣出價": round(p_future, 2),
                                "報酬率(%)": round(ret, 2),
                                "結果": "贏 🟢" if ret > 0 else "輸 🔴"
                            })
                    
                    if trades:
                        df_trades = pd.DataFrame(trades)
                        total_trades = len(df_trades)
                        win_trades = len(df_trades[df_trades["報酬率(%)"] > 0])
                        win_rate = (win_trades / total_trades) * 100
                        avg_return = df_trades["報酬率(%)"].mean()
                        max_drawdown = df_trades["報酬率(%)"].min()
                        
                        st.markdown("#### 🏆 回測總結表現")
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("總觸發次數", f"{total_trades} 次")
                        m2.metric("策略勝率", f"{win_rate:.1f}%")
                        m3.metric("平均報酬率", f"{avg_return:.2f}%")
                        m4.metric("單筆最大回檔", f"{max_drawdown:.2f}%")
                        
                        st.markdown("---")
                        st.markdown("#### 📜 歷史逐筆交易明細")
                        st.dataframe(df_trades, use_container_width=True, hide_index=True)
                    else:
                        st.warning("⚠️ 在過去一年內，該標的無符合條件的觸發次數。")
            except Exception as e:
                st.error(f"回測執行發生錯誤：{e}")
