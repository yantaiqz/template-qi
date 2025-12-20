import streamlit as st



# -------------------------- 右上角功能区 --------------------------

st.markdown("""
<style>

    /* 隐藏右上角的 Streamlit 主菜单（包含部署、源码、设置等） */
    #MainMenu {visibility: hidden;}
    /* 隐藏页脚（包含 "Made with Streamlit" 文字） */
    footer {visibility: hidden;}
    /* 隐藏顶部的 header（包含部署按钮） */
    header[data-testid="stHeader"] {display: none;}
    
    /* 2. HTML 链接按钮 (Get New Apps) */
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
        height: 38px; /* 强制与 st.button 高度对齐 */
    }
    .neal-btn:hover {
        background: #f9fafb;
        border-color: #111;
        transform: translateY(-1px);
    }
    .neal-btn-link { text-decoration: none; width: 100%; display: block; }
</style>
""", unsafe_allow_html=True)


# 创建右上角布局（占满整行，右侧显示按钮/链接）
col_empty, col_lang, col_more = st.columns([0.7, 0.1, 0.2])

with col_lang:
    # 仅展示无实际功能的语言切换按钮
    st.button("中/英文", key="lang_switch", help="语言切换（暂无实际功能）")

with col_more:
    # 修复：改用 HTML 链接按钮（替代 webbrowser 方式，兼容 Streamlit 云环境）
    st.markdown(
        f"""
        <a href="https://haowan.streamlit.app/" target="_blank" class="neal-btn-link">
            <button class="neal-btn">✨ 更多好玩应用</button>
        </a>
        """, 
        unsafe_allow_html=True
    )

    



# -------------------------- 原有代码 --------------------------
st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)

import json
import datetime
import os  
import time 

# --- 权限配置 ---
FREE_PERIOD_SECONDS = 60      # 免费试用期 60 秒
ACCESS_DURATION_HOURS = 24    # 密码解锁后的访问时长 24 小时
UNLOCK_CODE = "vip24"        # 预设的解锁密码
# --- 配置结束 ---

# -------------------------------------------------------------
# --- 1. 初始化会话状态 ---
# -------------------------------------------------------------

# 'start_time': 首次访问时间，用于计算免费试用期
if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.datetime.now()
    # 'access_status': 'free' (免费期), 'locked' (需解锁), 'unlocked' (已解锁)
    st.session_state.access_status = 'free'
    st.session_state.unlock_time = None # 记录密码解锁的时间点

# -------------------------------------------------------------
# --- 2. 检查访问状态和时间逻辑 ---
# -------------------------------------------------------------

current_time = datetime.datetime.now()
access_granted = False # 默认无权限

# 检查当前状态并更新
if st.session_state.access_status == 'free':
    time_elapsed = (current_time - st.session_state.start_time).total_seconds()
    
    if time_elapsed < FREE_PERIOD_SECONDS:
        # 仍在免费期内
        access_granted = True
        time_left = FREE_PERIOD_SECONDS - time_elapsed
        st.info(f"⏳ **免费试用中... 剩余 {time_left:.1f} 秒。**")
    else:
        # 免费期结束，进入锁定状态
        st.session_state.access_status = 'locked'
        st.session_state.start_time = None # 清除免费期计时
        st.rerun() # 强制刷新以立即显示锁定界面
        
