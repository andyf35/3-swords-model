import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from FinMind.data import DataLoader

# 1. 初始化台灣證交所/櫃買中心開源資料庫介面
api = DataLoader()

# 2. 網頁基本設定 (寬螢幕)
st.set_page_config(page_title="三刀流全能戰情室 (官方數據版)", page_icon="⚔️", layout="wide")
st.title("⚔️ 全能操盤戰情室 (TWSE 官方數據旗艦版)")

# ================= 🚦 大盤環境紅綠燈 =================
@st.cache_data(ttl=300)
def get_market_trend():
    try:
        # 取得加權指數 (TAIEX) 近半年資料
        start_date = (pd.Timestamp.now() - pd.Timedelta(days=150)).strftime('%Y-%m-%d')
        df = api.taiwan_stock_daily(stock_id='TAIEX', start_date=start_date)
        if df.empty:
            return 0, 0, True
            
        close_s = df['close']
        ma60 = float(close_s.rolling(60).mean().iloc[-1])
        cp = float(close_s.iloc[-1])
        return cp, ma60, cp > ma60
    except:
        return 0, 0, True 

market_cp, market_ma60, is_market_bull = get_market_trend()
if is_market_bull:
    st.success(f"🚦 **大盤環境：🟢 綠燈通行** (加權指數 {market_cp:.0f} 站穩季線 {market_ma60:.0f}，順勢波段操作，可動用標準資金)")
else:
    st.error(f"🚦 **大盤環境：🔴 紅燈警戒** (加權指數 {market_cp:.0f} 跌破季線 {market_ma60:.0f}，系統性風險升高，強制減碼或觀望)")
st.markdown("---")

# 3. 建立雙分頁架構
tab_single, tab_radar = st.tabs(["🎯 單兵深度偵蒐與決策", "🔥 自動化戰略選股雷達"])

