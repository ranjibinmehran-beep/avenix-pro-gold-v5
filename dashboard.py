import streamlit as st
import subprocess
import sys
import time
import threading

# --- BULLETPROOF SELF-INSTALLATION HEADER ---
try:
    import ccxt
    import pandas as pd
    import numpy as np
    import plotly
    import requests
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "ccxt", "pandas", "numpy", "plotly", "requests"])
    st.rerun()

import json
import os
import datetime
import streamlit.components.v1 as components
from bot import RealTimeTradingBot
from execution import OrderExecutionEngine
from signal_room import SignalRoom

# --- MANUAL TRADE ALERTS -------------------------------------------------
def notify_manual_open(symbol, side, entry, sl, tp1, tp2, tp3, lot):
    """Send an open-trade alert for a manually executed order."""
    try:
        room = SignalRoom()
        arrow = "🟢 خرید (BUY)" if side == "BUY" else "🔴 فروش (SELL)"
        msg = (
            f"⚡️ *معامله دستی در آونیکس ثبت شد* ⚡️\n\n"
            f"📈 *نماد:* {symbol}\n"
            f"↕️ *جهت:* {arrow}\n"
            f"💵 *قیمت ورود:* {entry}\n"
            f"📦 *حجم:* {lot}\n\n"
            f"🛑 *حد ضرر (SL):* {round(sl, 5)}\n"
            f"🎯 *TP1:* {round(tp1, 5)}\n"
            f"🎯 *TP2:* {round(tp2, 5)}\n"
            f"🎯 *TP3:* {round(tp3, 5)}\n\n"
            f"⏰ *زمان:* {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"👤 *این معامله به صورت دستی توسط تریدر باز شد*"
        )
        if room.config.get("enable_telegram", False):
            room.send_telegram_message(msg)
        if room.config.get("enable_bale", False):
            room.send_bale_message(msg)
        if room.config.get("enable_whatsapp", False):
            room.send_whatsapp_message(msg)
    except Exception as e:
        print(f"[ManualAlert-Open] {e}")

def notify_manual_close(trade):
    """Send a close alert for a manually closed position (green/red)."""
    try:
        SignalRoom().send_closed_trade_alert(trade)
    except Exception as e:
        print(f"[ManualAlert-Close] {e}")
# -------------------------------------------------------------------------