elif st.session_state.access_status == 'unlocked':
    unlock_expiry = st.session_state.unlock_time + datetime.timedelta(hours=ACCESS_DURATION_HOURS)
    
    if current_time < unlock_expiry:
        # 在 24 小时有效期内
        access_granted = True
        time_left_delta = unlock_expiry - current_time
        hours = int(time_left_delta.total_seconds() // 3600)
        minutes = int((time_left_delta.total_seconds() % 3600) // 60)
        
        st.info(f"🔓 **付费权限剩余:** {hours} 小时 {minutes} 分钟")
    else:
        # 24 小时已过期，进入锁定状态
        st.session_state.access_status = 'locked'
        st.session_state.unlock_time = None
        st.rerun() # 强制刷新

# -------------------------------------------------------------
# --- 3. 锁定界面及密码输入 ---
# -------------------------------------------------------------

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
                
    # 强制停止脚本，隐藏所有受保护的内容
    st.stop()

import sqlite3
import uuid  # <--- 新增导入
import datetime
import os
# 持久化目录（Streamlit Share 仅~/目录可持久化）
DB_DIR = os.path.expanduser("~/")
DB_FILE = os.path.join(DB_DIR, "visit_stats.db")
# -------------------------- 配置 --------------------------
#DB_FILE = "visit_stats.db"

def init_db():
    """初始化数据库（包含自动修复旧表结构的功能）"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    # 1. 确保表存在（这是旧逻辑）
    c.execute('''CREATE TABLE IF NOT EXISTS daily_traffic 
                 (date TEXT PRIMARY KEY, 
                  pv_count INTEGER DEFAULT 0)''')
                  
    c.execute('''CREATE TABLE IF NOT EXISTS visitors 
                 (visitor_id TEXT PRIMARY KEY, 
                  first_visit_date TEXT)''')
    
    # 2. 【关键修复】手动检查并添加缺失的列 (Schema Migration)
    # 获取 visitors 表的所有列名
    c.execute("PRAGMA table_info(visitors)")
    columns = [info[1] for info in c.fetchall()]
    
    # 如果发现旧数据库里没有 last_visit_date，就动态添加进去
    if "last_visit_date" not in columns:
        try:
            c.execute("ALTER TABLE visitors ADD COLUMN last_visit_date TEXT")
            # 可选：把所有老数据的最后访问时间初始化为他们的首次访问时间，避免空值
            c.execute("UPDATE visitors SET last_visit_date = first_visit_date WHERE last_visit_date IS NULL")
        except Exception as e:
            print(f"数据库升级失败: {e}")

    conn.commit()
    conn.close()

def get_visitor_id():
    """获取或生成访客ID（修复版：使用UUID替代不稳定的内部API）"""
    if "visitor_id" not in st.session_state:
        # 生成一个唯一的随机ID，并保存在当前会话状态中
        st.session_state["visitor_id"] = str(uuid.uuid4())
    return st.session_state["visitor_id"]

def track_and_get_stats():
    """核心统计逻辑"""
    init_db()
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    today_str = datetime.datetime.utcnow().date().isoformat()
    visitor_id = get_visitor_id() # 这里调用修改后的函数

    # --- 写操作 (仅当本Session未计数时执行) ---
    if "has_counted" not in st.session_state:
        try:
            # 1. 更新每日PV
            c.execute("INSERT OR IGNORE INTO daily_traffic (date, pv_count) VALUES (?, 0)", (today_str,))
            c.execute("UPDATE daily_traffic SET pv_count = pv_count + 1 WHERE date=?", (today_str,))
            
            # 2. 更新访客UV信息
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

    # --- 读操作 ---
    # 1. 获取今日UV
    c.execute("SELECT COUNT(*) FROM visitors WHERE last_visit_date=?", (today_str,))
    today_uv = c.fetchone()[0]
    
    # 2. 获取历史总UV
    c.execute("SELECT COUNT(*) FROM visitors")
    total_uv = c.fetchone()[0]

    # 3. 获取今日PV
    c.execute("SELECT pv_count FROM daily_traffic WHERE date=?", (today_str,))
    res_pv = c.fetchone()
    today_pv = res_pv[0] if res_pv else 0
    
    conn.close()
    
    return today_uv, total_uv, today_pv

# -------------------------- 页面展示 --------------------------

# 执行统计
try:
    today_uv, total_uv, today_pv = track_and_get_stats()
except Exception as e:
    st.error(f"统计模块出错: {e}")
    today_uv, total_uv, today_pv = 0, 0, 0

# CSS 样式
st.markdown("""
<style>
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
    .metric-label {
        color: #6c757d;
        font-size: 0.85rem;
        margin-bottom: 2px;
    }
    .metric-value {
        color: #212529;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .metric-sub {
        font-size: 0.7rem;
        color: #adb5bd;
    }
    /* 优化右上角按钮样式 */
    div[data-testid="column"]:nth-child(2) button {
        width: 100%;
        white-space: nowrap;
        font-size: 0.85rem;
        padding: 4px 8px;
    }
    /* 确保HTML按钮和原生按钮样式一致 */
    div[data-testid="column"]:nth-child(3) button:hover {
        background-color: #0284c7;
    }
</style>
""", unsafe_allow_html=True)

# 展示数据
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




# 初始化多语言和咖啡数量状态
if 'language' not in st.session_state:
    st.session_state.language = 'zh'
if 'coffee_num' not in st.session_state:
    st.session_state.coffee_num = 1

# 多语言文本（仅保留咖啡相关）
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

# ==========================================
# 2. 核心CSS（仅保留咖啡弹窗样式）
# ==========================================
st.markdown(f"""
<style>
    /* 基础样式重置 */
    .stApp {{ background-color: #FFFFFF !important; }}
    .block-container {{ padding-top: 2rem; max-width: 600px !important; }}
    
    /* 按钮样式优化 */
    .stButton > button {{
        background: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 10px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
        width: 100%;
    }}
    .stButton > button:hover {{
        background: #f9fafb !important;
        border-color: #d1d5db !important;
        transform: translateY(-1px);
    }}
    
    /* 金额展示样式 */
    .price-container {{
        text-align:center; margin: 15px 0; 
        padding: 15px; background-color:#f8f9fa; 
        border-radius:12px; border:1px solid #eee;
    }}
    .price-desc {{ font-size:0.9rem; color:#666; }}
    .price-value {{ font-size:2.4rem; font-weight:800; color:#d9534f; line-height:1.2; }}
    
    /* 语言切换按钮 */
    .lang-btn {{ position: fixed; top: 20px; right: 20px; z-index: 999; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 咖啡打赏弹窗核心逻辑
# ==========================================
@st.dialog(current_text['coffee_title'])
def show_coffee_window():
    # 1. 打赏描述文本
    st.markdown(f"""
        <div style='text-align:center; margin-bottom:15px; color:#444; font-size:0.95rem;'>
            {current_text['coffee_desc']}
        </div>
    """, unsafe_allow_html=True)

    # 2. 咖啡数量回调函数
    def set_coffee(num):
        st.session_state.coffee_num = num

    # 3. 快速选择按钮（1/3/5杯）
    c1, c2, c3 = st.columns(3)
    with c1:
        st.button("🍺 1杯", use_container_width=True, on_click=set_coffee, args=(1,))
    with c2:
        st.button("🍺 3杯", use_container_width=True, on_click=set_coffee, args=(3,))
    with c3:
        st.button("🍺 5杯", use_container_width=True, on_click=set_coffee, args=(5,))

    # 4. 自定义数量输入框
    count = st.number_input(
        current_text['custom_count'], 
        min_value=1, 
        max_value=100, 
        step=1, 
        key='coffee_num'
    )
    
    # 5. 金额计算与展示
    total_price = count * 10  # 单价10元/杯
    st.markdown(f"""
        <div class="price-container">
            <div class="price-desc">{current_text['support_amount'].format(count=count)}</div>
            <div class="price-value">¥ {total_price}</div>
        </div>
    """, unsafe_allow_html=True)

    # 6. 收款码展示（居中）
    col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
    with col_img2:
        try:
            # 替换为你的收款码图片路径（本地/网络）
            st.image("wechat_pay.jpg", use_container_width=True)
        except Exception as e:
            st.error(current_text['img_error'])
            st.caption(f"错误信息: {str(e)}")

# ==========================================
# 4. 页面渲染（简化版，仅保留核心入口）
# ==========================================
def render_coffee_donate():
    # 语言切换按钮
    with st.container():
        l_btn = "En" if st.session_state.language == 'zh' else "中"
        if st.button(l_btn, key="lang_switch", class_="lang-btn"):
            st.session_state.language = 'en' if st.session_state.language == 'zh' else 'zh'
            st.rerun()

    # 页面标题
    st.markdown(f"""
        <h1 style='text-align:center; font-size:2.5rem; font-weight:800; margin: 2rem 0;'>
            {current_text['coffee_title']}
        </h1>
    """, unsafe_allow_html=True)

    # 打赏入口按钮
    st.markdown("<div style='text-align:center; margin: 2rem 0;'>", unsafe_allow_html=True)
    if st.button(current_text['footer_btn3'], use_container_width=True, type="primary"):
        show_coffee_window()
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 5. 入口函数
# ==========================================
if __name__ == "__main__":
    render_coffee_donate()
