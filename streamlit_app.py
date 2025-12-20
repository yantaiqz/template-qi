import streamlit as st
import sqlite3
import uuid
import datetime
import os
import time

# -------------------------- 全局配置 & 样式（合并去重） --------------------------
st.set_page_config(
    page_title="工具集合 | AI.Fun",
    page_icon="🦕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 合并所有CSS样式（去重+兼容低版本）
st.markdown("""
<style>
    /* 隐藏Streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {display: none;}
    
    /* 右上角链接按钮样式 */
    .neal-btn {
        font-family: 'Inter', sans-serif;
        background: #fff;
        border: 1px solid #e5e7eb;
        color: #111;
        font-weight: 600;
        font-size: 14px;
        padding: 8px 16px;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        white-space: nowrap;
        text-decoration: none !important;
        width: 100%;
        height: 38px;
    }
    .neal-btn:hover {
        background: #f9fafb;
        border-color: #111;
        transform: translateY(-1px);
    }
    .neal-btn-link { text-decoration: none; width: 100%; display: block; }
    
    /* 统计模块样式 */
    .metric-container {
        display: flex;
        justify-content: center;
        gap: 20px;
        margin-top: 20px;
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 10px;
        border: 1px solid #e9ecef;
    }
    .metric-box {
        text-align: center;
    }
    .metric-sub {
        font-size: 0.7rem;
        color: #adb5bd;
    }
    
    /* 咖啡打赏相关样式（兼容低版本） */
    .stButton > button {
        background: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 10px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
        width: 100%;
    }
    .stButton > button:hover {
        background: #f9fafb !important;
        border-color: #d1d5db !important;
        transform: translateY(-1px);
    }
    .price-container {
        text-align:center; margin: 15px 0; 
        padding: 15px; background-color:#f8f9fa; 
        border-radius:12px; border:1px solid #eee;
    }
    .price-desc { font-size:0.9rem; color:#666; }
    .price-value { font-size:2.4rem; font-weight:800; color:#d9534f; line-height:1.2; }
    
    /* 语言切换按钮样式（替代class_） */
    [data-testid="button-lang_switch"] {
        position: fixed; top: 20px; right: 120px; z-index: 999;
        width: 80px !important;
    }
    /* 打赏按钮高亮（替代type="primary"） */
    [data-testid="button-donate_btn"] {
        background-color: #0ea5e9 !important;
        color: white !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------- 状态初始化（提前到最顶部） --------------------------
# 权限相关状态
if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.datetime.now()
    st.session_state.access_status = 'free'
    st.session_state.unlock_time = None

# 咖啡打赏相关状态
if 'language' not in st.session_state:
    st.session_state.language = 'zh'
if 'coffee_num' not in st.session_state:
    st.session_state.coffee_num = 1

# 数据库相关状态
if 'has_counted' not in st.session_state:
    st.session_state.has_counted = False
if 'visitor_id' not in st.session_state:
    st.session_state["visitor_id"] = str(uuid.uuid4())

# -------------------------- 常量配置 --------------------------
# 权限配置
FREE_PERIOD_SECONDS = 60
ACCESS_DURATION_HOURS = 24
UNLOCK_CODE = "vip24"

# 数据库配置
DB_DIR = os.path.expanduser("~/")
DB_FILE = os.path.join(DB_DIR, "visit_stats.db")

# 多语言配置（咖啡打赏）
lang_texts = {
    'zh': {
        'coffee_title': '请老登喝杯咖啡 ☕',
        'coffee_desc': '如果这些小工具让你感到了底线，欢迎支持老登的创作。',
        'footer_btn3': '请老登一杯咖啡 ☕',
        'custom_count': '自定义数量 (杯)',
        'support_amount': '支持 {count} 杯需',
        'img_error': '收款码图片加载失败'
    },
    'en': {
        'coffee_title': 'Buy me a coffee ☕',
        'coffee_desc': 'If you find these tools helpful, consider supporting my work!',
        'footer_btn3': 'Support Me ☕',
        'custom_count': 'Custom count (cups)',
        'support_amount': 'Support {count} cups',
        'img_error': 'Payment QR code load failed'
    }
}
current_text = lang_texts[st.session_state.language]

# -------------------------- 右上角功能区 --------------------------
col_empty, col_lang, col_more = st.columns([0.7, 0.1, 0.2])

with col_lang:
    # 语言切换按钮（唯一定义，兼容低版本）
    l_btn = "En" if st.session_state.language == 'zh' else "中"
    if st.button(l_btn, key="lang_switch"):
        st.session_state.language = 'en' if st.session_state.language == 'zh' else 'zh'
        st.rerun()

with col_more:
    # HTML链接按钮
    st.markdown(
        f"""
        <a href="https://haowan.streamlit.app/" target="_blank" class="neal-btn-link">
            <button class="neal-btn">✨ 更多好玩应用</button>
        </a>
        """, 
        unsafe_allow_html=True
    )

# -------------------------- 权限校验逻辑 --------------------------
current_time = datetime.datetime.now()
access_granted = False

# 检查免费期/解锁状态
if st.session_state.access_status == 'free':
    time_elapsed = (current_time - st.session_state.start_time).total_seconds()
    if time_elapsed < FREE_PERIOD_SECONDS:
        access_granted = True
        time_left = FREE_PERIOD_SECONDS - time_elapsed
        st.info(f"⏳ **免费试用中... 剩余 {time_left:.1f} 秒。**")
    else:
        st.session_state.access_status = 'locked'
        st.session_state.start_time = None
        st.rerun()
        
elif st.session_state.access_status == 'unlocked':
    unlock_expiry = st.session_state.unlock_time + datetime.timedelta(hours=ACCESS_DURATION_HOURS)
    if current_time < unlock_expiry:
        access_granted = True
        time_left_delta = unlock_expiry - current_time
        hours = int(time_left_delta.total_seconds() // 3600)
        minutes = int((time_left_delta.total_seconds() % 3600) // 60)
        st.info(f"🔓 **付费权限剩余:** {hours} 小时 {minutes} 分钟")
    else:
        st.session_state.access_status = 'locked'
        st.session_state.unlock_time = None
        st.rerun()

# 锁定界面
if not access_granted:
    st.error("🔒 **访问受限。免费试用期已结束！**")
    st.markdown(f"""
    <div style="background-color: #fff; padding: 15px; border-radius: 8px; border: 1px solid #e5e7eb; margin-top: 15px;">
        <p style="font-weight: 600; color: #1f2937; margin-bottom: 5px;">🔑 10元解锁无限制访问权限，获取代码链接 (请在微信中打开)</p>
        <p style="font-size: 0.9em; background-color: #eef2ff; padding: 8px; border-radius: 4px; overflow-wrap: break-word;">
            <code>#小程序://闲鱼/i4ahD0rqwGB5lba</code>
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("access_lock_form"):
        password_input = st.text_input("解锁代码:", type="password", key="password_input_key")
        submit_button = st.form_submit_button("验证并解锁")
        
        if submit_button:
            if password_input == UNLOCK_CODE:
                st.session_state.access_status = 'unlocked'
                st.session_state.unlock_time = datetime.datetime.now()
                st.success("🎉 解锁成功！您已获得 1 天访问权限。页面即将刷新...")
                st.rerun()
            else:
                st.error("❌ 代码错误，请重试。")
    st.stop()

# -------------------------- 数据库逻辑 --------------------------
def init_db():
    """初始化数据库（含Schema Migration）"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    # 创建表
    c.execute('''CREATE TABLE IF NOT EXISTS daily_traffic 
                 (date TEXT PRIMARY KEY, pv_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS visitors 
                 (visitor_id TEXT PRIMARY KEY, first_visit_date TEXT)''')
    
    # 检查并添加last_visit_date列
    c.execute("PRAGMA table_info(visitors)")
    columns = [info[1] for info in c.fetchall()]
    if "last_visit_date" not in columns:
        try:
            c.execute("ALTER TABLE visitors ADD COLUMN last_visit_date TEXT")
            c.execute("UPDATE visitors SET last_visit_date = first_visit_date WHERE last_visit_date IS NULL")
        except Exception as e:
            print(f"数据库升级失败: {e}")

    conn.commit()
    conn.close()

def track_and_get_stats():
    """核心统计逻辑"""
    init_db()
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    today_str = datetime.datetime.utcnow().date().isoformat()
    visitor_id = st.session_state["visitor_id"]

    # 仅首次计数
    if not st.session_state["has_counted"]:
        try:
            # 更新PV
            c.execute("INSERT OR IGNORE INTO daily_traffic (date, pv_count) VALUES (?, 0)", (today_str,))
            c.execute("UPDATE daily_traffic SET pv_count = pv_count + 1 WHERE date=?", (today_str,))
            
            # 更新UV
            c.execute("SELECT visitor_id FROM visitors WHERE visitor_id=?", (visitor_id,))
            exists = c.fetchone()
            if exists:
                c.execute("UPDATE visitors SET last_visit_date=? WHERE visitor_id=?", (today_str, visitor_id))
            else:
                c.execute("INSERT INTO visitors (visitor_id, first_visit_date, last_visit_date) VALUES (?, ?, ?)", 
                          (visitor_id, today_str, today_str))
            
            conn.commit()
            st.session_state["has_counted"] = True
        except Exception as e:
            st.error(f"数据库写入错误: {e}")

    # 查询数据
    c.execute("SELECT COUNT(*) FROM visitors WHERE last_visit_date=?", (today_str,))
    today_uv = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM visitors")
    total_uv = c.fetchone()[0]

    c.execute("SELECT pv_count FROM daily_traffic WHERE date=?", (today_str,))
    res_pv = c.fetchone()
    today_pv = res_pv[0] if res_pv else 0
    
    conn.close()
    return today_uv, total_uv, today_pv

# 执行统计并展示
try:
    today_uv, total_uv, today_pv = track_and_get_stats()
except Exception as e:
    st.error(f"统计模块出错: {e}")
    today_uv, total_uv, today_pv = 0, 0, 0

st.markdown(f"""
<div class="metric-container">
    <div class="metric-box">
        <div class="metric-sub">今日 UV: {today_uv} 访客数</div>
    </div>
    <div class="metric-box" style="border-left: 1px solid #dee2e6; border-right: 1px solid #dee2e6; padding-left: 20px; padding-right: 20px;">
        <div class="metric-sub">历史总 UV: {total_uv} 总独立访客</div>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------- 咖啡打赏功能（兼容低版本弹窗） --------------------------
def show_coffee_window():
    """替代st.dialog的低版本弹窗实现"""
    with st.expander(current_text['coffee_title'], expanded=True):
        # 描述文本
        st.markdown(f"""
            <div style='text-align:center; margin-bottom:15px; color:#444; font-size:0.95rem;'>
                {current_text['coffee_desc']}
            </div>
        """, unsafe_allow_html=True)

        # 数量选择回调
        def set_coffee(num):
            st.session_state.coffee_num = num

        # 快速选择按钮
        c1, c2, c3 = st.columns(3)
        with c1:
            st.button("🍺 1杯", use_container_width=True, on_click=set_coffee, args=(1,), key="coffee_1")
        with c2:
            st.button("🍺 3杯", use_container_width=True, on_click=set_coffee, args=(3,), key="coffee_3")
        with c3:
            st.button("🍺 5杯", use_container_width=True, on_click=set_coffee, args=(5,), key="coffee_5")

        # 自定义数量
        count = st.number_input(
            current_text['custom_count'], 
            min_value=1, 
            max_value=100, 
            step=1, 
            key='coffee_num'
        )
        
        # 金额展示
        total_price = count * 10
        st.markdown(f"""
            <div class="price-container">
                <div class="price-desc">{current_text['support_amount'].format(count=count)}</div>
                <div class="price-value">¥ {total_price}</div>
            </div>
        """, unsafe_allow_html=True)

        # 收款码（容错处理）
        col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
        with col_img2:
            try:
                # 建议替换为网络图片URL，避免本地路径问题
                st.image("https://via.placeholder.com/200x200?text=收款码", use_container_width=True)
            except Exception as e:
                st.error(current_text['img_error'])
                st.caption(f"错误信息: {str(e)}")

# 咖啡打赏入口
st.markdown(f"""
    <h1 style='text-align:center; font-size:2.5rem; font-weight:800; margin: 2rem 0;'>
        {current_text['coffee_title']}
    </h1>
""", unsafe_allow_html=True)

st.markdown("<div style='text-align:center; margin: 2rem 0;'>", unsafe_allow_html=True)
if st.button(current_text['footer_btn3'], use_container_width=True, key="donate_btn"):
    show_coffee_window()
st.markdown("</div>", unsafe_allow_html=True)

# 页面标题（核心内容）
st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)
