import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 網頁基本設定 
st.set_page_config(page_title="三刀流全能戰情室", page_icon="⚔️", layout="centered")
st.title("⚔️ 操盤戰情室 (雷達版)")

# 2. 定義核心計算邏輯 (封裝成函數以供重複使用)
@st.cache_data(ttl=3600)
def fetch_and_analyze(symbol, asset_type="一般個股"):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty:
            return None
            
        # 處理資料格式
        close_series = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
        vol_series = df['Volume'].iloc[:, 0] if isinstance(df['Volume'], pd.DataFrame) else df['Volume']
        open_series = df['Open'].iloc[:, 0] if isinstance(df['Open'], pd.DataFrame) else df['Open']
        
        df = pd.DataFrame({'Close': close_series, 'Volume': vol_series, 'Open': open_series})
        
        # 計算均線
        ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
        ma60 = df['Close'].rolling(window=60).mean().iloc[-1]
        ma240 = df['Close'].rolling(window=240).mean().iloc[-1]
        vol_5ma = df['Volume'].rolling(window=5).mean().iloc[-1]
        
        # MACD
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        macd_hist = (macd - signal_line).iloc[-1]
        
        # 價格與乖離率
        last_3_closes = df['Close'].iloc[-3:].tolist()
        current_price = float(last_3_closes[-1])
        yesterday_price = float(last_3_closes[-2])
        current_open = float(df['Open'].iloc[-1])
        current_vol = float(df['Volume'].iloc[-1])
        
        bias_60 = ((current_price - ma60) / ma60) * 100
        is_gap_up = (current_open - yesterday_price) / yesterday_price > 0.02
        stable_above_60 = all(price > ma60 for price in last_3_closes)
        
        # 判斷參數
        sweet_threshold = -15.0 if asset_type == "一般個股" else -5.0
        is_downtrend = (current_price < ma60 and ma20 < ma60)
        is_macd_bearish = (macd_hist <= 0)
        
        # 訊號判定
        if stable_above_60 and ma20 > ma60:
            trend = "🟢 多頭"
            if is_gap_up:
                signal = "🚀 強勢跳空買入"
            elif current_vol > vol_5ma and not is_macd_bearish:
                signal = "🔥 量增波段起漲"
            else:
                signal = "✅ 持股續抱"
        elif is_downtrend:
            trend = "🔴 空頭"
            signal = "🛡️ 跌破防線觀望"
        else:
            trend = "⚪ 盤整"
            signal = "⏳ 震盪洗盤中"
            
        # 甜甜價否決鎖
        if bias_60 <= sweet_threshold:
            if is_downtrend or is_macd_bearish:
                signal = "🛑 陷阱! 強烈觀望"
            else:
                signal = "💎 甜甜價觸發"
                
        return {
            "最新價": round(current_price, 2),
            "季線(60MA)": round(ma60, 2),
            "乖離率(%)": round(bias_60, 2),
            "多空趨勢": trend,
            "戰術燈號": signal,
            "MACD動能": "多方" if not is_macd_bearish else "空方"
        }
    except Exception as e:
        return None

# 3. 建立雙分頁架構
tab_single, tab_radar = st.tabs(["🎯 單兵深度偵蒐", "🔥 戰略選股雷達"])

# ================= TAB 1: 單兵深度偵蒐 =================
with tab_single:
    col_input1, col_input2 = st.columns([2, 1])
    with col_input1:
        user_input = st.text_input("請輸入台股代碼 (例如：2308 或 00713)", "2308")
    with col_input2:
        asset_type = st.selectbox("資產屬性", ["一般個股", "高股息/防禦ETF"])

    stock_symbol = f"{user_input}.TW" if not (user_input.endswith(".TW") or user_input.endswith(".TWO")) else user_input
    
    st.subheader(f"當前監控: {stock_symbol}")
    
    res = fetch_and_analyze(stock_symbol, asset_type)
    if res is None:
        st.error("⚠️ 找不到該檔股票的資料。")
    else:
        st.markdown(f"### 當前狀態: **{res['多空趨勢']}**")
        
        # 顯示警示框
        if "買入" in res['戰術燈號'] or "起漲" in res['戰術燈號'] or "續抱" in res['戰術燈號']:
            st.success(f"**操作建議：{res['戰術燈號']}**")
            st.info(f"🛡️ 建議防守價位設在 **{res['季線(60MA)'] * 0.97:.2f}** 附近。")
        elif "觀望" in res['戰術燈號'] or "陷阱" in res['戰術燈號']:
            st.error(f"**操作建議：{res['戰術燈號']}**")
        elif "甜甜價" in res['戰術燈號']:
            sweet_price = res['季線(60MA)'] * (1 - 0.15 if asset_type == "一般個股" else 1 - 0.05)
            st.success(f"💎 **黃金甜甜價！** 估算價位約 **{sweet_price:.2f}** 以下，可考慮分批佈局。")
        else:
            st.warning(f"**操作建議：{res['戰術燈號']}**")

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("最新收盤價", res['最新價'])
        col2.metric("季線 (60MA)", res['季線(60MA)'])
        col3.metric("乖離率", f"{res['乖離率(%)']}%")
        st.markdown(f"> 📊 **底層數據**：MACD 動能柱顯示為 **{res['MACD動能']}**")

# ================= TAB 2: 戰略選股雷達 =================
with tab_radar:
    st.markdown("### 🔍 專家嚴選：十大高階智造與 AI 股")
    st.write("點擊下方按鈕，系統將自動掃描 10 檔口袋名單，找出今日突破與甜甜價標的。")
    
    # 預設 10 檔觀察名單
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
    
    if st.button("🚀 啟動全網域掃描"):
        with st.spinner('雷達掃描中，請稍候...'):
            results = []
            for symbol, name in watch_list.items():
                data = fetch_and_analyze(symbol, "一般個股")
                if data:
                    results.append({
                        "代碼": symbol.replace(".TW", ""),
                        "名稱": name,
                        "最新價": data["最新價"],
                        "乖離率(%)": data["乖離率(%)"],
                        "趨勢": data["多空趨勢"],
                        "戰術建議": data["戰術燈號"]
                    })
            
            # 呈現表格結果
            if results:
                df_results = pd.DataFrame(results)
                st.dataframe(df_results, use_container_width=True, hide_index=True)
                st.success("✅ 掃描完成！請優先關注戰術建議為「🚀、🔥、💎」的標的。")
            else:
                st.error("網路讀取失敗，請重新嘗試。")