# Page Configuration - Clean & Modern Layout
st.set_page_config(
    page_title="Avenix Smart Trading Suite",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Premium iOS-like minimalist styling CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;700&display=swap');
    
    html, body, [data-testid="stSidebar"] {
        font-family: 'Vazirmatn', sans-serif !important;
        direction: rtl;
        text-align: right;
    }
    .stMarkdown, .stButton, .stText, h1, h2, h3, h4, h5, h6 {
        direction: rtl !important;
        text-align: right !important;
    }
    /* Clean Cards */
    .ios-card {
        background-color: #1e293b;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        border: 1px solid #2e3e4f;
        margin-bottom: 12px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #10b981;
        margin-top: 4px;
    }
    .metric-title {
        font-size: 13px;
        color: #94a3b8;
    }
    /* Tab Styling */
    .stTabs [data-basetab="tab"] {
        font-size: 16px;
        font-weight: 500;
        height: 50px;
        padding: 0 20px;
    }
    /* Brochure card style */
    .brochure-card {
        background-color: #0f172a;
        border-right: 5px solid #3b82f6;
        border-radius: 10px;
        padding: 16px;
        margin-top: 10px;
        line-height: 1.7;
        font-size: 13px;
        color: #cbd5e1;
    }
    /* Checklist style */
    .checklist-item {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid #2e3e4f;
    }
    /* Disclaimer layout */
    .disclaimer-text {
        font-size: 13px;
        color: #e2e8f0;
        line-height: 1.8;
        text-align: justify;
    }
    /* Live HUD Bar */
    .hud-banner {
        border-radius: 10px;
        padding: 12px 18px;
        margin-bottom: 20px;
        text-align: center;
        font-weight: 700;
        font-size: 15px;
    }
    
    /* Force horizontal column layout on mobile screens to match TradingView widgets */
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            gap: 8px !important;
            width: 100% !important;
        }
        div[data-testid="column"] {
            min-width: 0px !important;
            width: auto !important;
            flex: 1 1 0% !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Helper functions to load data
def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(config_data):
    with open("config.json", "w") as f:
        json.dump(config_data, f, indent=2)

def load_portfolio():
    if os.path.exists("portfolio.json"):
        with open("portfolio.json", "r") as f:
            return json.load(f)
    return {"balance": 10000.0, "active_trades": [], "completed_trades": []}

def save_portfolio(portfolio):
    with open("portfolio.json", "w") as f:
        json.dump(portfolio, f, indent=2)

def load_signals():
    if os.path.exists("signal_room.json"):
        with open("signal_room.json", "r") as f:
            return json.load(f)
    return []

def is_forex_market_closed():
    # Returns True if current UTC time is between Friday 22:00 UTC and Sunday 22:00 UTC
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    weekday = now.weekday() # 0 is Monday, ..., 4 is Friday, 5 is Saturday, 6 is Sunday
    if weekday == 5: # Saturday
        return True
    elif weekday == 4: # Friday
        return now.hour >= 22
    elif weekday == 6: # Sunday
        return now.hour < 22
    return False

def is_crypto_symbol(symbol):
    symbol_upper = symbol.upper()
    crypto_keywords = ["USDT", "BTC", "ETH", "BNB", "SOL", "DOGE", "XRP", "ADA", "TON"]
    non_crypto_keywords = ["XAU", "XAG", "PLATINUM", "PALLADIUM", "EUR", "GBP", "USD/JPY", "JPY", "AUD", "CAD", "CHF", "NZD", "BRENT", "UKOIL"]
    if any(k in symbol_upper for k in crypto_keywords):
        return True
    if any(nc in symbol_upper for nc in non_crypto_keywords):
        return False
    return True

config = load_config()

def symbol_mapping_back(mt5_symbol):
    sym = mt5_symbol.upper()
    if "XAU" in sym: return "XAU/USD"
    if "XAG" in sym: return "XAG/USD"
    if "EURUSD" in sym: return "EUR/USD"
    if "GBPUSD" in sym: return "GBP/USD"
    if "USDJPY" in sym: return "USD/JPY"
    if "BTC" in sym: return "BTC/USDT"
    if "ETH" in sym: return "ETH/USDT"
    if "SOL" in sym: return "SOL/USDT"
    if len(sym) == 6 and not "/" in sym:
        return f"{sym[:3]}/{sym[3:]}"
    return mt5_symbol

def sync_live_mt5_data():
    if config.get("broker_type") == "forex_mt5":
        try:
            import MetaTrader5 as mt5
            import datetime
            if mt5.initialize():
                account = config.get("mt5_account_id", "")
                password = config.get("mt5_password", "")
                server = config.get("mt5_server", "")
                if account and password:
                    authorized = mt5.login(login=int(account), password=password, server=server)
                    if authorized:
                        acc_info = mt5.account_info()
                        if acc_info:
                            portfolio = load_portfolio()
                            portfolio["balance"] = acc_info.balance
                            
                            # Fetch last 90 days deals history from MT5
                            from_date = datetime.datetime.now() - datetime.timedelta(days=90)
                            to_date = datetime.datetime.now()
                            deals = mt5.history_deals_get(from_date, to_date)
                            
                            if deals:
                                completed_trades_list = []
                                for d in deals:
                                    if d.entry == 1:  # DEAL_ENTRY_OUT (closed trade)
                                        original_side = "BUY" if d.type == 1 else "SELL"
                                        qty = d.volume
                                        pnl = d.profit + d.commission + d.swap
                                        close_price = d.price
                                        
                                        entry_price = 0.0
                                        for open_deal in deals:
                                            if open_deal.position_id == d.position_id and open_deal.entry == 0:
                                                entry_price = open_deal.price
                                                break
                                                
                                        close_time = datetime.datetime.fromtimestamp(d.time).strftime('%Y-%m-%d %H:%M:%S')
                                        completed_trades_list.append({
                                            "symbol": symbol_mapping_back(d.symbol),
                                            "side": original_side,
                                            "qty": qty,
                                            "entry_price": entry_price,
                                            "close_price": close_price,
                                            "pnl": round(pnl, 2),
                                            "close_time": close_time,
                                            "account_id": str(account),
                                            "status": "CLOSED"
                                        })
                                portfolio["completed_trades"] = completed_trades_list
                            
                            save_portfolio(portfolio)
        except Exception as e:
            print(f"[Live MT5 Sync Error]: {e}")

# Run Sync on Load
sync_live_mt5_data()

portfolio = load_portfolio()
signals = load_signals()

# ----------------- 🚨 INSTITUTIONAL 24/7 BACKGROUND SCANNING DAEMON -----------------
@st.cache_resource
def spawn_background_bot_daemon():
    bot_instance = RealTimeTradingBot()
    def background_loop():
        while True:
            try:
                bot_instance.run_one_cycle()
            except Exception as e:
                print(f"[Daemon Error]: {e}")
            time.sleep(15)
    daemon_thread = threading.Thread(target=background_loop, daemon=True)
    daemon_thread.start()
    return "AVENIX_DAEMON_ACTIVE"

spawn_background_bot_daemon()

# Initialize Session State for Legal Welcome Gate
if "terms_accepted" not in st.session_state:
    st.session_state.terms_accepted = False

# Setup language selector on the top-right header
lang_col1, lang_col2 = st.columns([7, 3])
with lang_col2:
    selected_lang = st.selectbox("🌐 Choose Language / انتخاب زبان", ["English", "فارسی", "العربية", "Türkçe"], index=1)

lang_code = "fa" if selected_lang == "فارسی" else ("en" if selected_lang == "English" else ("ar" if selected_lang == "العربية" else "tr"))

# Complete 4-Language UI Dictionary - ensuring ZERO missing keys!
TXT = {
    "fa": {
        "title": "🦅 پلتفرم معاملاتی هوشمند آونیکس",
        "sub": "پلتفرم معامله‌گری و ترید خودکار طلا، جفت‌ارزها و ارزهای دیجیتال",
        "tab_chart": "📊 اتاق چارت تریدینگ‌ویو",
        "tab_brain": "🧠 اتاق فرمان مغز ربات (AI)",
        "tab_signals": "📢 آرشیو سیگنال‌ها",
        "tab_broker": "🔌 اتاق اتصال کارگزاری (Broker Connection)",
        "tab_contest": "🏆 اتاق فانددنکست (FundedNext Portal)",
        "tab_settings": "⚙️ تنظیمات فوق‌پیشرفته سیستم",
        "tab_history": "📜 تاریخچه معاملات حساب",
        "selector_symbol": "انتخاب نماد معاملاتی جهت تحلیل زنده",
        "selector_tf": "تایم فریم چارت",
        "tv_caption": "🌐 <b>اتاق چارت تریدینگ‌ویو:</b> این نمودار کاملاً ریسپانسیو و تمام‌صفحه است. شما می‌توانید در گذشته بازار اسکرول کنید، ابزارهای ترسیمی اضافه کنید و اندیکاتورها را شخصی‌سازی کنید.",
        "brain_telemetry": "🧠 پایش مانیتورینگ مغز ربات و وضعیت اندیکاتورها",
        "brain_sub": "نمایش زنده امتیازدهی مغز سیستم و تاییده‌های تفکیک‌شده‌ی هر اندیکاتور",
        "force_scan_desc": "ربات در هر ۱۰ ثانیه کل بازار را مجدداً اسکن می‌کند. شما می‌توانید جهت تحلیل آنی دکمه روبرو را فشار دهید:",
        "force_scan_btn": "🔥 اجرای فوری آنالیز مغز ربات",
        "isolated_checklist": "📊 تاییده‌های تفکیک‌شده‌ی اندیکاتورها",
        "brain_score_title": "امتیاز فعلی همگرایی اندیکاتورها (Brain Score)",
        "score_threshold_desc": "حد نصاب ورود",
        "checklist_title": "وضعیت تک‌تک اندیکاتورها در آخرین تحلیل:",
        "pnl_report": "💼 گزارش موقعیت‌ها و معاملات زنده",
        "balance_title": "دارایی کل حساب دمو (Balance)",
        "active_trades_title": "معاملات فعال بازار",
        "broker_badge_title": "بستر معاملاتی متصل",
        "paper_badge": "شبیه‌ساز (دمو)",
        "real_badge": "حساب واقعی بروکر",
        "active_pnl": "سود زنده",
        "entry_price": "قیمت ورود",
        "live_price": "قیمت زنده",
        "current_sl": "حد ضرر فعلی",
        "original_sl": "حد ضرر اولیه",
        "targets": "اهداف حد سود",
        "trailing_step": "پله حد ضرر شناور",
        "completed_history": "✅ تاریخچه معاملات بسته شده",
        "exit_reason": "خروج با",
        "exit_time": "زمان خروج",
        "pnl_result": "نتیجه سود/زیان",
        "no_active_trades": "در حال حاضر هیچ معامله فعالی باز نیست.",
        "no_completed_trades": "تاریخچه معاملات بسته شده خالی است.",
        "settings_title": "⚙️ تنظیمات فوق‌پیشرفته اندیکاتورها و مغز سیستم",
        "ind_custom": "📊 شخصی‌سازی مجزای اندیکاتورها",
        "emas_title": "۱. میانگین‌های متحرک (EMAs)",
        "fast_ema": "دوره موینگ سریع (Fast EMA)",
        "medium_ema": "دوره موینگ میان‌مدت (Medium EMA)",
        "long_ema": "دوره موینگ بلندمدت روند (Long EMA)",
        "ich_title": "۲. ابر ایچیموکو (Ichimoku)",
        "tenkan_val": "دوره خط تبدیل (Tenkan-sen)",
        "kijun_val": "دوره خط پایه (Kijun-sen)",
        "span_b_val": "دوره خط سنکو ب (Senkou Span B)",
        "rsi_title": "۳. شاخص قدرت (RSI)",
        "rsi_period": "دوره زمانی RSI",
        "rsi_os": "مرز اشباع فروش (Oversold)",
        "rsi_ob": "مرز اشباع خرید (Overbought)",
        "macd_title": "۴. اندیکاتور MACD",
        "macd_fast": "موینگ سریع مکدی",
        "macd_slow": "موینگ کند مکدی",
        "macd_signal": "خط سیگنال مکدی",
        "bb_title": "۵. باندهای بولینگر (Bollinger)",
        "bb_period": "دوره زمانی باند بولینگر",
        "bb_std": "انحراف معیار (Std Dev)",
        "risk_title": "🛡️ درصد ریسک، اهداف حد سود و بستر معاملاتی",
        "risk_pct": "درصد ریسک روی کل حساب (%)",
        "leverage": "ضریب اهرم صرافی (Leverage)",
        "score_thresh": "حد نصاب امتیاز تاییدیه مغز ربات جهت ترید %",
        "broker_connect_title": "انتخاب بستر اتصال و اجرای معاملات (ریل / دمو)",
        "mt5_desc": "🔌 اتصال به کارگزاری فارکس (لایت فایننس، آلپاری) یا حساب‌های چالش پروپ‌فرم (FundedNext):",
        "prop_guard_title": "🛡️ سیستم ضد کال‌مارجین و محافظ چالش‌های پروپ‌فرم (Avenix Prop Guard)",
        "prop_limit_desc": "حداکثر دروداون (افت سرمایه) مجاز روزانه حساب %",
        "prop_locked_err": "🚨 قفل محافظ دروداون روزانه فعال شده است! معاملات موقتاً مسدود هستند.",
        "prop_unlock_btn": "🔓 ریست کردن دستی قفل دروداون روزانه ربات",
        "prop_safe": "🟢 محافظ دروداون روزانه فعال و حساب در حاشیه امنیت کامل قرار دارد.",
        "tp_reward": "🎯 تنظیم ضرایب ریوارد اهداف سود پله‌ای (Trailing Take Profits)",
        "social_broadcast_title": "### ✉️ اتاق مدیریت انتشار سیگنال‌ها (Bale, Telegram, WhatsApp)",
        "social_broadcast_sub": "ارسال فوق‌سریع و همزمان بروشورهای تحلیلی ربات به پیام‌رسان‌های ایرانی و خارجی",
        "tg_title": "۱. پیام‌رسان تلگرام (Telegram)",
        "tg_enable": "فعال‌سازی ارسال به تلگرام",
        "tg_token": "توکن ربات تلگرام",
        "tg_chat": "آیدی چت / کانال تلگرام",
        "bale_title": "۲. پیام‌رسان ایرانی بله (Bale)",
        "bale_enable": "فعال‌سازی ارسال به بله",
        "bale_token": "توکن ربات بله (Bale Token)",
        "bale_chat": "آیدی چت / کانال بله",
        "wa_title": "۳. پیام‌رسان واتس‌اپ (WhatsApp)",
        "wa_enable": "فعال‌سازی ارسال به واتس‌اپ",
        "wa_inst": "شناسه درگاه (Instance ID)",
        "wa_token": "توکن درگاه واتس‌اپ",
        "wa_phone": "شماره تلفن مقصد (مثلاً 989123456789)",
        "symbols_under_watch": "نمادهای تحت نظر (با کاما جدا کنید)",
        "main_tf_scan": "تایم‌فریم اصلی ورود و تحلیل مغز ربات",
        "reset_wallet_btn": "🔄 ریست کردن کیف پول معاملاتی دمو",
        "save_settings_btn": "💾 ذخیره و اعمال نهایی تمام تنظیمات فوق‌پیشرفته آونیکس",
        "manual_term_title": "🚀 پایانه معاملات دستی (Manual Trade Terminal)",
        "manual_term_sub": "ثبت مستقیم و آنی پوزیشن‌های شخصی شما روی صرافی یا متاتریدر ۵ کارگزاری",
        "btn_buy": "🚀 خرید دستی (BUY)",
        "btn_sell": "🚨 فروش دستی (SELL)",
        "btn_close_trade": "❌ بستن فوری و دستی معامله (Emergency Close)",
        "disclaimer_title": "⚠️ بیانیه قوانین و سلب مسئولیت حقوقی (Terms of Service & Disclaimer)",
        "disclaimer_body": "فعالیت در بازارهای مالی بین‌المللی اعم از فارکس، طلا، جفت‌ارزها و ارزهای دیجیتال دارای ریسک بسیار بالایی است و ممکن است منجر به از دست رفتن بخشی یا تمام سرمایه شما شود. پلتفرم معاملاتی آونیکس (Avenix) یک نرم‌افزار تحلیلی، الگوریتمی و محاسباتی ریاضی است. تمامی سیگنال‌ها، تاییده‌ها، گزارش‌های بروشوری و تحلیل‌های صادر شده در این نرم‌افزار، صرفاً جهت پیشنهاد تحلیل بازار و اهداف آموزشی شبیه‌سازی شده‌اند و به هیچ عنوان توصیه سرمایه‌گذاری، سیگنال خرید یا فروش قطعی یا مشاوره‌ی مالی به حساب نمی‌آیند. مالک، طراح و توسعه‌دهندگان این نرم‌افزار هیچ‌گونه مسئولیت حقوقی، مالی یا قانونی در قبال سودها، زیان‌ها، دروداون‌ها، افت سرمایه، مسدود شدن حساب‌های پروپ‌فرم یا هرگونه خسارت ناشی از استفاده از این برنامه در بازار واقعی و دمو ندارند. استفاده شما از این نرم‌افزار به معنای پذیرش کامل و بدون قید و شرط این قوانین سلب مسئولیت است.",
        "sl_ratio": "حد ضرر اولیه درصد (SL Ratio) %",
        "btn_accept_terms": "✅ قوانین و سلب مسئولیت را به طور کامل خواندم و می‌پذیرم و قصد ورود دارم",
        "locked_terms_desc": "🔒 لطفا برای دسترسی به چارت زنده و مغز هوشمند سیستم، ابتدا بیانیه سلب مسئولیت زیر را تأیید کنید:"
    },
    "en": {
        "title": "🦅 AVENIX SMART TRADING SUITE",
        "sub": "Algorithmic Trading & Automated Risk Management for Forex, Metals, & Crypto",
        "tab_chart": "📊 Live Chart",
        "tab_brain": "🧠 AI Brain",
        "tab_signals": "📢 Signals",
        "tab_broker": "🔌 Broker Connect",
        "tab_contest": "🏆 FundedNext Portal",
        "tab_settings": "⚙️ System Config",
        "tab_history": "📜 Account History",
        "selector_symbol": "Select Asset for Live Analysis",
        "selector_tf": "Chart Timeframe",
        "tv_caption": "🌐 <b>TradingView Terminal:</b> This chart is fully interactive. You can scroll back, add drawing tools, and customize indicators natively.",
        "brain_telemetry": "🧠 Robot Telemetry & Indicator Status",
        "brain_sub": "Live scoring and isolated status configurations for each technical indicator",
        "force_scan_desc": "The robot scans the market every 10 seconds. You can trigger an instant scan below:",
        "force_scan_btn": "🔥 Trigger Instant AI Brain Scan",
        "isolated_checklist": "📊 Isolated Indicator Confirmations",
        "brain_score_title": "Consolidated Convergence Score (Brain Score)",
        "score_threshold_desc": "Threshold Limit",
        "checklist_title": "Individual indicator readings in the last scan:",
        "pnl_report": "💼 Live Positions & Orders Telemetry",
        "balance_title": "Demo Wallet Equity (Balance)",
        "active_trades_title": "Active Positions",
        "broker_badge_title": "Connected Execution Bridge",
        "paper_badge": "Simulated Demo (Paper)",
        "real_badge": "Live Broker Server",
        "active_pnl": "Floating Profit",
        "entry_price": "Entry Price",
        "live_price": "Live Price",
        "current_sl": "Current Stop Loss",
        "original_sl": "Original Stop Loss",
        "targets": "Take Profit Targets",
        "trailing_step": "Trailing Step",
        "completed_history": "✅ Completed Trades History",
        "exit_reason": "Closed by",
        "exit_time": "Exit Time",
        "pnl_result": "Resulting PnL",
        "no_active_trades": "There are currently no active trades.",
        "no_completed_trades": "Completed trade history is empty.",
        "settings_title": "⚙️ Advanced Indicator & System Config",
        "ind_custom": "📊 Individual Indicator Setups",
        "emas_title": "1. Exponential Moving Averages (EMAs)",
        "fast_ema": "Fast EMA Period",
        "medium_ema": "Medium EMA Period",
        "long_ema": "Long EMA Trend Filter",
        "ich_title": "2. Ichimoku Kinko Hyo",
        "tenkan_val": "Tenkan-sen (Conversion) Period",
        "kijun_val": "Kijun-sen (Base) Period",
        "span_b_val": "Senkou Span B Period",
        "rsi_title": "3. Relative Strength Index (RSI)",
        "rsi_period": "RSI Period",
        "rsi_os": "Oversold Boundary",
        "rsi_ob": "Overbought Boundary",
        "macd_title": "4. MACD Configuration",
        "macd_fast": "MACD Fast EMA",
        "macd_slow": "MACD Slow EMA",
        "macd_signal": "MACD Signal Line",
        "bb_title": "5. Bollinger Bands",
        "bb_period": "Bollinger Period",
        "bb_std": "Standard Deviation (Std Dev)",
        "risk_title": "🛡️ Risk Sizing, Target Profits, & Broker Bridge",
        "risk_pct": "Account Risk Percentage (%)",
        "leverage": "Margin Leverage Factor",
        "score_thresh": "Consolidated Score Entrance Threshold %",
        "broker_connect_title": "Connected Account Connection Setup (Real/Demo)",
        "mt5_desc": "🔌 Connect to Forex Broker (LiteFinance, Alpari) or Prop-Firm account challenge (FundedNext):",
        "prop_guard_title": "🛡️ Drawdown Protection Guard (Avenix Prop Guard)",
        "prop_limit_desc": "Maximum Daily Allowed Account Loss %",
        "prop_locked_err": "🚨 Daily Drawdown limit breached! Trading is locked for today.",
        "prop_unlock_btn": "🔓 Reset Daily Drawdown Lock",
        "prop_safe": "🟢 Daily drawdown guard is active. Account margins are highly secure.",
        "tp_reward": "🎯 Trailing Profit Ratios (Risk-to-Reward)",
        "social_broadcast_title": "### Social Broadcast Management",
        "social_broadcast_sub": "Broadcast analytical brochure signal reports simultaneously across social platforms",
        "tg_title": "1. Telegram Messenger API",
        "tg_enable": "Enable Telegram Broadcast",
        "tg_token": "Telegram Bot Token",
        "tg_chat": "Telegram Chat / Channel ID",
        "bale_title": "2. Bale Messenger API (Iranian)",
        "bale_enable": "Enable Bale Broadcast",
        "bale_token": "Bale Bot Token",
        "bale_chat": "Bale Sohbet / Channel ID",
        "wa_title": "3. WhatsApp API Gateway",
        "wa_enable": "Enable WhatsApp Broadcast",
        "wa_inst": "WhatsApp Instance ID",
        "wa_token": "WhatsApp Token",
        "wa_phone": "Target Phone Number",
        "symbols_under_watch": "Symbols Under Watch (Comma separated)",
        "main_tf_scan": "Main Scan Timeframe",
        "reset_wallet_btn": "🔄 Reset Demo Portfolio",
        "save_settings_btn": "💾 Save & Apply All Configs",
        "manual_term_title": "🚀 Manual Trade Terminal",
        "manual_term_sub": "Submit manual positions.",
        "btn_buy": "🚀 Place Manual BUY",
        "btn_sell": "🚨 Place Manual SELL",
        "btn_close_trade": "Manual Emergency Close Trade",
        "disclaimer_title": "⚠️ Legal Disclaimer & Terms of Service",
        "disclaimer_body": "Trading involves high risk. Avenix is an analytical software for educational simulation purposes only.",
        "sl_ratio": "Initial Stop Loss Ratio %",
        "btn_accept_terms": "✅ I fully read and accept the Terms of Service & Disclaimer",
        "locked_terms_desc": "🔒 Please accept the Legal Disclaimer first to unlock Avenix Charts:"
    }
}

t = TXT[lang_code]

with lang_col1:
    st.markdown(f"<h1 style='color: #3b82f6; font-size: 24px; font-weight: 700; margin-top: 5px;'>{t['title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #64748b; font-size: 13px;'>{t['sub']}</p>", unsafe_allow_html=True)

# Initialize execution engine
executor = OrderExecutionEngine()

# ----------------- ⚠️ WELCOME LEGAL GATE (قفل پذیرش قوانین سلب مسئولیت) -----------------
if not st.session_state.terms_accepted:
    st.markdown(f"### {t['disclaimer_title']}")
    st.markdown(f"<p style='color: #f87171; font-weight: 500; font-size: 14px;'>{t['locked_terms_desc']}</p>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class='ios-card' style='border-right: 5px solid #ef4444; max-height: 380px; overflow-y: auto;'>
        <p class='disclaimer-text'>{t['disclaimer_body']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Checkbox to Accept Terms
    if st.button(t["btn_accept_terms"], use_container_width=True):
        st.session_state.terms_accepted = True
        st.success("🎉 Welcome to Avenix!")
        time.sleep(1)
        st.rerun()

else:
    # ----------------- 🟢 LIVE FLOATING PNL HUD BANNER -----------------
    active_trades = portfolio.get("active_trades", [])
    total_floating_pnl = 0.0
    total_pnl_percent = 0.0
    
    if len(active_trades) > 0:
        for trade in active_trades:
            total_floating_pnl += trade.get("pnl", 0.0)
            total_pnl_percent += trade.get("pnl_percent", 0.0)
            
        hud_bg = "rgba(16, 185, 129, 0.15)" if total_floating_pnl >= 0 else "rgba(239, 68, 68, 0.15)"
        hud_border = "#10b981" if total_floating_pnl >= 0 else "#ef4444"
        hud_text_color = "#10b981" if total_floating_pnl >= 0 else "#ef4444"
        sign = "+" if total_floating_pnl >= 0 else ""
        
        hud_msg_fa = f"🟢 سود زنده در جریان کل معاملات: {sign}${total_floating_pnl:,.2f} ({sign}{total_pnl_percent:.2f}%)" if total_floating_pnl >= 0 else f"🔴 زیان زنده در جریان کل معاملات: ${total_floating_pnl:,.2f} ({total_pnl_percent:.2f}%)"
        hud_msg_en = f"🟢 LIVE FLOATING PROFIT: {sign}${total_floating_pnl:,.2f} ({sign}{total_pnl_percent:.2f}%)" if total_floating_pnl >= 0 else f"🔴 LIVE FLOATING LOSS: ${total_floating_pnl:,.2f} ({total_pnl_percent:.2f}%)"
        hud_display = hud_msg_fa if lang_code == "fa" else hud_msg_en
        
        st.markdown(f"""
        <div class='hud-banner' style='background-color: {hud_bg}; border: 1px solid {hud_border}; color: {hud_text_color};'>
            {hud_display}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='hud-banner' style='background-color: rgba(148, 163, 184, 0.08); border: 1px solid #475569; color: #94a3b8;'>
            ⚪ { "هیچ معامله فعال تکنیکالی در جریان نیست" if lang_code == "fa" else "NO ACTIVE POSITION IN TARGETS" }
        </div>
        """, unsafe_allow_html=True)

    # ----------------- 🌐 WEEKEND AUTO-CRYPTO PIVOT BANNER -----------------
    if is_forex_market_closed():
        weekend_msg_fa = """
        <div class='hud-banner' style='background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(217, 119, 6, 0.15) 100%); border: 1px solid #f59e0b; color: #fbbf24; margin-bottom: 20px; border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);'>
            <div style='display: flex; align-items: center; gap: 10px;'>
                <span style='font-size: 24px;'>🌐</span>
                <div style='flex: 1; text-align: right; direction: rtl;'>
                    <strong style='font-size: 15px;'>حالت هوشمند آخر هفته فعال است (Weekend Focus Active)</strong><br/>
                    <span style='font-size: 13px; opacity: 0.9;'>بازارهای جهانی فارکس، طلا و نفت در تعطیلات پایان هفته هستند. ربات به‌صورت خودکار و هوشمند روی <b>بازار ارزهای دیجیتال (Crypto 24/7)</b> متمرکز شده است تا از هرگونه سردرگمی، رکود نمودارها و سیگنال‌های اشتباه جلوگیری شود. معاملات و نمودارهای فعال شما هم‌اکنون به رمزارزها اختصاص دارند.</span>
                </div>
            </div>
        </div>
        """
        weekend_msg_en = """
        <div class='hud-banner' style='background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(217, 119, 6, 0.15) 100%); border: 1px solid #f59e0b; color: #fbbf24; margin-bottom: 20px; border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);'>
            <div style='display: flex; align-items: center; gap: 10px;'>
                <span style='font-size: 24px;'>🌐</span>
                <div style='flex: 1; text-align: left; direction: ltr;'>
                    <strong style='font-size: 15px;'>Intelligent Weekend Mode Active</strong><br/>
                    <span style='font-size: 13px; opacity: 0.9;'>Global Forex, Gold, and Oil markets are currently closed. Avenix Pro Gold has automatically pivoted all scanning and charting focus to the <b>24/7 Cryptocurrency Market (BTC, ETH, SOL)</b> to prevent chart freezes, stale prices, and confusion. Enjoy uninterrupted trading!</span>
                </div>
            </div>
        </div>
        """
        weekend_display = weekend_msg_fa if lang_code == "fa" else weekend_msg_en
        st.markdown(weekend_display, unsafe_allow_html=True)

    # ----------------- ACTIVE MAIN TABS (7-Tab Layout: Completely Separated!) -----------------
    tab_chart_view, tab_brain_view, tab_signals_view, tab_broker_view, tab_contest_view, tab_settings_view, tab_history_view = st.tabs([
        t["tab_chart"], t["tab_brain"], t["tab_signals"], t["tab_broker"], t["tab_contest"], t["tab_settings"], t["tab_history"]
    ])

    # ----------------- TAB 1: TRADINGVIEW LIVE CHART & INSTANT TRADING PANEL -----------------
    with tab_chart_view:
        sel_col1, sel_col2 = st.columns([1, 1])
        with sel_col1:
            raw_symbols = config.get("symbols", ["XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "BRENT/USD", "SOL/USDT"])
            selected_symbol = st.selectbox(t["selector_symbol"], raw_symbols, index=0, key="chart_sym")
        with sel_col2:
            selected_timeframe = st.selectbox(t["selector_tf"], ["1", "5", "15", "60", "240", "D"], index=2, key="chart_tf")

        # Pull current price to compute SL/TP automatically in 1-click
        current_market_price = 2420.0
        if "XAU" in selected_symbol:
            current_market_price = 2420.0
        elif "XAG" in selected_symbol:
            current_market_price = 29.0
        elif "EUR" in selected_symbol:
            current_market_price = 1.0850
        elif "BRENT" in selected_symbol:
            current_market_price = 82.50
        elif "BTC" in selected_symbol:
            current_market_price = 65000.0

        # --- ⚡ HIGH-SPEED QUICK TRADING PANEL PLACED CONVENIENTLY ABOVE CHART ---
        st.markdown("<p style='font-weight: 700; color: #f8fafc; margin-top: 15px;'>⚡ پنل ترید فوق‌سریع آونیکس (Avenix One-Click Fast Execution):</p>", unsafe_allow_html=True)
        
        col_exec_sell, col_exec_lot, col_exec_buy = st.columns([1.5, 1, 1.5])
        with col_exec_lot:
            default_lot_val = 2.0 if config.get("contest_mode", False) else 1.0
            lot_size_input = st.number_input("Lot / حجم معامله", min_value=0.01, max_value=50.0, value=default_lot_val, step=0.1, label_visibility="collapsed")
            
        with col_exec_buy:
            if st.button("🚀 BUY (LONG) | خرید فوری", use_container_width=True):
                if is_forex_market_closed() and not is_crypto_symbol(selected_symbol):
                    st.error(f"❌ امکان خرید وجود ندارد! بازار نماد {selected_symbol} در حال حاضر به دلیل تعطیلات آخر هفته بسته است. لطفاً روی رمزارزهای فعال معامله کنید.")
                else:
                    with st.spinner("Executing BUY..."):
                        sl_dist = current_market_price * (config.get("sl_ratio", 1.5) / 100)
                        quick_sl = current_market_price - sl_dist
                        quick_tp1 = current_market_price + (sl_dist * config.get("tp1_ratio", 1.0))
                        quick_tp2 = current_market_price + (sl_dist * config.get("tp2_ratio", 2.0))
                        quick_tp3 = current_market_price + (sl_dist * config.get("tp3_ratio", 3.0))
                        
                        config["contest_fixed_lot_size"] = lot_size_input
                        save_config(config)
                        
                        res = executor.open_trade(selected_symbol, "BUY", current_market_price, quick_sl, quick_tp1, quick_tp2, quick_tp3, "ثبت خرید فوق‌سریع دستی", is_manual=True)
                        if res.get("status") == "success":
                            notify_manual_open(selected_symbol, "BUY", current_market_price, quick_sl, quick_tp1, quick_tp2, quick_tp3, lot_size_input)
                            st.success("Instant BUY order opened successfully on MT5!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(res.get("reason"))
                        
        with col_exec_sell:
            if st.button("🚨 SELL (SHORT) | فروش فوری", use_container_width=True):
                if is_forex_market_closed() and not is_crypto_symbol(selected_symbol):
                    st.error(f"❌ امکان فروش وجود ندارد! بازار نماد {selected_symbol} در حال حاضر به دلیل تعطیلات آخر هفته بسته است. لطفاً روی رمزارزهای فعال معامله کنید.")
                else:
                    with st.spinner("Executing SELL..."):
                        sl_dist = current_market_price * (config.get("sl_ratio", 1.5) / 100)
                        quick_sl = current_market_price + sl_dist
                        quick_tp1 = current_market_price - (sl_dist * config.get("tp1_ratio", 1.0))
                        quick_tp2 = current_market_price - (sl_dist * config.get("tp2_ratio", 2.0))
                        quick_tp3 = current_market_price - (sl_dist * config.get("tp3_ratio", 3.0))
                        
                        config["contest_fixed_lot_size"] = lot_size_input
                        save_config(config)
                        
                        res = executor.open_trade(selected_symbol, "SELL", current_market_price, quick_sl, quick_tp1, quick_tp2, quick_tp3, "ثبت فروش فوق‌سریع دستی", is_manual=True)
                        if res.get("status") == "success":
                            notify_manual_open(selected_symbol, "SELL", current_market_price, quick_sl, quick_tp1, quick_tp2, quick_tp3, lot_size_input)
                            st.success("Instant SELL order opened successfully on MT5!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(res.get("reason"))

        # --- 🔔 ACTIVE ORDER LINES INFORMATION BANNER ---
        active_trades = portfolio.get("active_trades", [])
        symbol_trades = [tr for tr in active_trades if tr["symbol"] == selected_symbol]
        if symbol_trades:
            st.markdown("<p style='font-weight: 700; color: #fbbf24; font-size: 14px; margin-top: 15px;'>🛡️ شبیه‌ساز تصویری خطوط سفارش فعال آونیکس (MT5 Style Order Lines):</p>", unsafe_allow_html=True)
            for tr in symbol_trades:
                entry = tr["entry_price"]
                sl = tr["sl"]
                tp = tr["tp1"]
                side = tr["side"]
                qty = tr.get("qty", 1.0)
                
                # Calculate live PnL for this specific trade
                side_mult = 1 if side == "BUY" else -1
                pnl_cash = qty * (current_market_price - entry) * side_mult
                pnl_color = "#10b981" if pnl_cash >= 0 else "#ef4444"
                sign = "+" if pnl_cash >= 0 else ""
                
                st.markdown(f"""
                <div style='background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 15px; margin-bottom: 15px;'>
                    <div style='display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 13px;'>
                        <span style='color: #cbd5e1; font-weight: bold;'>📊 پوزیشن زنده {side} در {tr['symbol']}</span>
                        <span style='color: {pnl_color}; font-weight: 700;'>سود/زیان زنده: {sign}${pnl_cash:,.2f}</span>
                    </div>
                    <!-- TP Line -->
                    <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 8px;'>
                        <span style='color: #10b981; font-weight: bold; width: 80px; font-size: 12px;'>🟢 TP:</span>
                        <div style='flex: 1; border-bottom: 2px dotted #10b981; opacity: 0.6;'></div>
                        <span style='color: #10b981; font-weight: bold; font-size: 13px;'>${tp:,.2f}</span>
                    </div>
                    <!-- Entry Line -->
                    <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 8px;'>
                        <span style='color: #3b82f6; font-weight: bold; width: 80px; font-size: 12px;'>🔵 {side}:</span>
                        <div style='flex: 1; border-bottom: 2px dotted #3b82f6; opacity: 0.6;'></div>
                        <span style='color: #3b82f6; font-weight: bold; font-size: 13px;'>${entry:,.2f} (حجم: {qty:.2f})</span>
                    </div>
                    <!-- SL Line -->
                    <div style='display: flex; align-items: center; gap: 10px;'>
                        <span style='color: #f97316; font-weight: bold; width: 80px; font-size: 12px;'>🟠 SL:</span>
                        <div style='flex: 1; border-bottom: 2px dotted #f97316; opacity: 0.6;'></div>
                        <span style='color: #f97316; font-weight: bold; font-size: 13px;'>${sl:,.2f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Map all 20 prestigious assets to TV institutional feeds
        symbol_mapping = {
            "XAU/USD": "OANDA:XAUUSD",
            "XAG/USD": "OANDA:XAGUSD",
            "PLATINUM/USD": "OANDA:XPTUSD",
            "PALLADIUM/USD": "OANDA:XPDUSD",
            "EUR/USD": "FX:EURUSD",
            "GBP/USD": "FX:GBPUSD",
            "USD/JPY": "FX:USDJPY",
            "AUD/USD": "FX:AUDUSD",
            "USD/CAD": "FX:USDCAD",
            "USD/CHF": "FX:USDCHF",
            "NZD/USD": "FX:NZDUSD",
            "BRENT/USD": "TVC:UKOIL",
            "BTC/USDT": "BINANCE:BTCUSDT",
            "ETH/USDT": "BINANCE:ETHUSDT",
            "BNB/USDT": "BINANCE:BNBUSDT",
            "SOL/USDT": "BINANCE:SOLUSDT",
            "DOGE/USDT": "BINANCE:DOGEUSDT",
            "XRP/USDT": "BINANCE:XRPUSDT",
            "ADA/USDT": "BINANCE:ADAUSDT",
            "TON/USDT": "BINANCE:TONUSDT"
        }
        
        tv_symbol = symbol_mapping.get(selected_symbol, "OANDA:XAUUSD")

        # TradingView HTML5 terminal with live candle countdown timer!
        tradingview_html = f"""
        <div class="tradingview-widget-container" style="height:100%;width:100%;background-color:#0f172a;">
          <div id="tradingview_chart" style="height:620px;width:100%;"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget(
          {{
            "autosize": true,
            "symbol": "{tv_symbol}",
            "interval": "{selected_timeframe}",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "enable_publishing": false,
            "hide_side_toolbar": false,
            "allow_symbol_change": true,
            "details": true,
            "hotlist": true,
            "calendar": true,
            "countdown": true,
            "container_id": "tradingview_chart"
          }}
          );
          </script>
        </div>
        """
        st.markdown(f"<p style='color: #94a3b8; font-size: 13px;'>{t['tv_caption']}</p>", unsafe_allow_html=True)
        components.html(tradingview_html, height=630)

    # ----------------- TAB 2: THE AI TRADING BRAIN ROOM -----------------
    with tab_brain_view:
        st.markdown(f"### {t['brain_telemetry']}")
        st.markdown(f"<p style='color: #94a3b8; font-size: 13px;'>{t['brain_sub']}</p>", unsafe_allow_html=True)
        
        col_cmd1, col_cmd2 = st.columns([3, 1])
        with col_cmd1:
            st.info(t["force_scan_desc"])
        with col_cmd2:
            if st.button(t["force_scan_btn"], use_container_width=True):
                with st.spinner("Analyzing..."):
                    bot_runner = RealTimeTradingBot()
                    bot_runner.run_one_cycle()
                    st.success("Analysis complete!")
                    st.rerun()

        col_intel, col_trades = st.columns([1, 1])
        
        with col_intel:
            st.markdown(f"#### {t['isolated_checklist']}")
            
            latest_sig = signals[-1] if len(signals) > 0 else {}
            confirmations = latest_sig.get("confirmations", {
                "EMA 200": "BULLISH 🟢",
                "EMA 20/50": "BULLISH 🟢",
                "Ichimoku Cloud": "BULLISH 🟢",
                "Ichimoku TK Cross": "BULLISH 🟢",
                "RSI": "BULLISH 🟢",
                "MACD": "BULLISH 🟢",
                "Bollinger Bands": "NEUTRAL 🟡"
            })
            
            score = latest_sig.get("brain_score", 85)
            score_color = "#10b981" if score >= config.get("brain_score_threshold", 70) else "#ef4444"
            
            st.markdown(f"""
            <div class='ios-card'>
                <div class='metric-title'>{t['brain_score_title']}</div>
                <div style='display: flex; align-items: center; justify-content: space-between; margin-top: 8px;'>
                    <span style='font-size: 28px; font-weight: 700; color: {score_color};'>{score}٪</span>
                    <span style='font-size: 13px; color: #94a3b8;'>{t['score_threshold_desc']}: {config.get("brain_score_threshold", 70)}٪</span>
                </div>
                <div style='background-color: #334155; border-radius: 10px; height: 10px; width: 100%; margin-top: 10px;'>
                    <div style='background-color: {score_color}; border-radius: 10px; height: 10px; width: {score}%;'></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-weight: 700; color: #f8fafc; margin-bottom: 12px;'>{t['checklist_title']}</p>", unsafe_allow_html=True)
            for name, status in confirmations.items():
                st.markdown(f"""
                <div class='checklist-item'>
                    <span style='color: #cbd5e1;'>{name}</span>
                    <span style='font-weight: 500;'>{status}</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_trades:
            st.markdown(f"#### {t['pnl_report']}")
            
            current_balance = portfolio.get("balance", 10000.0)
            st.markdown(f"""
            <div class='ios-card'>
                <div class='metric-title'>{t['balance_title']}</div>
                <div class='metric-value'>${current_balance:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

            # Show active trades with Emergency Close buttons
            if len(active_trades) == 0:
                st.info(t["no_active_trades"])
            else:
                for trade in active_trades:
                    color_t = "#10b981" if trade["side"] == "BUY" else "#ef4444"
                    
                    st.markdown(f"""
                    <div class='ios-card'>
                        <div style='display: flex; justify-content: space-between;'>
                            <b>{trade['symbol']} ({trade['side']})</b>
                            <span style='color: {color_t}; font-weight: 700;'>{t['active_pnl']}: ${trade['pnl']} ({trade['pnl_percent']}%)</span>
                        </div>
                        <div style='margin-top: 10px; font-size: 13px; color: #cbd5e1; margin-bottom: 12px;'>
                            {t['entry_price']}: {trade['entry_price']} | {t['live_price']}: {trade['current_price']}<br>
                            {t['current_sl']}: <b style='color: #f87171;'>{trade['sl']}</b> | {t['targets']}: TP1: {trade['tp1']} | TP2: {trade['tp2']} | TP3: {trade['tp3']}<br>
                            {t['trailing_step']}: <b>{trade.get('highest_tp_reached', 0)}</b> of 3
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Manual emergency position close button!
                    if st.button(f"{t['btn_close_trade']} ({trade['symbol']})", key=f"close_{trade['id']}"):
                        with st.spinner("Closing..."):
                            closed_pos = executor.close_trade_manually(trade["id"], trade["current_price"])
                            if closed_pos:
                                notify_manual_close(closed_pos)
                                st.success(f"Position Closed manually at {closed_pos['close_price']}!")
                                time.sleep(1)
                                st.rerun()

            if latest_sig:
                st.markdown(f"<p style='font-weight: 700; color: #f8fafc; margin-top: 15px;'>📄 Analysis Brochure:</p>", unsafe_allow_html=True)
                st.markdown(f"""
                <div class='brochure-card'>
                    {latest_sig['reason']}
                </div>
                """, unsafe_allow_html=True)

    # ----------------- TAB 3: SIGNALS ROOM ARCHIVE & MANUAL TERMINAL -----------------
    with tab_signals_view:
        st.markdown(f"### {t['manual_term_title']}")
        st.markdown(f"<p style='color: #94a3b8; font-size: 13px;'>{t['manual_term_sub']}</p>", unsafe_allow_html=True)
        
        with st.expander("💼 " + t["manual_term_title"]):
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                m_raw_symbols = config.get("symbols", ["XAU/USD"])
                m_sym = st.selectbox("نماد معامله", m_raw_symbols, key="m_sym")
                m_price = st.number_input("قیمت ورود فعلی بازار", value=2420.0, step=0.1, key="m_price")
            with m_col2:
                m_side = st.selectbox("جهت معامله", ["BUY", "SELL"], key="m_side")
                m_sl = st.number_input("حد ضرر (Stop Loss)", value=2410.0, step=0.1, key="m_sl")
            with m_col3:
                m_tp1 = st.number_input("حد سود اول (TP1)", value=2430.0, step=0.1, key="m_tp1")
                m_tp2 = st.number_input("حد سود دوم (TP2)", value=2440.0, step=0.1, key="m_tp2")
                m_tp3 = st.number_input("حد سود سوم (TP3)", value=2450.0, step=0.1, key="m_tp3")
                
            m_btn_label = t["btn_buy"] if m_side == "BUY" else t["btn_sell"]
            if st.button(m_btn_label, use_container_width=True):
                if is_forex_market_closed() and not is_crypto_symbol(m_sym):
                    st.error(f"❌ امکان ثبت معامله روی {m_sym} وجود ندارد. بازار فارکس/طلا در تعطیلات پایان هفته است. لطفاً روی نمادهای کریپتو معامله ثبت کنید.")
                else:
                    with st.spinner("Submitting Order..."):
                        res = executor.open_trade(m_sym, m_side, m_price, m_sl, m_tp1, m_tp2, m_tp3, "معامله دستی کاربر", is_manual=True)
                        if res.get("status") == "success":
                            st.success("Manual Position established successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(res.get("reason", "Order failed"))

        st.markdown("---")
        st.markdown(f"### {t['tab_signals']}")
        signals_list = load_signals()
        
        if len(signals_list) == 0:
            st.info("No signals found.")
        else:
            for sig in reversed(signals_list):
                side_badge = "🟢 BUY" if sig["side"] == "BUY" else "🔴 SELL"
                color_theme = "#10b981" if sig["side"] == "BUY" else "#ef4444"
                status_fa = "🟡 PENDING" if sig["status"] == "PENDING" else f"🔒 CLOSED ({sig['status']})"
                
                st.markdown(f"""
                <div class='ios-card' style='border-right: 5px solid {color_theme};'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <span style='font-size: 18px; font-weight: 700; color: #f8fafc;'>{sig['symbol']} (TF: {config.get('trading_timeframe','15m')})</span>
                        <span style='color: {color_theme}; font-weight: 700; font-size: 15px;'>{side_badge}</span>
                        <span style='font-size: 11px; color: #94a3b8; background-color: #334155; padding: 4px 8px; border-radius: 20px;'>{status_fa}</span>
                    </div>
                    <div style='margin-top: 15px; font-size: 13px; color: #cbd5e1; line-height: 1.6;'>
                        💵 {t['entry_price']}: <b>{sig['entry_price']}</b> | 🛡️ {t['original_sl']}: <b style='color: #f87171;'>{sig['sl']}</b><br>
                        🎯 {t['targets']}: TP1: <b>{sig.get('tp1','N/A')}</b> | TP2: <b>{sig.get('tp2','N/A')}</b> | TP3: <b>{sig.get('tp3','N/A')}</b>
                    </div>
                    <div class='brochure-card'>
                        {sig['reason']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ----------------- 🔌 TAB 4: DEDICATED BROKER CONNECT ROOM (اتاق اتصال کارگزاری - تفکیک شده!) -----------------
    with tab_broker_view:
        st.markdown(f"### {t['broker_connect_title']}")
        st.markdown(f"<p style='color: #94a3b8; font-size: 13px;'>{t['mt5_desc']}</p>", unsafe_allow_html=True)
        
        st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
        current_b = config.get("broker_type", "paper").lower()
        b_idx = 0 if current_b == "paper" else (1 if current_b == "crypto" else 2)
        
        broker_opt = st.selectbox(
            t["broker_connect_title"],
            ["شبیه‌ساز تستی (Paper Trading)", "صرافی کریپتو (Binance, Bybit via CCXT)", "بروکر فارکس و پروپ‌فرم‌ها (MetaTrader 5)"],
            index=b_idx,
            key="broker_connect_sel"
        )
        selected_b = "paper" if "شبیه‌ساز" in broker_opt else ("crypto" if "صرافی" in broker_opt else "forex_mt5")

        # Dynamic inputs depending on Broker type
        m_acc = config.get("mt5_account_id", "")
        m_pwd = config.get("mt5_password", "")
        m_srv = config.get("mt5_server", "Exness-MT5-Trial")
        c_api = config.get("exchange_api_key", "")
        c_sec = config.get("exchange_secret_key", "")

        if selected_b == "forex_mt5":
            m_acc = st.text_input("Account ID", value=m_acc)
            m_pwd = st.text_input("Password", type="password", value=m_pwd)
            m_srv = st.text_input("Broker Server (مثلاً FundedNext-Server یا LiteFinance-MT5-Real)", value=m_srv)
        elif selected_b == "crypto":
            c_api = st.text_input("API Key صرافی", value=c_api)
            c_sec = st.text_input("Secret Key صرافی", type="password", value=c_sec)
            
        st.markdown("---")
        if st.button("💾 ذخیره و همگام‌سازی فوری حساب کارگزاری (Save Broker Connection)", use_container_width=True):
            config["broker_type"] = selected_b
            config["mt5_account_id"] = m_acc
            config["mt5_password"] = m_pwd
            config["mt5_server"] = m_srv
            config["exchange_api_key"] = c_api
            config["exchange_secret_key"] = c_sec
            save_config(config)
            st.success("Broker Connection credentials saved & synced successfully on MT5/Exchange!")
            time.sleep(1)
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)

        # Persistent config warning and download button
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("""
        <div class='ios-card' style='border-right: 5px solid #eab308; background-color: rgba(234, 179, 8, 0.05);'>
            <strong style='color: #eab308; font-size: 14px;'>⚠️ قفل امنیتی ماندگاری مشخصات حساب (Anti-Wipe Guard)</strong><br/><br/>
            <span style='color: #cbd5e1; font-size: 13px; line-height: 1.6;'>
            به دلیل ساختار سرورهای ابری عمومی، اطلاعات حساب شما پس از مدتی بی‌کار ماندن سرور پاک شده و به حالت اولیه گیت‌هاب برمی‌گردند. 
            برای اینکه مشخصات لایت‌فایننس و توکن‌های شبکه‌های اجتماعی شما <b>برای همیشه ماندگار بمانند و هرگز پاک نشوند</b>:
            کافیست ابتدا اطلاعات را در کادرهای بالا وارد کرده و دکمه ذخیره آبی بالا را بزنید، سپس روی دکمه سبز زیر کلیک کنید تا فایل پیکربندی پایدار دانلود شود. این فایل دانلود شده را در مخزن گیت‌هاب خود آپلود (جایگزین) کنید تا برای همیشه قفل شوند!
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            with open("config.json", "r") as f:
                config_str = f.read()
        except Exception:
            config_str = "{}"
            
        st.download_button(
            label="📥 دانلود فایل پیکربندی پایدار جهت آپلود در گیت‌هاب (Download config.json)",
            data=config_str,
            file_name="config.json",
            mime="application/json",
            use_container_width=True
        )

    # ----------------- 🏆 TAB 5: DEDICATED FUNDEDNEXT PORTAL (اتاق اختصاصی فانددنکست) -----------------
    with tab_contest_view:
        st.markdown("### 🏆 اتاق پایش و کنترل هوشمند مسابقات فارکس (FundedNext Contest Terminal)")
        st.markdown("<p style='color: #94a3b8; font-size: 13px;'>کنترل لحظه‌ای تاییده‌ها، فیلترهای ضد ردیابی ربات و انطباق کامل با قوانین FundedNext</p>", unsafe_allow_html=True)
        
        # --- ⏳ DYNAMIC LIVE COUNTDOWN TIMER UNTIL NEXT MONTH'S COMPETITION ---
        now = datetime.datetime.now()
        if now.month == 12:
            target_date = datetime.datetime(now.year + 1, 1, 1, 0, 0, 0)
        else:
            target_date = datetime.datetime(now.year, now.month + 1, 1, 0, 0, 0)
            
        time_diff = target_date - now
        
        months_fa = ["ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن", "جولای", "آگوست", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"]
        months_en = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        target_month_name_fa = months_fa[target_date.month - 1]
        target_month_name_en = months_en[target_date.month - 1]
        
        if time_diff.total_seconds() > 0:
            days = time_diff.days
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            countdown_bg = "rgba(59, 130, 246, 0.12)"
            countdown_border = "#3b82f6"
            
            countdown_display = f"⏳ زمان باقی‌مانده تا شروع مسابقه {target_month_name_fa} فانددنکست: {days} روز و {hours} ساعت و {minutes} دقیقه و {seconds} ثانیه" if lang_code == "fa" else f"⏳ TIME UNTIL {target_month_name_en.upper()} COMPETITION START: {days} Days, {hours} Hours, {minutes} Mins, {seconds} Secs"
            hud_contest_title = f"مسابقه بزرگ ماه {target_month_name_fa} فانددنکست ({target_month_name_en} Competition)" if lang_code == "fa" else f"{target_month_name_en} Competition Upcoming"
            
            st.markdown(f"""
            <div class='hud-banner' style='background-color: {countdown_bg}; border: 1px solid {countdown_border}; color: #3b82f6; font-size: 16px; margin-bottom: 25px;'>
                🏆 <b>{hud_contest_title}</b><br><br>
                {countdown_display}<br><br>
                🎁 <b>جوایز مسابقه:</b> ۸,۰۰۰ دلار وجه نقد + ۶۵۰,۰۰۰ دلار اکانت‌های فوری استلار فانددنکست<br>
                👥 <b>تعداد تریدرهای ثبت‌نام شده در این لحظه:</b> ۶۰,۹۶۳ شرکت‌کننده در سراسر جهان
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='hud-banner' style='background-color: rgba(16, 185, 129, 0.12); border: 1px solid #10b981; color: #10b981; font-size: 16px; margin-bottom: 25px;'>
                🏆 <b>{ "مسابقه بزرگ فانددنکست آغاز شد!" if lang_code == "fa" else "The Competition is LIVE Now!" }</b>
            </div>
            """, unsafe_allow_html=True)

        # Display 4 Shield Telemetry metrics
        col_rule1, col_rule2, col_rule3, col_rule4 = st.columns(4)
        
        with col_rule1:
            is_mt5_active = config.get("broker_type") == "forex_mt5"
            shield_color = "#10b981" if is_mt5_active else "#94a3b8"
            shield_text = "🟢 فعال (عبور سفارش با هویت انسان)" if is_mt5_active else "⚪ غیرفعال"
            st.markdown(f"""
            <div class='ios-card' style='border-left: 4px solid {shield_color};'>
                <div class='metric-title'>🛡️ سپر ضد ردیابی ربات (Anti-EA)</div>
                <div style='font-size: 16px; font-weight: 700; color: {shield_color}; margin-top: 8px;'>{shield_text}</div>
                <p style='font-size: 11px; color: #94a3b8; margin-top: 4px; line-height: 1.4;'>حذف خودکار کد جادویی (magic: 0) و کامنت‌ها جهت دور زدن ربات‌یاب FundedNext</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_rule2:
            open_count = len(portfolio.get("active_trades", []))
            pos_color = "#10b981" if open_count < 4 else ("#eab308" if open_count == 4 else "#ef4444")
            st.markdown(f"""
            <div class='ios-card' style='border-left: 4px solid {pos_color};'>
                <div class='metric-title'>📊 سقف موقعیت‌های باز همزمان</div>
                <div style='font-size: 20px; font-weight: 700; color: {pos_color}; margin-top: 8px;'>{open_count} از ۵ پوزیشن</div>
                <div style='background-color: #334155; border-radius: 10px; height: 6px; width: 100%; margin-top: 10px;'>
                    <div style='background-color: {pos_color}; border-radius: 10px; height: 6px; width: {open_count * 20}%;'></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_rule3:
            daily_count = portfolio.get("daily_trades_count", 0)
            trade_color = "#10b981" if daily_count < 35 else ("#eab308" if daily_count < 45 else "#ef4444")
            st.markdown(f"""
            <div class='ios-card' style='border-left: 4px solid {trade_color};'>
                <div class='metric-title'>⏰ حد تعداد تریدهای روزانه</div>
                <div style='font-size: 20px; font-weight: 700; color: {trade_color}; margin-top: 8px;'>{daily_count} از ۴۵ معامله</div>
                <div style='background-color: #334155; border-radius: 10px; height: 6px; width: 100%; margin-top: 10px;'>
                    <div style='background-color: {trade_color}; border-radius: 10px; height: 6px; width: {daily_count * 2}%;'></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_rule4:
            c_mode_active = config.get("contest_mode", False)
            mode_color = "#10b981" if c_mode_active else "#94a3b8"
            mode_label = "🟢 فعال (حالت تهاجمی)" if c_mode_active else "⚪ غیرفعال"
            st.markdown(f"""
            <div class='ios-card' style='border-left: 4px solid {mode_color};'>
                <div class='metric-title'>🏆 وضعیت حالت مسابقه (Contest)</div>
                <div style='font-size: 16px; font-weight: 700; color: {mode_color}; margin-top: 8px;'>{mode_label}</div>
                <p style='font-size: 11px; color: #94a3b8; margin-top: 4px; line-height: 1.4;'>ترید تهاجمی با لات ثابت {config.get('contest_fixed_lot_size', 2.0)} و اهداف حد سود سود بالا</p>
            </div>
            """, unsafe_allow_html=True)

        # Drawdown protections and MT5 terminal sync visual cards
        col_status1, col_status2 = st.columns([1, 1])
        
        with col_status1:
            st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
            st.markdown("<p style='font-weight: 700; color: #f87171; margin-bottom: 12px;'>🛡️ وضعیت سپرهای محافظ ضد افت حساب (Drawdown Guards):</p>", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='checklist-item'>
                <span>سقف دروداون روزانه مجاز (حاشیه امنیت فانددنکست):</span>
                <span style='font-weight: 700; color: #f87171;'>{config.get("prop_drawdown_limit", 4.5)}٪ (۵٪ حداکثر)</span>
            </div>
            <div class='checklist-item'>
                <span>سقف دروداون کل حساب (حاشیه امنیت مسابقه):</span>
                <span style='font-weight: 700; color: #f87171;'>{config.get("prop_overall_drawdown_limit", 9.0)}٪ (۱۰٪ حداکثر)</span>
            </div>
            <div class='checklist-item'>
                <span>قفل ترید خودکار اضطراری در روز جاری:</span>
                <span>{"🚨 مسدود شده (فعال)" if config.get("prop_drawdown_breached") else "🟢 باز و ایمن (آماده معامله)"}</span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_status2:
            st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
            st.markdown("<p style='font-weight: 700; color: #3b82f6; margin-bottom: 12px;'>📊 انطباق و همگام‌سازی تریدها با MetaTrader 5:</p>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class='checklist-item'>
                <span>شماره حساب کارگزار:</span>
                <span>{config.get("mt5_account_id", "N/A")}</span>
            </div>
            <div class='checklist-item'>
                <span>سرور بروکر متصل:</span>
                <span>{config.get("mt5_server", "N/A")}</span>
            </div>
            <div class='checklist-item'>
                <span>قابلیت کپی ترید همزمان روی لپ‌تاپ:</span>
                <span style='color: #10b981; font-weight: 700;'>🟢 فعال و همگام</span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ----------------- TAB 6: SYSTEM SETTINGS -----------------
    with tab_settings_view:
        st.markdown(f"### {t['settings_title']}")
        
        # Disclaimer box (Exactly as requested!)
        with st.expander(t["disclaimer_title"]):
            st.markdown(f"<p class='disclaimer-text'>{t['disclaimer_body']}</p>", unsafe_allow_html=True)
            
        # 1. Indicator settings (Organized in Clean Expanders - "تفکیک تنظیمات سیستم"!)
        st.markdown("---")
        with st.expander("🤖 ۱. تنظیمات پیشرفته هوش اندیکاتورها (MACD, Bollinger, RSI, EMAs)"):
            col_set_ma, col_set_ich = st.columns(2)
            with col_set_ma:
                st.markdown(f"<p style='font-weight: 700; color: #3b82f6;'>{t['emas_title']}</p>", unsafe_allow_html=True)
                ma_s = st.slider(t["fast_ema"], 5, 30, config.get("ma_short", 20))
                ma_m = st.slider(t["medium_ema"], 30, 100, config.get("ma_medium", 50))
                ma_l = st.slider(t["long_ema"], 100, 300, config.get("ma_long", 200))
            with col_set_ich:
                st.markdown(f"<p style='font-weight: 700; color: #a855f7;'>{t['ich_title']}</p>", unsafe_allow_html=True)
                ich_t = st.number_input(t["tenkan_val"], min_value=5, max_value=20, value=config.get("ichimoku_tenkan", 9))
                ich_k = st.number_input(t["kijun_val"], min_value=15, max_value=40, value=config.get("ichimoku_kijun", 26))
                ich_b = st.number_input(t["span_b_val"], min_value=40, max_value=80, value=config.get("ichimoku_senkou_b", 52))

            st.markdown("---")
            col_set_rsi, col_set_macd, col_set_bb = st.columns(3)
            with col_set_rsi:
                st.markdown(f"<p style='font-weight: 700; color: #f43f5e;'>{t['rsi_title']}</p>", unsafe_allow_html=True)
                rsi_per = st.number_input(t["rsi_period"], min_value=5, max_value=30, value=config.get("rsi_period", 14))
                rsi_os = st.slider(t["rsi_os"], 10, 40, config.get("rsi_oversold", 30))
                rsi_ob = st.slider(t["rsi_ob"], 60, 90, config.get("rsi_overbought", 70))
            with col_set_macd:
                st.markdown(f"<p style='font-weight: 700; color: #10b981;'>{t['macd_title']}</p>", unsafe_allow_html=True)
                macd_f = st.number_input(t["macd_fast"], min_value=5, max_value=25, value=config.get("macd_fast", 12))
                macd_s = st.number_input(t["macd_slow"], min_value=20, max_value=40, value=config.get("macd_slow", 26))
                macd_sig = st.number_input(t["macd_signal"], min_value=5, max_value=15, value=config.get("macd_signal", 9))
            with col_set_bb:
                st.markdown(f"<p style='font-weight: 700; color: #eab308;'>{t['bb_title']}</p>", unsafe_allow_html=True)
                bb_per = st.number_input(t["bb_period"], min_value=5, max_value=40, value=config.get("bb_period", 20))
                bb_std = st.number_input(t["bb_std"], min_value=1.0, max_value=4.0, value=config.get("bb_std_dev", 2.0), step=0.1)

        # 2. Risk & Broker
        with st.expander("🛡️ ۲. تنظیمات مدیریت سرمایه, ریسک و اهداف سود پله‌ای"):
            col_set_r1, col_set_r2 = st.columns(2)
            with col_set_r1:
                r_pct = st.slider(t["risk_pct"], 0.1, 5.0, float(config.get("risk_percentage", 1.0)), 0.1)
                lev = st.number_input(t["leverage"], min_value=1, max_value=125, value=config.get("default_leverage", 1))
                sl_rat = st.slider(t["sl_ratio"], 0.5, 5.0, float(config.get("sl_ratio", 1.5)), 0.1)
                score_thresh = st.slider(t["score_thresh"], 50, 95, config.get("brain_score_threshold", 70))
            with col_set_r2:
                st.markdown(f"🎯 **{t['tp_reward']}**")
                tp1_val = st.slider("TP1 R:R", 0.5, 2.0, float(config.get("tp1_ratio", 1.0)), 0.1)
                tp2_val = st.slider("TP2 R:R", 1.5, 4.0, float(config.get("tp2_ratio", 2.0)), 0.1)
                tp3_val = st.slider("TP3 R:R", 2.5, 6.0, float(config.get("tp3_ratio", 3.0)), 0.1)

        # 5. Specialized Prop-Firm/Contest Mode (🏆 اتاق فرمول‌نویسی مسابقات و چالش‌های پروپ‌فرم)
        with st.expander("🏆 ۳. تنظیمات تهاجمی مسابقات و چالش‌های پروپ‌فرم (Contest Mode)"):
            st.info("با فعال‌سازی حالت مسابقه، ربات با تاییده‌های بسیار سریع (حساسیت بالا) و اهداف سود بسیار بزرگ کار خواهد کرد تا رتبه شما را در مسابقات FundedNext و بروکرها افزایش دهد.")
            c_mode = st.checkbox("فعال‌سازی حالت مسابقه تهاجمی (Contest Mode)", value=config.get("contest_mode", False))
            
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                use_fixed_lot = st.checkbox("استفاده از حجم لات ثابت مسابقاتی (لات ۲.۰)", value=config.get("use_fixed_lot_in_contest", True))
                c_lot = st.number_input("حجم لات ثابت مسابقاتی (مثال: ۲.۰ لات)", value=float(config.get("contest_fixed_lot_size", 2.0)), min_value=0.01, max_value=20.0, step=0.1)
            with c_col2:
                c_risk = st.number_input("یا مدیریت سرمایه شناور مسابقاتی (مثال: ۱.۵٪ کل حساب)", value=float(config.get("contest_risk_percentage", 1.5)), min_value=0.1, max_value=10.0, step=0.1)
            
            st.markdown("🎯 **تنظیم اهداف سود بزرگ مسابقاتی (Contest Take Profits R:R):**")
            cc_tp1, cc_tp2, cc_tp3 = st.columns(3)
            with cc_tp1:
                c_tp1 = st.slider("حد سود اول مسابقاتی", 0.5, 3.0, float(config.get("contest_tp1_ratio", 1.5)))
            with cc_tp2:
                c_tp2 = st.slider("حد سود دوم مسابقاتی", 1.5, 6.0, float(config.get("contest_tp2_ratio", 3.0)))
            with cc_tp3:
                c_tp3 = st.slider("حد سود سوم مسابقاتی", 2.5, 10.0, float(config.get("contest_tp3_ratio", 5.0)))

        # 4. Social Broadcast Settings
        with st.expander("✉️ ۴. اتاق مدیریت انتشار سیگنال‌ها (Bale, Telegram, WhatsApp)"):
            col_tg, col_bale, col_wa = st.columns(3)
            with col_tg:
                st.markdown(f"<p style='font-weight: 700; color: #3b82f6;'>{t['tg_title']}</p>", unsafe_allow_html=True)
                tg_enabled = st.checkbox(t["tg_enable"], value=config.get("enable_telegram", False))
                tg_tok = st.text_input(t["tg_token"], value=config.get("telegram_bot_token", ""))
                tg_chat = st.text_input(t["tg_chat"], value=config.get("telegram_chat_id", ""))
            with col_bale:
                st.markdown(f"<p style='font-weight: 700; color: #10b981;'>{t['bale_title']}</p>", unsafe_allow_html=True)
                bale_enabled = st.checkbox(t["bale_enable"], value=config.get("enable_bale", False))
                bale_tok = st.text_input(t["bale_token"], value=config.get("bale_bot_token", ""))
                bale_chat = st.text_input(t["bale_chat"], value=config.get("bale_chat_id", ""))
            with col_wa:
                st.markdown(f"<p style='font-weight: 700; color: #eab308;'>{t['wa_title']}</p>", unsafe_allow_html=True)
                wa_enabled = st.checkbox(t["wa_enable"], value=config.get("enable_whatsapp", False))
                wa_inst = st.text_input(t["wa_inst"], value=config.get("whatsapp_instance_id", "instance99999"))
                wa_tok = st.text_input(t["wa_token"], value=config.get("whatsapp_token", ""))
                wa_phone = st.text_input(t["wa_phone"], value=config.get("whatsapp_phone", ""))

            # DEDICATED SOCIAL SAVE BUTTON (Save instantly!)
            st.markdown("---")
            if st.button("💾 ذخیره فوری تنظیمات شبکه‌های اجتماعی (Bale, Telegram, WhatsApp)", use_container_width=True):
                config["enable_telegram"] = tg_enabled
                config["telegram_bot_token"] = tg_tok
                config["telegram_chat_id"] = tg_chat
                config["enable_bale"] = bale_enabled
                config["bale_bot_token"] = bale_tok
                config["bale_chat_id"] = bale_chat
                config["enable_whatsapp"] = wa_enabled
                config["whatsapp_instance_id"] = wa_inst
                config["whatsapp_token"] = wa_tok
                config["whatsapp_phone"] = wa_phone
                save_config(config)
                st.success("Social Broadcast Settings Saved successfully!")
                time.sleep(1)
                st.rerun()

        with st.expander("📊 ۵. جفت‌ارزهای فعال تحت نظر و تایم‌فریم اسکن"):
            all_available_symbols = [
                "XAU/USD", "XAG/USD", "PLATINUM/USD", "PALLADIUM/USD",
                "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "NZD/USD",
                "BRENT/USD", "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
                "ADA/USDT", "DOGE/USDT", "TON/USDT"
            ]
            default_active = config.get("active_symbols", ["XAU/USD", "XAG/USD", "EUR/USD", "GBP/USD", "USD/JPY"])
            active_symbols_list = st.multiselect(
                "🎯 انتخاب جفت‌ارزهای فعال برای اسکن و معامله خودکار ربات:",
                options=all_available_symbols,
                default=[s for s in default_active if s in all_available_symbols]
            )
            trading_tf_val = st.selectbox(t["main_tf_scan"], ["1m", "5m", "15m", "1h", "4h", "1d"], index=2)
            if is_forex_market_closed():
                st.info("💡 حالت آخر هفته فعال است. بازارهای طلا و فارکس هم‌اکنون تعطیل هستند، بنابراین پوزیشن‌های جدید فقط بر روی رمزارزهای فعال انتخاب‌شده بالا ثبت خواهند شد.")

        with st.expander("🔮 ۶. طرح پیشنهادی ارتقای استراتژیک Avenix Pro (Roadmap)"):
            st.markdown("""
            <div class='brochure-card' style='border-right: 5px solid #a855f7;'>
                <strong style='font-size: 15px; color: #a855f7;'>✨ برآیند کلی طرح ارتقا و توسعه آینده پلتفرم</strong><br/><br/>
                این سند نشان‌دهنده چشم‌انداز توسعه فنی پلتفرم معاملاتی <b>Avenix Pro Gold</b> به عنوان یک نرم‌افزار لول سازمانی (Enterprise Grade) است:<br/><br/>
                <b>۱. حد ضرر نوسان‌سنج هوشمند بر پایه ATR</b><br/>
                محاسبه خودکار و داینامیک حد ضررها بر اساس نوسانات واقعی بازار در زمان اخبار مهم طلا و فارکس.<br/><br/>
                <b>۲. سپر انجماد خودکار معاملات در زمان اخبار (News Freeze Auto-Guard)</b><br/>
                اتصال مستقیم به تقویم اقتصادی جهان و متوقف کردن اسکن ۳۰ دقیقه قبل از انتشار اخبار قرمز.<br/><br/>
                <b>۳. مکانیزم هجینگ هوشمند برای ریکاوری پوزیشن‌ها (Risk Lock-In)</b><br/>
                باز کردن پوزیشن‌های معکوس با حجم کاملاً بالانس برای منجمد کردن دروداون و نجات حساب در طوفان‌های بازار.<br/><br/>
                <b>۴. چارت زنده رشد بالانس حساب (Interactive Equity Curve)</b><br/>
                ترسیم نمودار تعاملی MyFxBook به صورت کاملاً لایو از معاملات ثبت شده تاریخی در فایل پورتفولیو.<br/><br/>
                <i>💡 تریدر گرامی، این سند برآیند استراتژیک به‌صورت دائمی در مخزن دوم شما آپلود شده است و پس از تست‌های فاز اول، تک‌تک این ماژول‌ها قابل فعال‌سازی خواهند بود!</i>
            </div>
            """, unsafe_allow_html=True)

        # Save button
        st.markdown("---")
        if st.button(t["save_settings_btn"], use_container_width=True):
            config["active_symbols"] = active_symbols_list
            config["trading_timeframe"] = trading_tf_val
            config["risk_percentage"] = r_pct
            config["default_leverage"] = lev
            config["sl_ratio"] = sl_rat
            config["tp1_ratio"] = tp1_val
            config["tp2_ratio"] = tp2_val
            config["tp3_ratio"] = tp3_val
            config["enable_telegram"] = tg_enabled
            config["telegram_bot_token"] = tg_tok
            config["telegram_chat_id"] = tg_chat
            config["enable_bale"] = bale_enabled
            config["bale_bot_token"] = bale_tok
            config["bale_chat_id"] = bale_chat
            config["enable_whatsapp"] = wa_enabled
            config["whatsapp_instance_id"] = wa_inst
            config["whatsapp_token"] = wa_tok
            config["whatsapp_phone"] = wa_phone
            config["sensitivity"] = config.get("sensitivity", "medium")
            config["broker_type"] = config.get("broker_type", "forex_mt5")
            config["mt5_account_id"] = config.get("mt5_account_id", "")
            config["mt5_password"] = config.get("mt5_password", "")
            config["mt5_server"] = config.get("mt5_server", "LiteFinance-MT5-Demo")
            config["exchange_api_key"] = config.get("exchange_api_key", "")
            config["exchange_secret_key"] = config.get("exchange_secret_key", "")
            config["ma_short"] = ma_s
            config["ma_medium"] = ma_m
            config["ma_long"] = ma_l
            config["ichimoku_tenkan"] = ich_t
            config["ichimoku_kijun"] = ich_k
            config["ichimoku_senkou_b"] = ich_b
            config["rsi_period"] = rsi_per
            config["rsi_oversold"] = rsi_os
            config["rsi_overbought"] = rsi_ob
            config["macd_fast"] = macd_f
            config["macd_slow"] = macd_s
            config["macd_signal"] = macd_sig
            config["bb_period"] = bb_per
            config["bb_std_dev"] = bb_std
            config["brain_score_threshold"] = score_thresh
            config["prop_drawdown_limit"] = config.get("prop_drawdown_limit", 4.5)
            
            # Save Contest parameters
            config["contest_mode"] = c_mode
            config["use_fixed_lot_in_contest"] = use_fixed_lot
            config["contest_fixed_lot_size"] = c_lot
            config["contest_risk_percentage"] = c_risk
            config["contest_tp1_ratio"] = c_tp1
            config["contest_tp2_ratio"] = c_tp2
            config["contest_tp3_ratio"] = c_tp3
            
            save_config(config)
            st.success("Settings Saved!")
            time.sleep(1)
            st.rerun()

    # ----------------- TAB 7: ACCOUNT-SPECIFIC TRANSACTION HISTORY -----------------
    with tab_history_view:
        active_account_id = config.get("mt5_account_id", "Demo Simulator")
        if not active_account_id:
            active_account_id = "Demo Simulator"
            
        st.markdown(f"### 📜 تاریخچه معاملات متمرکز حساب: {active_account_id}")
        st.markdown(f"<p style='color: #94a3b8; font-size: 13px;'>نمایش تاریخچه معاملات بسته شده و تایید شده منحصر به فرد حساب فعال شما</p>", unsafe_allow_html=True)
        
        # Period Filter Row
        period_col = st.radio(
            "انتخاب بازه زمانی تاریخچه معاملات:",
            ["امروز", "هفته گذشته", "ماه گذشته", "سه ماه گذشته", "کل تاریخچه"],
            horizontal=True,
            index=4
        )
        
        completed_trades = portfolio.get("completed_trades", [])
        
        # 1. Filter by unique account ID
        account_trades = [tr for tr in completed_trades if tr.get("account_id", "Demo Simulator") == active_account_id]
        
        # 2. Filter by selected period
        filtered_trades = []
        now_dt = datetime.datetime.now()
        
        for tr in account_trades:
            close_time_str = tr.get("close_time", "")
            try:
                close_dt = datetime.datetime.strptime(close_time_str, "%Y-%m-%d %H:%M:%S")
                delta_days = (now_dt - close_dt).days
                
                if period_col == "امروز" and delta_days > 0:
                    continue
                elif period_col == "هفته گذشته" and delta_days > 7:
                    continue
                elif period_col == "ماه گذشته" and delta_days > 30:
                    continue
                elif period_col == "سه ماه گذشته" and delta_days > 90:
                    continue
            except Exception:
                # Fallback for old/empty timestamps
                if period_col != "کل تاریخچه":
                    continue
                    
            filtered_trades.append(tr)
            
        if len(filtered_trades) == 0:
            st.markdown(f"""
            <div style='text-align: center; padding: 40px; color: #94a3b8;'>
                <span style='font-size: 48px;'>🗃️</span><br/><br/>
                <b>تاریخچه معامله‌ای برای این حساب در بازه انتخابی یافت نشد.</b>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Show sum total of profit for the filtered trades
            total_history_pnl = sum(tr.get("pnl", 0.0) for tr in filtered_trades)
            sum_color = "#10b981" if total_history_pnl >= 0 else "#ef4444"
            sign = "+" if total_history_pnl >= 0 else ""
            
            st.markdown(f"""
            <div class='ios-card' style='border-left: 4px solid {sum_color}; display: flex; justify-content: space-between; align-items: center;'>
                <span style='font-weight: bold; color: #cbd5e1;'>📊 خلاصه برآیند سود/زیان این بازه:</span>
                <span style='color: {sum_color}; font-weight: bold; font-size: 18px;'>{sign}${total_history_pnl:,.2f}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Render MT5 styled trade cards
            for tr in reversed(filtered_trades):
                symbol = tr.get("symbol", "N/A")
                side = tr.get("side", "BUY")
                qty = tr.get("qty", 1.0)
                entry_p = tr.get("entry_price", 0.0)
                close_p = tr.get("close_price", 0.0)
                pnl = tr.get("pnl", 0.0)
                close_time = tr.get("close_time", "N/A")
                
                side_color = "#3b82f6" if side == "BUY" else "#ef4444"
                pnl_color = "#10b981" if pnl >= 0 else "#ef4444"
                pnl_sign = "+" if pnl >= 0 else ""
                
                st.markdown(f"""
                <div class='ios-card' style='border-right: 5px solid {pnl_color}; padding: 12px 18px; margin-bottom: 8px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
                        <div>
                            <strong style='font-size: 14px; color: #f8fafc;'>{symbol}</strong>
                            <span style='color: {side_color}; font-weight: bold; font-size: 12px; margin-left: 6px;'>{side.lower()} {qty:.2f}</span>
                        </div>
                        <span style='font-size: 11px; color: #94a3b8;'>{close_time}</span>
                    </div>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <span style='font-size: 13px; color: #cbd5e1;'>{entry_p:,.2f} → {close_p:,.2f}</span>
                        <strong style='color: {pnl_color}; font-size: 14px;'>{pnl_sign}${pnl:,.2f}</strong>
                    </div>
                </div>
                """, unsafe_allow_html=True)
