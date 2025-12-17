import streamlit as st
from cookies_manager import CookiesManager  # 需要安装：pip install streamlit-cookies-manager
import datetime
import sqlite3
import uuid
import os

# --- 权限配置 ---
FREE_PERIOD_SECONDS = 60      # 免费试用期 60 秒
ACCESS_DURATION_HOURS = 24    # 密码解锁后的访问时长 24 小时
UNLOCK_CODE = "vip24"        # 预设的解锁密码
# --- 配置结束 ---

# -------------------------------------------------------------
# --- 新增：初始化Cookie管理器（核心修复） ---
# -------------------------------------------------------------
cookies = CookiesManager()
if not cookies.ready():
    st.stop()

# -------------------------------------------------------------
# --- 1. 初始化状态（从Cookie恢复，而非仅依赖session_state） ---
# -------------------------------------------------------------
def init_state_from_cookies():
    # 从Cookie读取持久化状态
    cookie_start_time = cookies.get("start_time")
    cookie_access_status = cookies.get("access_status")
    cookie_unlock_time = cookies.get("unlock_time")
    
    # 初始化session_state（优先从Cookie恢复）
    if 'start_time' not in st.session_state:
        if cookie_start_time:
            # 恢复Cookie中的时间（字符串转datetime）
            st.session_state.start_time = datetime.datetime.fromisoformat(cookie_start_time)
        else:
            st.session_state.start_time = datetime.datetime.now()
            # 写入Cookie（datetime转字符串）
            cookies["start_time"] = st.session_state.start_time.isoformat()
    
    if 'access_status' not in st.session_state:
        st.session_state.access_status = cookie_access_status or 'free'
        cookies["access_status"] = st.session_state.access_status
    
    if 'unlock_time' not in st.session_state:
        if cookie_unlock_time:
            st.session_state.unlock_time = datetime.datetime.fromisoformat(cookie_unlock_time)
        else:
            st.session_state.unlock_time = None
            cookies["unlock_time"] = None
    
    # 保存Cookie
    cookies.save()

# 执行状态初始化
init_state_from_cookies()

# -------------------------------------------------------------
# --- 2. 检查访问状态和时间逻辑（修复计时逻辑） ---
# -------------------------------------------------------------
current_time = datetime.datetime.now()
access_granted = False # 默认无权限
time_left = 0  # 初始化剩余时间

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
        st.session_state.start_time = None
        cookies["access_status"] = 'locked'  # 同步到Cookie
        cookies["start_time"] = None         # 清除Cookie中的计时
        cookies.save()
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
        cookies["access_status"] = 'locked'  # 同步到Cookie
        cookies["unlock_time"] = None        # 清除Cookie中的解锁时间
        cookies.save()
        st.rerun() # 强制刷新

# -------------------------------------------------------------
# --- 3. 锁定界面及密码输入（同步解锁状态到Cookie） ---
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
                # 同步解锁状态到Cookie
                cookies["access_status"] = 'unlocked'
                cookies["unlock_time"] = st.session_state.unlock_time.isoformat()
                cookies.save()
                st.success("🎉 解锁成功！您已获得 1 天访问权限。页面即将刷新...")
                st.rerun()
            else:
                st.error("❌ 代码错误，请重试。")
                
    # 强制停止脚本，隐藏所有受保护的内容
    st.stop()

# -------------------------------------------------------------
# --- 以下是原有统计逻辑（保留，仅修正数据库路径） ---
# -------------------------------------------------------------
# 持久化目录（Streamlit Share 仅~/目录可持久化）
DB_DIR = os.path.expanduser("~/")
DB_FILE = os.path.join(DB_DIR, "visit_stats.db")

def init_db():
    """初始化数据库（包含自动修复旧表结构的功能）"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    # 1. 确保表存在
    c.execute('''CREATE TABLE IF NOT EXISTS daily_traffic 
                 (date TEXT PRIMARY KEY, 
                  pv_count INTEGER DEFAULT 0)''')
                  
    c.execute('''CREATE TABLE IF NOT EXISTS visitors 
                 (visitor_id TEXT PRIMARY KEY, 
                  first_visit_date TEXT)''')
    
    # 2. 检查并添加缺失的列
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

def get_visitor_id():
    """获取或生成访客ID"""
    if "visitor_id" not in st.session_state:
        st.session_state["visitor_id"] = str(uuid.uuid4())
    return st.session_state["visitor_id"]

def track_and_get_stats():
    """核心统计逻辑"""
    init_db()
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    # 修正时区：使用本地时间（避免跨天统计错位）
    today_str = datetime.datetime.now().date().isoformat()
    visitor_id = get_visitor_id()

    # --- 写操作 ---
    if "has_counted" not in st.session_state:
        try:
            c.execute("INSERT OR IGNORE INTO daily_traffic (date, pv_count) VALUES (?, 0)", (today_str,))
            c.execute("UPDATE daily_traffic SET pv_count = pv_count + 1 WHERE date=?", (today_str,))
            
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
    c.execute("SELECT COUNT(*) FROM visitors WHERE last_visit_date=?", (today_str,))
    today_uv = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM visitors")
    total_uv = c.fetchone()[0]

    c.execute("SELECT pv_count FROM daily_traffic WHERE date=?", (today_str,))
    res_pv = c.fetchone()
    today_pv = res_pv[0] if res_pv else 0
    
    conn.close()
    
    return today_uv, total_uv, today_pv

# -------------------------- 页面展示 --------------------------
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

# 新增：自动刷新（可选，实现倒计时实时更新）
if st.session_state.access_status == 'free' and access_granted:
    st_autorefresh = st.empty()
    st_autorefresh.markdown(f"""
    <meta http-equiv="refresh" content="1">
    """, unsafe_allow_html=True)