# ================= TAB 1: 單兵深度偵蒐與決策 =================
with tab_single:
    col_input1, col_input2 = st.columns([2, 1])
    with col_input1:
        user_input = st.text_input("請輸入台股代碼 (直接輸入數字，例如：00878 或 2308)", "2308", key="single_input")
    with col_input2:
        asset_type = st.selectbox("資產屬性", ["一般個股", "高股息/防禦ETF"], key="single_asset_type")

    # 過濾掉可能殘留的 .TW 尾綴
    raw_symbol = user_input.replace('.TW', '').replace('.TWO', '').strip()
    st.subheader(f"當前監控標的: {raw_symbol} ({asset_type})")

    @st.cache_data(ttl=300)
    def get_single_data(symbol):
        # 抓取過去約 400 天，以確保能算出 240MA
        start_date = (pd.Timestamp.now() - pd.Timedelta(days=400)).strftime('%Y-%m-%d')
        try:
            df = api.taiwan_stock_daily(stock_id=symbol, start_date=start_date)
            if df.empty: return pd.DataFrame()
            
            # 將官方欄位名稱轉換為系統分析格式
            df = df.rename(columns={'date': 'Date', 'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close', 'Trading_Volume': 'Volume'})
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            return df
        except:
            return pd.DataFrame()

    df = get_single_data(raw_symbol)

    # 🛡️ 安全防護：從證交所抓取本益比與殖利率
    pe_ratio = 'N/A'
    div_str = 'N/A'
    try:
        info_date = (pd.Timestamp.now() - pd.Timedelta(days=15)).strftime('%Y-%m-%d')
        info_df = api.taiwan_stock_per_pbr_and_dividend_yield(stock_id=raw_symbol, start_date=info_date)
        if not info_df.empty:
            pe_val = info_df['PER'].iloc[-1]
            div_val = info_df['dividend_yield'].iloc[-1]
            if pd.notna(pe_val) and pe_val > 0:
                pe_ratio = round(pe_val, 2)
            if pd.notna(div_val) and div_val > 0:
                div_str = f"{div_val}%"
    except:
        pass

    if df.empty:
        st.error("⚠️ 無法從證交所取得該檔股票資料，請確認代碼是否正確。")
    else:
        c_series = df['Close']
        v_series = df['Volume']
        o_series = df['Open']
        h_series = df['High']
        l_series = df['Low']
            
        df['月線_20MA'] = c_series.rolling(window=20).mean()
        df['季線_60MA'] = c_series.rolling(window=60).mean()
        df['年線_240MA'] = c_series.rolling(window=240).mean()
        df['Volume_5MA'] = v_series.rolling(window=5).mean()
        
        macd = c_series.ewm(span=12, adjust=False).mean() - c_series.ewm(span=26, adjust=False).mean()
        df['MACD_Hist'] = macd - macd.ewm(span=9, adjust=False).mean()

        df['Prev_Close'] = c_series.shift(1)
        tr1 = h_series - l_series
        tr2 = (h_series - df['Prev_Close']).abs()
        tr3 = (l_series - df['Prev_Close']).abs()
        df['TR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR_14'] = df['TR'].rolling(window=14).mean()

        last_3_closes = c_series.iloc[-3:].tolist()
        current_price = float(last_3_closes[-1])
        
        ma20, ma60, ma240 = float(df['月線_20MA'].iloc[-1]), float(df['季線_60MA'].iloc[-1]), float(df['年線_240MA'].iloc[-1])
        current_vol, vol_5ma = float(v_series.iloc[-1]), float(df['Volume_5MA'].iloc[-1])
        macd_hist_val = float(df['MACD_Hist'].iloc[-1])
        current_atr = float(df['ATR_14'].iloc[-1])

        bias_60 = ((current_price - ma60) / ma60) * 100
        stable_above_60 = all(price > ma60 for price in last_3_closes)
        
        sweet_threshold, overheat_threshold = (-15.0, 15.0) if asset_type == "一般個股" else (-5.0, 6.0)

        is_downtrend = (current_price < ma60 and ma20 < ma60)
        is_macd_bull = (macd_hist_val > 0)
        is_vol_surge = (current_vol > vol_5ma)
        is_below_240ma = (current_price < ma240)

        # 📈 視覺化 K 線
        st.markdown("### 📈 戰情動態走勢圖 (近半年)")
        df_plot = df.iloc[-120:].copy() 
        fig = go.Figure(data=[go.Candlestick(x=df_plot.index, open=o_series.iloc[-120:], high=h_series.iloc[-120:], low=l_series.iloc[-120:], close=c_series.iloc[-120:], name="日K線")])
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['月線_20MA'], name='月線 (20MA)', line=dict(color='blue', width=1.5)))
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['季線_60MA'], name='季線 (60MA - 生命線)', line=dict(color='orange', width=2)))
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['年線_240MA'], name='年線 (240MA)', line=dict(color='purple', width=2)))
        fig.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0), height=450, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        
        col_chk, col_dec = st.columns([1, 1.2])
        
        with col_chk:
            st.markdown("### 📋 進場檢核清單")
            c1 = "✅ 達成" if stable_above_60 else "❌ 未達標"
            c2 = "✅ 達成" if ma20 > ma60 else "❌ 未達標"
            c3 = "✅ 達成" if is_macd_bull else "❌ 未達標"
            c5 = "✅ 達成" if bias_60 < overheat_threshold else "❌ 過熱"
            c4 = "❌ 危險 (爆量下殺)" if (is_vol_surge and current_price < ma60 and not is_macd_bull) else ("✅ 達成 (出量點火)" if is_vol_surge else "❌ 未達標 (量能平淡)")
            c6 = "❌ 跌破 (年線失守)" if is_below_240ma else "✅ 達成 (長線保護)"

            st.markdown(f"""
            > - **{c1}** ｜ **站穩防線**：連三日站穩季線
            > - **{c2}** ｜ **多頭排列**：20MA > 60MA
            > - **{c3}** ｜ **動能向上**：MACD 紅柱
            > - **{c4}** ｜ **量能狀態**：成交量檢核
            > - **{c5}** ｜ **風險控管**：乖離率 < {overheat_threshold}%
            > - **{c6}** ｜ **長線保護**：股價 > 240MA
            """)

        with col_dec:
            st.markdown("### ⚖️ 綜合決策與資金配置")
            grade_title, grade_desc, color = "", "", "info"
            
            if bias_60 <= sweet_threshold and not (is_downtrend or not is_macd_bull):
                grade_title, grade_desc, color = "🌟【強烈買進 / 分批低接】", "跌至黃金甜蜜點且結構健康。", "success"
            elif bias_60 >= overheat_threshold:
                grade_title, grade_desc, color = "⚠️【減碼 / 觀望勿追】", "正乖離過大，慎防短線回檔。", "warning"
            elif current_price > ma60 and ma20 > ma60 and is_macd_bull:
                grade_title, grade_desc, color = "🔥【強烈買進 / 順勢點火】", "多頭排列且動能強勁。", "success"
            elif is_downtrend and is_below_240ma:
                grade_title, grade_desc, color = "🛑【絕對不能買 / 空頭成形】", "跌破季與年線，全面轉空。", "error"
            else:
                grade_title, grade_desc, color = "⏳【觀望 / 震盪打底】", "缺乏明確進場理由，等待突破。", "info"

            if color == "success": st.success(f"**{grade_title}**\n\n{grade_desc}")
            elif color == "error": st.error(f"**{grade_title}**\n\n{grade_desc}")
            elif color == "warning": st.warning(f"**{grade_title}**\n\n{grade_desc}")
            else: st.info(f"**{grade_title}**\n\n{grade_desc}")

            if color == "success":
                entry_high = current_price
                entry_low = max(ma20, ma60) 
                stop_loss = ma60 - (current_atr * 1.5) 
                risk_per_share = current_price - stop_loss
                risk_per_1000 = max(0, risk_per_share * 1000)
                target_price = current_price + (risk_per_share * 2)
                reward_per_1000 = (target_price - current_price) * 1000

                st.markdown("### 🛡️ 專業風控推演 (買進 1 張試算)")
                st.markdown(f"""
                * 🎯 **最佳進場區間**：**{entry_low:.1f} ~ {entry_high:.1f}** 元 (收盤價與月線之間分批低接)
                * 🛑 **ATR 防守底線**：**{stop_loss:.1f}** 元 (季線向下緩衝 1.5 倍 ATR `{current_atr:.1f}`)
                * 🩸 **單筆最大風險**：若跌破停損，預估虧損 **-NT$ {risk_per_1000:,.0f}**
                * 🏆 **合理停利目標**：**{target_price:.1f}** 元以上 (盈虧比 1:2，預估獲利 **+NT$ {reward_per_1000:,.0f}**)
                """)
                
                if risk_per_1000 > 10000:
                    st.warning("⚠️ 系統警示：由於該股近期波動率(ATR)過大或離季線較遠，單筆停損金額破萬。建議改買零股或等回檔縮小風險距離。")

        st.markdown("---")
        st.markdown("### 📊 關鍵指標總覽")
        row1_c1, row1_c2, row1_c3, row1_c4 = st.columns(4)
        row1_c1.metric("月線 (20MA)", f"{ma20:.2f}")
        row1_c2.metric("季線 (60MA)", f"{ma60:.2f}")
        row1_c3.metric("年線 (240MA)", f"{ma240:.2f}")
        row1_c4.metric("真實波動 (ATR)", f"{current_atr:.2f}")

        row2_c1, row2_c2, row2_c3 = st.columns(3)
        pe_display = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else str(pe_ratio)
        row2_c1.metric("本益比 (PE)", pe_display)
        row2_c2.metric("預估殖利率", div_str)
        row2_c3.metric("最新日收盤價", f"{current_price:.2f}", delta=f"乖離率: {bias_60:.2f}%")

