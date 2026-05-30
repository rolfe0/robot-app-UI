import streamlit as st
import streamlit.components.v1 as components
import base64
import os
from dotenv import load_dotenv  # 新增：導入讀取 .env 的套件

# 自動尋找並讀取專案目錄下的 .env 檔案
load_dotenv()

# 從環境變數中安全地取得密鑰（"DISCORD_TOKEN" 需與你 .env 檔案中的設定一致）
bot_token = os.getenv("DISCORD_TOKEN")

# 1. 設定網頁標題
st.set_page_config(page_title="🤖 機器人控制台", layout="centered")
st.title("🤖 我的面板機器人")
st.write("目前狀態：🟢 待機動作播放中，已停用自動旋轉。")

# --- 安全檢查：確保密鑰有被正確讀取 ---
if not bot_token:
    st.warning("⚠️ 系統未偵測到環境變數中的密鑰，請確認 .env 檔案設定是否正確。")
else:
    # 這裡可以放你需要用到 bot_token 的功能，例如啟動背景機器人
    pass
# ------------------------------------

# 設定你的 3D 模型檔名
model_filename = "robot.glb"

# 2. 檢查檔案是否存在並讀取
if os.path.exists(model_filename):
    with open(model_filename, "rb") as f:
        bytes_data = f.read()
    b64_model = base64.b64encode(bytes_data).decode()

    # 3. 嵌入 Google 3D 渲染器
    html_code = f"""
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    <div style="display: flex; justify-content: center;">
        <model-viewer 
            src="data:application/octet-stream;base64,{b64_model}" 
            alt="3D 機器人模型" 
            autoplay
            camera-controls 
            style="width: 100%; height: 500px; background-color: #1E1E24; border-radius: 15px; box-shadow: 0px 4px 12px rgba(0,0,0,0.3);">
        </model-viewer>
    </div>
    """
# 將 3D 畫面畫在網頁上
    components.html(html_code, height=530)
    st.success("🟢 網頁已成功同步！")
else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
