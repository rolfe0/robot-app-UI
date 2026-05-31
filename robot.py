import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音與材質變體同步面板")
st.write("目前狀態：🟢 採用官方安全材質變體機制。請修改 Firebase 的 test 欄位進行測試。")

# --- 讀取 Firebase 秘密金鑰 ---
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

# 貼圖與模型檔名
model_filename = "robot.glb"
texture_normal = "idle.png"
texture_talking = "talk.png"

# 2. 檢查並準備貼圖的 Base64 資料
b64_normal = ""
b64_talking = ""

if os.path.exists(texture_normal):
    with open(texture_normal, "rb") as f:
        b64_normal = base64.b64encode(f.read()).decode()
if os.path.exists(texture_talking):
    with open(texture_talking, "rb") as f:
        b64_talking = base64.b64encode(f.read()).decode()

# 3. 檢查 3D 檔案是否存在並讀取
if os.path.exists(model_filename):
    with open(model_filename, "rb") as f:
        bytes_data = f.read()
    b64_model = base64.b64encode(bytes_data).decode()

    # 4. 嵌入 3D 渲染器與連動腳本
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

    <script type="module">
        import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
        import {{ getDatabase, ref, onValue }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

        const modelViewer = document.querySelector("#live-robot");
        
        const imgNormalUrl = "data:image/png;base64,{b64_normal}";
        const imgTalkingUrl = "data:image/png;base64,{b64_talking}";
        
        let isFirebaseInitialized = false;

        // 建立快取物件，避開不相容的材質屬性尋找
        let textureNormalObj = null;
        let textureTalkingObj = null;

        modelViewer.addEventListener("load", async () => {{
            // 1. 動態安全啟動
            try {{
                const anims = modelViewer.availableAnimations;
                let targetAnim = anims.find(name => name.toLowerCase().includes("mixamo.com.001")) ||
                                 anims.find(name => name.toLowerCase().includes("armature.001")) ||
                                 anims[0];
                if (
