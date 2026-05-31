import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音與貼圖即時同步面板")
st.write("目前狀態：🟢 系統已進入【雲端監聽模式】。只要 Firebase 資料庫接收到語音，這裡就會自動發聲並切換口型。")

# --- 讀取 Firebase 秘密金鑰與設定變數 ---
firebase_secret_str = st.secrets.get("FIREBASE_KEY")
fb_config_json = "{}"

if firebase_secret_str:
    try:
        config_data = json.loads(firebase_secret_str)
        st.success("🟢 Firebase 雲端監聽核心已安全啟動！")
        
        fb_config_json = json.dumps({
            "apiKey": config_data.get("apiKey", ""),
            "authDomain": f"{config_data.get('project_id')}.firebaseapp.com",
            "databaseURL": f"https://{config_data.get('project_id')}-default-rtdb.firebaseio.com",
            "projectId": config_data.get("project_id"),
        })
    except Exception as e:
        st.error(f"❌ 金鑰解析失敗，請檢查 Settings 裡的 Secrets。")
else:
    st.warning("⚠️ 系統未偵測到環境變數中的 Firebase 金鑰。")
# ------------------------------

# 💥 精準鎖定你在 GitHub 上的貼圖真實檔名
model_filename = "robot.glb"
texture_normal = "idle.png"  # 已修正為你的檔名
texture_talking = "talk.png" # 已修正為你的檔名

# 2. 檢查並準備貼圖的 Base64 資料
b64_normal = ""
b64_talking = ""

if os.path.exists(texture_normal):
    with open(texture_normal, "rb") as f:
        b64_normal = base64.b64encode(f.read()).decode()
else:
    st.error(f"❌ 找不到待機貼圖【{texture_normal}】")

if os.path.exists(texture_talking):
    with open(texture_talking, "rb") as f:
        b64_talking = base64.b64encode(f.read()).decode()
else:
    st.error(f"❌ 找不到說話貼圖【{texture_talking}】")

# 3. 檢查 3D 檔案是否存在並讀取
if os.path.exists(model_filename):
    with open(model_filename, "rb") as f:
        bytes_data = f.read()
    b64_model = base64.b64encode(bytes_data).decode()

    # 4. 嵌入 3D 渲染器與 Firebase 即時監聽與語音切貼圖連動腳本
    html_code = f"""
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    
    <div style="display: flex; justify-content: center; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 10px;">
        <model-viewer 
            id="live-robot"
            src="data:application/octet-stream;base64,{b64_model}" 
            alt="3D 機器人模型" 
            camera-controls 
            autoplay
            loop
            time-scale="0.01"
            style="width: 100%; height: 500px;">
        </model-viewer>
    </div>

    <script>
        // 為了確保後續模組載入安全，我們把初始化都收進主要監聽邏輯中
        window.addEventListener("DOMContentLoaded", () => {{
            // 這裡保留空實作或基礎網頁追蹤
        }});
    </script>

    <script type="module">
        import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
        import {{ getDatabase, ref, onValue }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

        const modelViewer = document.querySelector("#live-robot");
        
        // 讀取正確的貼圖來源
        const imgNormalSrc = "data:image/png;base64,{b64_normal}";
        const imgTalkingSrc = "data:image/png;base64,{b64_talking}";
        
        let textureNormalObj = null;
        let textureTalkingObj = null;
        let isFirebaseInitialized = false;

        // 模型載入後，初始化動畫與預備貼圖物件
        modelViewer.addEventListener("load", async () => {{
            const anims = modelViewer.availableAnimations;
            let targetAnim = anims.find(name => name.toLowerCase().includes("mixamo.com.001")) ||
                             anims.
