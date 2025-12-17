# 安装依赖：pip install streamlit-cookies-manager
import streamlit as st
from cookies_manager import CookiesManager
import sqlite3
import uuid
import datetime

# -------------------------- 新增：Cookie管理 --------------------------
cookies = CookiesManager()
if not cookies.ready():
    st.stop()

def get_visitor_id():
    """修复版：从Cookie获取访客ID，无则生成并写入Cookie（有效期1年）"""
    # 优先从Cookie读取
    visitor_id = cookies.get("visitor_id")
    if not visitor_id:
        visitor_id = str(uuid.uuid4())
        # 写入Cookie，有效期365天
        cookies["visitor_id"] = visitor_id
        cookies.set_expire("visitor_id", days=365)
        cookies.save()
    # 同步到session_state（可选）
    st.session_state["visitor_id"] = visitor_id
    return visitor_id

# -------------------------- 原有逻辑保留（仅修改get_visitor_id调用） --------------------------
DB_FILE = "visit_stats.db"

def init_db():
    """初始化数据库（保留原有逻辑）"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS daily_traffic 
                 (date TEXT PRIMARY KEY, 
                  pv_count INTEGER DEFAULT 0)''')
                  
    c.execute('''CREATE TABLE IF NOT EXISTS visitors 
                 (visitor_id TEXT PRIMARY KEY, 
                  first_visit_date TEXT,
                  last_visit_date TEXT)''') # 直接创建完整表，避免动态修改
    
    conn.commit()
    conn.close()

def track_and_get_stats():
    """核心统计逻辑（保留原有逻辑）"""
    init_db()
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    
    # 修复时区问题：使用本地时间而非UTC（根据需求调整）
    today_str = datetime.datetime.now().date().isoformat()
    visitor_id = get_visitor_id() # 调用新的Cookie版函数

    if "has_counted" not in st.session_state:
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

    # 读取统计数据
    c.execute("SELECT COUNT(*) FROM visitors WHERE last_visit_date=?", (today_str,))
    today_uv = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM visitors")
    total_uv = c.fetchone()[0]

    c.execute("SELECT pv_count FROM daily_traffic WHERE date=?", (today_str,))
    res_pv = c.fetchone()
    today_pv = res_pv[0] if res_pv else 0
    
    conn.close()
    return today_uv, total_uv, today_pv

# -------------------------- 页面展示（保留原有逻辑） --------------------------
try:
    today_uv, total_uv, today_pv = track_and_get_stats()
except Exception as e:
    st.error(f"统计模块出错: {e}")
    today_uv, total_uv, today_pv = 0, 0, 0

# CSS样式（保留）
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

# 展示数据（保留）
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