# ================= TAB 2: 自動化戰略選股雷達 =================
with tab_radar:
    st.markdown("### 🔍 自動化選股與戰略池雷達")
    col_pool1, col_pool2, col_pool3 = st.columns(3)
    with col_pool1: pool_tech = st.checkbox("🔥 AI 與高階智造核心 (10檔)", value=True)
    with col_pool2: pool_tw50 = st.checkbox("👑 台灣 50 權值大隊 (50檔)", value=False)
    with col_pool3: pool_etf = st.checkbox("🛡️ 高股息與大型 ETF (10檔)", value=False)

    list_tech = ["2308", "2330", "1590", "2317", "2360", "2382", "2059", "3017", "2395", "1519"]
    list_tw50 = ["2330", "2317", "2454", "2308", "2382", "2881", "2882", "2303", "3711", "2891", "2886", "1301", "1303", "2002", "1216", "2884", "2885", "3008", "2357", "2892", "5880", "2880", "2883", "2887", "1101", "3034", "2327", "4904", "1326", "2912", "2890", "5871", "1590", "3037", "2395", "2379", "3231", "6669", "2345", "1402", "2408", "2801", "6505", "1102", "3045", "2301", "9910", "3661", "2603", "2609"]
    list_etf = ["0050", "006208", "00878", "00919", "0056", "00713", "00929", "00940", "0051", "00733"]

    target_symbols = []
    if pool_tech: target_symbols.extend(list_tech)
    if pool_tw50: target_symbols.extend(list_tw50)
    if pool_etf: target_symbols.extend(list_etf)
    
    with st.expander("➕ 想要臨時另外手動加看其他股票嗎？"):
        custom_add = st.text_input("輸入要額外加入的代碼 (用半形逗號隔開，純數字即可)：", value="")
        if custom_add.strip():
            target_symbols.extend([s.strip() for s in custom_add.split(',') if s.strip()])
            
    target_symbols = list(set(target_symbols))
    only_recommend = st.checkbox("🌟 【僅顯示進攻與推薦標的】", value=False)

    if st.button("🚀 啟動自動化推薦雷達"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        total_stocks = len(target_symbols)
        
        for i, raw_sym in enumerate(target_symbols):
            if not raw_sym: continue
            
            # 清理代碼，對接台灣官方資料源只需純數字
            clean_sym = raw_sym.replace('.TW', '').replace('.TWO', '')
            status_text.text(f"📡 正在從證交所接收 {clean_sym} 的數據 ({i+1}/{total_stocks})...")
            
            try:
                start_date = (pd.Timestamp.now() - pd.Timedelta(days=400)).strftime('%Y-%m-%d')
                df_r = api.taiwan_stock_daily(stock_id=clean_sym, start_date=start_date)
                
                if not df_r.empty:
                    c_s = df_r['close']
                    v_s = df_r['Trading_Volume']
                    
                    cp = float(c_s.iloc[-1])
                    cv = float(v_s.iloc[-1])
                    m60 = float(c_s.rolling(60).mean().iloc[-1])
                    m20 = float(c_s.rolling(20).mean().iloc[-1])
                    v5 = float(v_s.rolling(5).mean().iloc[-1])
                    
                    # 💧 流動性濾網 (日均成交額 > 1 億)
                    daily_turnover = cp * cv
                    is_liquid = daily_turnover >= 100_000_000

                    b60 = ((cp - m60) / m60) * 100
                    
                    if not is_liquid:
                        eval_res = "💧 流動性不足"
                    elif b60 <= -15.0:
                        eval_res = "🌟 分批低接" if (cp > m60 and m20 > m60) else "🛑 絕對不能買"
                    elif b60 >= 15.0:
                        eval_res = "⚠️ 減碼/勿追"
                    elif cp > m60 and m20 > m60 and cv > v5:
                        eval_res = "🔥 強烈買進"
                    elif cp < m60 and m20 < m60:
                        eval_res = "🛑 下行確認"
                    else:
                        eval_res = "⏳ 觀望打底"

                    short_term = "⚡ 出量點火" if (cv > v5) else "💤 量縮整理"
                        
                    results.append({"代碼": clean_sym, "最新價": round(cp, 2), "乖離率(%)": round(b60, 2), "綜合訊號": eval_res, "短線動能": short_term})
                
                # 安全緩衝，遵守官方開源資料庫請求速率原則
                time.sleep(0.1)
                
            except:
                pass
                
            progress_bar.progress((i + 1) / total_stocks)
            
        status_text.text("✅ 雷達掃描完成！")
        time.sleep(1)
        status_text.empty()
        progress_bar.empty()
                
        if results:
            dfr = pd.DataFrame(results)
            if only_recommend: 
                dfr = dfr[dfr["綜合訊號"].isin(["🔥 強烈買進", "🌟 分批低接"])]
            dfr = dfr.sort_values(by="最新價", ascending=False)
            st.dataframe(dfr, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ 目前暫無數據回傳，請確認伺服器連線狀態。")
