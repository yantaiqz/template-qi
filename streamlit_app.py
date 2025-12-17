import streamlit as st
import datetime
import sqlite3
import uuid
import os
import urllib.parse

# --- 权限配置 ---
FREE_PERIOD_SECONDS = 60      # 免费试用期 60 秒
ACCESS_DURATION_HOURS = 24    # 密码解锁后的访问时长 24 小时
UNLOCK_CODE = "vip24"        # 预设的解锁密码
# --- 配置结束 ---

# -------------------------------------------------------------
# --- 数据库初始化（新增：存储访客计时状态） ---
# -------------------------------------------------------------
# 持久化目录（Streamlit Share 仅~/目录可持久化）
DB_DIR = os.path.expanduser("~/")
DB_FILE = os.path.join(DB_DIR, "visit_stats.db")

def init_full_db():
    """初始化完整数据库（包含访客计时表）"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    # 1. 原有流量统计表格
    c.execute('''CREATE TABLE IF NOT EXISTS daily_traffic 
                 (date TEXT PRIMARY KEY, 
                  pv_count INTEGER DEFAULT 0)''')
                  
    c.execute('''CREATE TABLE IF NOT EXISTS visitors 
                 (visitor_id TEXT PRIMARY KEY, 
                  first_visit_date TEXT,
                  last_visit_date TEXT)''')
    
    # 2. 新增：访客权限表
    c.execute('''CREATE TABLE IF NOT EXISTS visitor_access 
                 (visitor_id TEXT PRIMARY KEY,
                  start_time TEXT,        # 免费期开始时间（ISO字符串）
                  access_status TEXT,     # free/locked/unlocked
                  unlock_time TEXT,       # 解锁时间（ISO字符串）
                  FOREIGN KEY (visitor_id) REFERENCES visitors(visitor_id))''')
    
    # 修复visitors表缺失列
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

# -------------------------------------------------------------
# --- 访客ID管理（URL参数持久化） ---
# -------------------------------------------------------------
def get_visitor_id_from_url():
    """从URL参数获取/生成访客ID（无需Cookie）"""
    # 获取当前URL参数
    query_params = st.query_params
    
    # 从URL参数读取visitor_id
    visitor_id = query_params.get("visitor_id", [None])[0]
    
    if not visitor_id:
        # 生成新ID
        visitor_id = str(uuid.uuid4())
        # 更新URL参数（不刷新页面）
        st.query_params["visitor_id"] = visitor_id
    
    # 同步到session_state
    if "visitor_id" not in st.session_state:
        st.session_state["visitor_id"] = visitor_id
    
    return visitor_id

# -------------------------------------------------------------
# --- 权限状态管理（从数据库读取/写入） ---
# -------------------------------------------------------------
def get_visitor_access_status(visitor_id):
    """从数据库获取访客权限状态"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    c.execute("SELECT start_time, access_status, unlock_time FROM visitor_access WHERE visitor_id=?", (visitor_id,))
    res = c.fetchone()
    conn.close()
    
    if not res:
        # 新访客：初始化状态
        start_time = datetime.datetime.now().isoformat()
        return {
            "start_time": start_time,
            "access_status": "free",
            "unlock_time": None
        }
    
    # 解析数据库中的时间字符串
    return {
        "start_time": res[0],
        "access_status": res[1],
        "unlock_time": res[2] if res[2] else None
    }

def save_visitor_access_status(visitor_id, status_dict):
    """保存访客权限状态到数据库"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    # 插入或更新
    c.execute('''INSERT OR REPLACE INTO visitor_access 
                 (visitor_id, start_time, access_status, unlock_time)
                 VALUES (?, ?, ?, ?)''',
              (visitor_id,
               status_dict["start_time"],
               status_dict["access_status"],
               status_dict["unlock_time"]))
    
    conn.commit()
    conn.close()

# -------------------------------------------------------------
# --- 初始化状态 ---
# -------------------------------------------------------------
# 初始化数据库
init_full_db()

# 获取访客ID（URL参数）
visitor_id = get_visitor_id_from_url()

# 从数据库获取权限状态
access_data = get_visitor_access_status(visitor_id)

# 初始化session_state
if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.datetime.fromisoformat(access_data["start_time"]) if access_data["start_time"] else datetime.datetime.now()
if 'access_status' not in st.session_state:
    st.session_state.access_status = access_data["access_status"] or "free"
if 'unlock_time' not in st.session_state:
    st.session_state.unlock_time = datetime.datetime.fromisoformat(access_data["unlock_time"]) if access_data["unlock_time"] else None

# -------------------------------------------------------------
# --- 检查访问状态和时间逻辑 ---
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
        
        # 保存到数据库
        save_visitor_access_status(visitor_id, {
            "start_time": None,
            "access_status": "locked",
            "unlock_time": None
        })
        
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
        
        # 保存到数据库
        save_visitor_access_status(visitor_id, {
            "start_time": None,
            "access_status": "locked",
            "unlock_time": None
        })
        
        st.rerun() # 强制刷新

# -------------------------------------------------------------
# --- 锁定界面及密码输入 ---
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
                
                # 保存解锁状态到数据库
                save_visitor_access_status(visitor_id, {
                    "start_time": None,
                    "access_status": "unlocked",
                    "unlock_time": st.session_state.unlock_time.isoformat()
                })
                
                st.success("🎉 解锁成功！您已获得 1 天访问权限。页面即将刷新...")
                st.rerun()
            else:
                st.error("❌ 代码错误，请重试。")
                
    # 强制停止脚本，隐藏所有受保护的内容
    st.stop()

# -------------------------------------------------------------
# --- 原有流量统计逻辑 ---
# -------------------------------------------------------------
def track_and_get_stats():
    """核心统计逻辑"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    # 修正时区：使用本地时间
    today_str = datetime.datetime.now().date().isoformat()

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
            
            # 3. 确保访客权限记录存在
            c.execute("SELECT visitor_id FROM visitor_access WHERE visitor_id=?", (visitor_id,))
            if not c.fetchone():
                save_visitor_access_status(visitor_id, {
                    "start_time": st.session_state.start_time.isoformat(),
                    "access_status": "free",
                    "unlock_time": None
                })
            
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

# 自动刷新实现实时倒计时
if st.session_state.access_status == 'free' and access_granted:
    st.markdown(f"""
    <meta http-equiv="refresh" content="1">
    """, unsafe_allow_html=True)
