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


    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@500&display=swap');
    
    /* 统一的支付卡片容器 */
    .pay-card {
        background: #fdfdfd;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-top: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    
    /* 金额显示 */
    .pay-amount-display {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.8rem;
        font-weight: 800;
        margin: 10px 0;
    }
    
    /* 支付方式标签 */
    .pay-label {
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 5px;
    }
    
    /* 底部操作提示 */
    .pay-instruction {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-top: 15px;
        margin-bottom: 5px;
    }
    
    /* 不同渠道的品牌色 */
    .color-wechat { color: #2AAD67; }
    .color-alipay { color: #1677ff; }
    .color-paypal { color: #003087; }
    
    /* 按钮微调 */
    div[data-testid="stButton"] button {
        border-radius: 8px;
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
        'coffee_desc': '如果这些工具帮到了你，欢迎支持老登的创作。',
        'footer_btn3': '请老登一杯咖啡 ☕',
        'custom_count': '自定义数量 (杯)',
        'total_label': '总计投入',
        'pay_wechat': '微信支付',
        'pay_alipay': '支付宝',
        'pay_paypal': '贝宝',
        'paid_btn': '🎉 我已支付，给老登打气！',
        'paid_toast': '收到！感谢你的 {count} 杯咖啡！代码写得更有劲了！❤️',
        'presets': [("☕ 提神", "由衷感谢"), ("🍗 鸡腿", "动力加倍"), ("🚀 续命", "老登不朽")],
        "coffee_btn": "☕ 请开发者喝咖啡",
        "coffee_title": " ",
        "pay_success": "收到！感谢打赏。代码写得更有劲了！❤️",
        "coffee_amount": "请输入打赏杯数"
    },
    'en': {
        'footer_btn3': 'Support Me ☕',
        'custom_count': 'Custom count (cups)',
        'total_label': 'Total',
        'pay_wechat': 'WeChat',
        'pay_alipay': 'Alipay',
        'pay_paypal': 'PayPal',
        'paid_btn': '🎉 I have paid!',
        'paid_toast': 'Received! Thanks for the {count} coffees! ❤️',
        'presets': [("☕ Coffee", "Thanks"), ("🍗 Meal", "Power Up"), ("🚀 Rocket", "Amazing")],
        "coffee_btn": "☕ Buy me a coffee",
        "coffee_title": " ",
        "coffee_desc": "If you enjoyed this, consider buying me a coffee!",
        "pay_success": "Received! Thanks for the coffee! ❤️",
        "coffee_amount": "Enter Coffee Count"
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

def get_txt(key): 
    return lang_texts[st.session_state.language][key]

st.title("Component Demo")
st.write("点击下方按钮体验打赏弹窗：")

c1, c2, c3 = st.columns([1, 2, 1])

with c2:
    @st.dialog(" " + get_txt('coffee_title'), width="small")
    def show_coffee_window():
        # 1. 顶部描述
        st.markdown(f"""<div style="text-align:center; color:#666; margin-bottom:15px;">{get_txt('coffee_desc')}</div>""", unsafe_allow_html=True)
        
        # 2. 快捷选择按钮
        presets = [("☕", 1), ("🍗", 3), ("🚀", 5)]
        def set_val(n): st.session_state.coffee_num = n
        
        cols = st.columns(3, gap="small")
        for i, (icon, num) in enumerate(presets):
            with cols[i]:
                # 点击快捷键直接修改 session_state
                if st.button(f"{icon} {num}", use_container_width=True, key=f"p_btn_{i}"): 
                    set_val(num)
        st.write("")

        # 3. 自定义输入与金额计算
        col_amount, col_total = st.columns([1, 1], gap="small")
        with col_amount: 
            cnt = st.number_input(get_txt('coffee_amount'), 1, 100, step=1, key='coffee_num')
        
        # 汇率计算逻辑
        cny_total = cnt * 10
        usd_total = cnt * 2
        
        with col_total: 
            # 动态显示人民币总额
            st.markdown(f"""<div style="background:#fff1f2; border-radius:8px; padding:8px; text-align:center; color:#e11d48; font-weight:bold; font-size:1.5rem; height: 100%; display: flex; align-items: center; justify-content: center;">¥{cny_total}</div>""", unsafe_allow_html=True)
        
        # 4. 统一支付卡片渲染函数 (核心复用逻辑)
        def render_pay_tab(title, amount_str, color_class, img_path, qr_data_suffix, link_url=None):
            # 卡片头部
            st.markdown(f"""
                <div class="pay-card">
                    <div class="pay-label {color_class}">{title}</div>
                    <div class="pay-amount-display {color_class}">{amount_str}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # 卡片中部：二维码或图片
            # 使用 container + columns 居中图片
            c_img_1, c_img_2, c_img_3 = st.columns([1, 3, 1])
            with c_img_2:
                if os.path.exists(img_path): 
                    st.image(img_path, use_container_width=True)
                else: 
                    # 本地图片不存在时，生成 API 二维码作为演示
                    qr_data = f"Donate_{cny_total}_{qr_data_suffix}"
                    # PayPal 如果是链接模式，二维码也可以指向链接
                    if link_url: qr_data = link_url
                    st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={qr_data}", use_container_width=True)
            
            # 卡片底部：按钮或提示文字
            if link_url:
                # PayPal 等外链跳转
                st.link_button(f"👉 Pay {amount_str}", link_url, type="primary", use_container_width=True)
            else:
                # 扫码提示
                st.markdown('<div class="pay-instruction">请使用手机扫描上方二维码</div>', unsafe_allow_html=True)

        # 5. 支付方式 Tabs
        st.write("")
        t1, t2, t3 = st.tabs([get_txt('pay_wechat'), get_txt('pay_alipay'), get_txt('pay_paypal')])
        
        with t1:
            render_pay_tab("WeChat Pay", f"¥{cny_total}", "color-wechat", "wechat_pay.jpg", "WeChat")
            
        with t2:
            render_pay_tab("Alipay", f"¥{cny_total}", "color-alipay", "ali_pay.jpg", "Alipay")
            
        with t3:
            # PayPal 特殊处理：提供 URL 跳转
            render_pay_tab("PayPal", f"${usd_total}", "color-paypal", "paypal.png", "PayPal", "https://paypal.me/ytqz")
        
        # 6. 确认按钮
        st.write("")
        if st.button("🎉 " + get_txt('pay_success').split('!')[0], type="primary", use_container_width=True):
            st.balloons()
            st.success(get_txt('pay_success').format(count=cnt))
            time.sleep(1.5)
            st.rerun()

    # 主界面触发按钮
    if st.button(get_txt('coffee_btn'), use_container_width=True):
        show_coffee_window()

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
