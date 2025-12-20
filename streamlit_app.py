import streamlit as st
import sqlite3
import uuid
import datetime
import os
import time

# ==========================================
# 1. 全局配置
# ==========================================
st.set_page_config(
    page_title="工具集合 | AI.Fun",
    page_icon="🦕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. 样式合并 (基础样式 + 咖啡加强版样式)
# ==========================================
st.markdown("""
<style>
    /* --- 基础设置 --- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {display: none;}
    .stApp { background-color: #FFFFFF !important; }

    /* --- 右上角按钮 --- */
    .neal-btn {
        font-family: 'Inter', sans-serif; background: #fff;
        border: 1px solid #e5e7eb; color: #111; font-weight: 600;
        padding: 8px 16px; border-radius: 8px; cursor: pointer;
        transition: all 0.2s; display: inline-flex; align-items: center;
        justify-content: center; text-decoration: none !important;
        width: 100%;
    }
    .neal-btn:hover { background: #f9fafb; transform: translateY(-1px); }
    .neal-btn-link { text-decoration: none; width: 100%; display: block; }

    /* --- 统计模块 --- */
    .metric-container {
        display: flex; justify-content: center; gap: 20px;
        margin-top: 20px; padding: 10px; background-color: #f8f9fa;
        border-radius: 10px; border: 1px solid #e9ecef;
    }
    .metric-box { text-align: center; }
    .metric-sub { font-size: 0.7rem; color: #adb5bd; }

    /* --- ☕ 咖啡打赏 2.0 专用样式 --- */
    .coffee-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border: 1px solid #e5e7eb; border-radius: 16px;
        padding: 5px; box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        margin-bottom: 5px; text-align: center;
    }
    .price-tag-container {
        background: #fff0f0; border: 1px dashed #ffcccc;
        border-radius: 12px; padding: 10px; text-align: center;
        margin-top: 5px; transition: all 0.3s;
    }
    .price-tag-container:hover { transform: scale(1.02); }
    .price-label { color: #888; font-size: 0.8rem; margin-bottom: 2px; }
    .price-number { color: #d9534f; font-weight: 900; font-size: 1.8rem; }
    
    /* 语言切换按钮定位 */
    [data-testid="button-lang_switch"] {
        position: fixed; top: 20px; right: 120px; z-index: 999; width: 80px !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 状态初始化
# ==========================================
if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.datetime.now()
    st.session_state.access_status = 'free'
    st.session_state.unlock_time = None

if 'language' not in st.session_state:
    st.session_state.language = 'zh'
if 'coffee_num' not in st.session_state:
    st.session_state.coffee_num = 1

if 'has_counted' not in st.session_state:
    st.session_state.has_counted = False
if 'visitor_id' not in st.session_state:
    st.session_state["visitor_id"] = str(uuid.uuid4())

# ==========================================
# 4. 常量与文本配置
# ==========================================
FREE_PERIOD_SECONDS = 60
ACCESS_DURATION_HOURS = 24
UNLOCK_CODE = "vip24"
DB_FILE = os.path.join(os.path.expanduser("~/"), "visit_stats.db")

lang_texts = {
    'zh': {
        'coffee_title': '请老登喝杯咖啡 ☕',
        'coffee_desc': '如果这些工具帮到了你，欢迎支持老登的创作。',
        'footer_btn3': '请老登一杯咖啡 ☕',
        'custom_count': '自定义数量 (杯)',
        'total_label': '总计投入',
        'pay_wechat': '💬 微信支付',
        'pay_alipay': '💙 支付宝',
        'paid_btn': '🎉 我已支付，给老登打气！',
        'paid_toast': '收到！感谢你的 {count} 杯咖啡！代码写得更有劲了！❤️',
        'presets': [("☕ 提神", "由衷感谢"), ("🍗 鸡腿", "动力加倍"), ("🚀 续命", "老登不朽")]
    },
    'en': {
        'coffee_title': 'Buy me a coffee ☕',
        'coffee_desc': 'If you find these tools helpful, consider supporting my work!',
        'footer_btn3': 'Support Me ☕',
        'custom_count': 'Custom count (cups)',
        'total_label': 'Total',
        'pay_wechat': '💬 WeChat',
        'pay_alipay': '💙 Alipay',
        'paid_btn': '🎉 I have paid!',
        'paid_toast': 'Received! Thanks for the {count} coffees! ❤️',
        'presets': [("☕ Coffee", "Thanks"), ("🍗 Meal", "Power Up"), ("🚀 Rocket", "Amazing")]
    }
}
current_text = lang_texts[st.session_state.language]

# ==========================================
# 5. 右上角功能区 (语言 & 更多)
# ==========================================
col_empty, col_lang, col_more = st.columns([0.7, 0.1, 0.2])
with col_lang:
    l_btn = "En" if st.session_state.language == 'zh' else "中"
    if st.button(l_btn, key="lang_switch"):
        st.session_state.language = 'en' if st.session_state.language == 'zh' else 'zh'
        st.rerun()

with col_more:
    st.markdown("""
        <a href="#" target="_blank" class="neal-btn-link">
            <button class="neal-btn">✨ 更多好玩应用</button>
        </a>""", unsafe_allow_html=True)

# ==========================================
# 6. 权限校验逻辑 (保持原样)
# ==========================================
current_time = datetime.datetime.now()
access_granted = False

if st.session_state.access_status == 'free':
    time_elapsed = (current_time - st.session_state.start_time).total_seconds()
    if time_elapsed < FREE_PERIOD_SECONDS:
        access_granted = True
        st.info(f"⏳ **免费试用中... 剩余 {FREE_PERIOD_SECONDS - time_elapsed:.1f} 秒。**")
    else:
        st.session_state.access_status = 'locked'
        st.rerun()
elif st.session_state.access_status == 'unlocked':
    unlock_expiry = st.session_state.unlock_time + datetime.timedelta(hours=ACCESS_DURATION_HOURS)
    if current_time < unlock_expiry:
        access_granted = True
        left = unlock_expiry - current_time
        st.info(f"🔓 **付费权限剩余:** {int(left.total_seconds()//3600)} 小时")
    else:
        st.session_state.access_status = 'locked'
        st.rerun()

if not access_granted:
    st.error("🔒 **访问受限。免费试用期已结束！**")
    st.markdown(f"""
    <div style="background-color: #fff; padding: 15px; border-radius: 8px; border: 1px solid #e5e7eb; margin-top: 15px;">
        <p style="font-weight: 600; color: #1f2937; margin-bottom: 5px;">🔑 10元解锁无限制访问权限</p>
        <code style="background-color: #eef2ff; padding: 5px;">#小程序://闲鱼/i4ahD0rqwGB5lba</code>
    </div>""", unsafe_allow_html=True)
    
    with st.form("lock_form"):
        if st.form_submit_button("验证并解锁") and st.text_input("解锁代码", type="password") == UNLOCK_CODE:
            st.session_state.access_status, st.session_state.unlock_time = 'unlocked', datetime.datetime.now()
            st.rerun()
    st.stop()

# ==========================================
# 7. 数据库逻辑 (保持原样)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS daily_traffic (date TEXT PRIMARY KEY, pv_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS visitors (visitor_id TEXT PRIMARY KEY, first_visit_date TEXT, last_visit_date TEXT)''')
    try:
        c.execute("ALTER TABLE visitors ADD COLUMN last_visit_date TEXT")
        c.execute("UPDATE visitors SET last_visit_date = first_visit_date")
    except: pass
    conn.commit(); conn.close()

def track_and_get_stats():
    init_db(); conn = sqlite3.connect(DB_FILE, check_same_thread=False); c = conn.cursor()
    today = datetime.datetime.utcnow().date().isoformat()
    if not st.session_state.has_counted:
        try:
            c.execute("INSERT OR IGNORE INTO daily_traffic (date, pv_count) VALUES (?, 0)", (today,))
            c.execute("UPDATE daily_traffic SET pv_count = pv_count + 1 WHERE date=?", (today,))
            c.execute("INSERT OR IGNORE INTO visitors (visitor_id, first_visit_date) VALUES (?, ?)", (st.session_state.visitor_id, today))
            c.execute("UPDATE visitors SET last_visit_date=? WHERE visitor_id=?", (today, st.session_state.visitor_id))
            conn.commit(); st.session_state.has_counted = True
        except: pass
    
    try:
        t_uv = c.execute("SELECT COUNT(*) FROM visitors WHERE last_visit_date=?", (today,)).fetchone()[0]
        a_uv = c.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]
        t_pv = c.execute("SELECT pv_count FROM daily_traffic WHERE date=?", (today,)).fetchone()[0]
    except: t_uv, a_uv, t_pv = 0, 0, 0
    conn.close(); return t_uv, a_uv, t_pv

try: today_uv, total_uv, today_pv = track_and_get_stats()
except: today_uv, total_uv, today_pv = 0, 0, 0

st.markdown(f"""
<div class="metric-container">
    <div class="metric-box"><div class="metric-sub">今日 UV: {today_uv}</div></div>
    <div class="metric-box" style="border-left:1px solid #ddd; padding-left:20px;"><div class="metric-sub">历史 UV: {total_uv}</div></div>
</div>""", unsafe_allow_html=True)

# ==========================================
# 8. 新版咖啡打赏逻辑 (替换旧版)
# ==========================================
@st.dialog(" ", width="small")
def show_coffee_window():
    # 头部信息
    st.markdown(f"""
    <div class="coffee-card">
        <h3 style="margin:0; font-size:1.2rem;">{current_text['coffee_title']}</h3>
        <p style="color:#666; font-size:0.8rem; margin-top:5px;">{current_text['coffee_desc']}</p>
    </div>""", unsafe_allow_html=True)

    # 1. 预设按钮
    def set_val(n): st.session_state.coffee_num = n
    cols = st.columns(3)
    # 获取当前语言的预设文案
    presets_data = current_text['presets']
    # 对应的数量
    preset_nums = [1, 3, 5]
    
    for i, (txt, sub) in enumerate(presets_data):
        with cols[i]:
            if st.button(txt, use_container_width=True, key=f"c_btn_{i}"): set_val(preset_nums[i])
            st.markdown(f"<div style='text-align:center; font-size:0.7rem; color:#aaa; margin-top:-5px;'>{sub}</div>", unsafe_allow_html=True)
    
    st.write("")
    
    # 2. 数量与金额
    c1, c2 = st.columns([1, 1])
    with c1:
        cnt = st.number_input(current_text['custom_count'], 1, 100, step=1, key='coffee_num')
    total = cnt * 10
    with c2:
        st.markdown(f"""
        <div class="price-tag-container">
            <div class="price-label">{current_text['total_label']}</div>
            <div class="price-number">¥ {total}</div>
        </div>""", unsafe_allow_html=True)

    # 3. 支付方式 Tab
    t1, t2 = st.tabs([current_text['pay_wechat'], current_text['pay_alipay']])
    
    def show_qr(img_path):
        # 如果图片不存在，显示占位符
        if os.path.exists(img_path):
            st.image(img_path, use_container_width=True)
        else:
            st.warning(f"需放置图片: {img_path}")
            # 仅作演示的在线占位符
            st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=Pay_{total}", width=150)
            
    with t1: show_qr("wechat_pay.jpg")
    with t2: show_qr("ali_pay.jpg")

    # 4. 支付反馈
    st.write("")
    if st.button(current_text['paid_btn'], type="primary", use_container_width=True):
        st.balloons()
        st.success(current_text['paid_toast'].format(count=cnt))
        time.sleep(2)
        st.rerun()

# ==========================================
# 9. 页面主内容与入口
# ==========================================
#st.markdown(f"<h1 style='text-align:center;'>{current_text['coffee_title']}</h1>", unsafe_allow_html=True)

# 触发按钮
col_center = st.columns([1, 2, 1])
with col_center[1]:
    if st.button(current_text['footer_btn3'], use_container_width=True, key="donate_btn"):
        show_coffee_window()

# 示例内容区
st.divider()
st.title("🎈 My new app Content")
st.write("这里是付费/解锁后可见的核心内容区域...")
