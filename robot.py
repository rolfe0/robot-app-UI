import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題
st.set_page_config(page_title="🤖 機器人控制台", layout="centered")
st.title("🤖 我的面板機器人")
st.write("目前狀態：🟢 待機動作播放中，已停用自動旋轉。")

# --- 安全讀取 Firebase 金鑰 ---
firebase_secret_str = st.secrets.get("FIREBASE_KEY")

if firebase_secret_str:
    try:
        # 將字串安全轉換成 Python 字典，供你的 Firebase 程式後續使用
        firebase_config = json.loads(firebase_secret_str)
        st.success("🟢 Firebase 安全金鑰已成功載入！")
    except Exception as e:
        st.error(f"❌ 金鑰格式解析失敗，請檢查 Secrets 設定。錯誤訊息: {e}")
else:
    st.warning("⚠️ 系統未偵測到環境變數中的 Firebase 金鑰，請確認 Secrets 設定是否正確。")
# ------------------------------

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
    
    # 將 3D 畫面畫在網頁上（改用 2026/06/01 官方推薦的新版 st.iframe 寫法）
    b64_html = base64.b64encode(html_code.encode()).decode()
    st.iframe(f"data:text/html;base64,{b64_html}", height=530)
    st.success("🟢 網頁已成功同步！")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
