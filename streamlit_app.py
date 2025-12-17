import streamlit as st
import datetime
import uuid
import urllib.parse

# --- 权限配置 ---
FREE_PERIOD_SECONDS = 60      # 免费试用期 60 秒
ACCESS_DURATION_HOURS = 24    # 密码解锁后的访问时长 24 小时
UNLOCK_CODE = "vip24"        # 预设的解锁密码
# --- 配置结束 ---

# -------------------------------------------------------------
# --- 核心修复：纯内存+URL参数实现状态持久化（无数据库） ---
# -------------------------------------------------------------
def get_visitor_id():
    """从URL参数获取/生成访客ID（唯一标识用户）"""
    # 读取URL参数
    query_params = st.query_params
    visitor_id = query_params.get("vid", [None])[0]
    
    # 无ID则生成并写入URL
    if not visitor_id:
        visitor_id = str(uuid.uuid4())[:8]  # 缩短ID，更友好
        st.query_params["vid"] = visitor_id
    
    return visitor_id

# 获取访客ID
visitor_id = get_visitor_id()

# 初始化会话状态（按访客ID隔离）
state_key_prefix = f"visitor_{visitor_id}_"

# 初始化免费期开始时间
if f"{state_key_prefix}start_time" not in st.session_state:
    st.session_state[f"{state_key_prefix}start_time"] = datetime.datetime.now()

# 初始化访问状态
if f"{state_key_prefix}access_status" not in st.session_state:
    st.session_state[f"{state_key_prefix}access_status"] = "free"

# 初始化解锁时间
if f"{state_key_prefix}unlock_time" not in st.session_state:
    st.session_state[f"{state_key_prefix}unlock_time"] = None

# -------------------------------------------------------------
# --- 访问状态检查逻辑 ---
# -------------------------------------------------------------
current_time = datetime.datetime.now()
access_granted = False
time_left = 0

# 读取当前访客的状态
access_status = st.session_state[f"{state_key_prefix}access_status"]
start_time = st.session_state[f"{state_key_prefix}start_time"]
unlock_time = st.session_state[f"{state_key_prefix}unlock_time"]

# 免费期逻辑
if access_status == "free":
    try:
        time_elapsed = (current_time - start_time).total_seconds()
        if time_elapsed < FREE_PERIOD_SECONDS:
            access_granted = True
            time_left = FREE_PERIOD_SECONDS - time_elapsed
            st.info(f"⏳ **免费试用中... 剩余 {time_left:.1f} 秒。**")
        else:
            # 免费期结束，锁定
            st.session_state[f"{state_key_prefix}access_status"] = "locked"
            st.rerun()
    except Exception as e:
        st.error(f"计时出错: {str(e)[:50]}")
        access_granted = False

# 解锁后逻辑
elif access_status == "unlocked":
    try:
        unlock_expiry = unlock_time + datetime.timedelta(hours=ACCESS_DURATION_HOURS)
        if current_time < unlock_expiry:
            access_granted = True
            delta = unlock_expiry - current_time
            hours = int(delta.total_seconds() // 3600)
            minutes = int((delta.total_seconds() % 3600) // 60)
            st.info(f"🔓 **付费权限剩余: {hours} 小时 {minutes} 分钟**")
        else:
            # 解锁过期，锁定
            st.session_state[f"{state_key_prefix}access_status"] = "locked"
            st.rerun()
    except Exception as e:
        st.error(f"解锁状态检查出错: {str(e)[:50]}")
        access_granted = False

# -------------------------------------------------------------
# --- 锁定界面 ---
# -------------------------------------------------------------
if not access_granted:
    st.error("🔒 **访问受限。免费试用期已结束！**")
    st.markdown("""
    <div style="background-color: #fff; padding: 15px; border-radius: 8px; border: 1px solid #e5e7eb; margin-top: 15px;">
        <p style="font-weight: 600; color: #1f2937; margin-bottom: 5px;">🔑 10元解锁无限制访问权限，获取代码链接 (请在微信中打开)</p>
        <p style="font-size: 0.9em; background-color: #eef2ff; padding: 8px; border-radius: 4px; overflow-wrap: break-word;">
            <code>#小程序://闲鱼/i4ahD0rqwGB5lba</code>
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("unlock_form"):
        pwd = st.text_input("输入解锁代码", type="password")
        submit = st.form_submit_button("验证解锁")
        
        if submit:
            if pwd == UNLOCK_CODE:
                # 解锁成功，更新状态
                st.session_state[f"{state_key_prefix}access_status"] = "unlocked"
                st.session_state[f"{state_key_prefix}unlock_time"] = datetime.datetime.now()
                st.success("🎉 解锁成功！页面即将刷新...")
                st.rerun()
            else:
                st.error("❌ 解锁代码错误，请重试！")
    
    st.stop()

# -------------------------------------------------------------
# --- 简化版统计（仅会话内有效，无数据库） ---
# -------------------------------------------------------------
# 初始化统计状态
if "pv_count" not in st.session_state:
    st.session_state.pv_count = 0
if "uv_count" not in st.session_state:
    st.session_state.uv_count = 1  # 当前访客计1个UV

# 仅首次加载计数
if "counted" not in st.session_state:
    st.session_state.pv_count += 1
    st.session_state.counted = True

# 今日UV/总UV（简化：仅当前会话）
today_uv = st.session_state.uv_count
total_uv = st.session_state.uv_count
today_pv = st.session_state.pv_count

# -------------------------------------------------------------
# --- 页面展示 ---
# -------------------------------------------------------------
st.title("🎈 My new app")
st.write("Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/).")

# CSS样式
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
    .metric-sub {
        font-size: 0.9rem;
        color: #212529;
    }
</style>
""", unsafe_allow_html=True)

# 展示统计数据
st.markdown(f"""
<div class="metric-container">
    <div class="metric-box">
        <div class="metric-sub">今日 UV: {today_uv} 访客数</div>
    </div>
    <div class="metric-box" style="border-left: 1px solid #dee2e6; border-right: 1px solid #dee2e6; padding: 0 20px;">
        <div class="metric-sub">历史总 UV: {total_uv} 总独立访客</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 自动刷新倒计时
if access_status == "free" and access_granted:
    st.markdown('<meta http-equiv="refresh" content="1">', unsafe_allow_html=True)
