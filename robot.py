import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與基本樣式
st.set_page_config(page_title="🤖 機器人控制台", layout="centered")
st.title("🤖 我的面板機器人")
st.write("目前狀態：🟢 動力核心已啟動，正在透過指令強制執行補正。")

# --- 安全讀取 Firebase 金鑰 ---
firebase_secret_str = st.secrets.get("FIREBASE_KEY")

if firebase_secret_str:
    try:
        firebase_config = json.loads(firebase_secret_str)
        st.success("🟢 Firebase 安全金鑰已成功載入！")
    except Exception as e:
        st.error(f"❌ 金鑰格式解析失敗，請檢查 Secrets 設定。錯誤訊息: {e}")
else:
    st.warning("⚠️ 系統未偵測到環境變數中的 Firebase 金鑰，請確認 Secrets 設定是否正確。")
# ------------------------------

# 設定你的 3D 模型檔名
model_filename = "robot.glb"

# 2. 檢查 3D 檔案是否存在並讀取
if os.path.exists(model_filename):
    with open(model_filename, "rb") as f:
        bytes_data = f.read()
    b64_model = base64.b64encode(bytes_data).decode()

    # 3. 嵌入 Google 3D 渲染器（加入 id="my-robot" 與自動播放腳本）
    html_code = f"""
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    <div style="display: flex; justify-content: center; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 10px;">
        <model-viewer 
            id="my-robot"
            src="data:application/octet-stream;base64,{b64_model}" 
            alt="3D 機器人模型" 
            autoplay
            loop
            camera-controls 
            style="width: 100%; height: 500px;">
        </model-viewer>
    </div>

    <script>
        // 💥 強制核心：當 3D 模型載入完成後，用 JavaScript 灌入播放指令
        const modelViewer = document.querySelector("#my-robot");
        modelViewer.addEventListener("load", () => {{
            modelViewer.play();
        }});
    </script>
    """
    
    # 4. 畫出 3D 畫面並維持高度
    st.components.v1.html(html_code, height=530)
    st.success("🟢 網頁 3D 核心已與模型同步！")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
