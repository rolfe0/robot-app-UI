import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音同步面板 (遠端音訊串流版)")
st.write("目前狀態：🟢 連線機制已修復！網頁載入後，請在網頁任意空白處「點擊滑鼠一下」以啟用聲音。")

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

# 檔案名稱定義
model_filename = "robot.glb"
texture_normal = "idle.png"
texture_talking = "talk.png"

# 2. 檢查並準備貼圖
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

    # 4. 嵌入 3D 渲染器與音訊連動腳本
    html_code = f"""
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    
    <div id="click-zone" style="display: flex; flex-direction: column; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 15px; cursor: pointer;">
        <p id="unlock-tip" style="color: #00CC66; font-size: 16px; margin-bottom: 10px; font-weight: bold; text-align: center;">
            ⚠️ 【測試前提示】請先在下方機器人區域「點擊滑鼠任意處」啟用音效！
        </p>

        <model-viewer 
            id="live-robot"
            src="data:application/octet-stream;base64,{b64_model}" 
            alt="3D 機器人模型" 
            camera-controls 
            autoplay
            loop
            style="width: 100%; height: 450px;">
        </model-viewer>
        
        <p id="status-debug" style="color: #AAAAAA; font-size: 14px; margin-top: 10px; font-family: monospace; text-align: center;">系統狀態: 等待點擊解鎖音訊...</p>
    </div>

    <script type="module">
        import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
        import {{ getDatabase, ref, onValue }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

        const modelViewer = document.querySelector("#live-robot");
        const clickZone = document.querySelector("#click-zone");
        const statusDebug = document.querySelector("#status-debug");
        const unlockTip = document.querySelector("#unlock-tip");
        
        const imgNormalUrl = "data:image/png;base64,{b64_normal}";
        const imgTalkingUrl = "data:image/png;base64,{b64_talking}";
        
        let isFirebaseInitialized = false;
        let textureNormalObj = null;
        let textureTalkingObj = null;

        let mouthTimer = null; 
        let globalAudio = new Audio(); 
        let isAudioUnlocked = false;

        // 🛠️ 全螢幕/區域點擊解鎖：使用者只要碰一下網頁，立刻解鎖喇叭
        clickZone.addEventListener("click", () => {{
            if (isAudioUnlocked) return;
            
            // 播放極短的空白音訊來激活
            globalAudio.src = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA=";
            globalAudio.play().then(() => {{
                isAudioUnlocked = true;
                unlockTip.innerHTML = "🟢 喇叭通道已開啟！請去 Firebase 更改資料庫進行測試";
                unlockTip.style.color = "#888888";
                statusDebug.innerText = "系統狀態: 喇叭已解鎖，正在即時監聽 Firebase...";
            }}).catch(err => {{
                statusDebug.innerText = "❌ 喇叭解鎖失敗: " + err.message;
            }});
        }});

        modelViewer.addEventListener("load", async () => {{
            try {{
                const anims = modelViewer.availableAnimations;
                let targetAnim = anims.find(name => name.toLowerCase().includes("mixamo.com.001")) ||
                                 anims.find(name => name.toLowerCase().includes("armature.001")) ||
                                 anims[0];
                if (targetAnim) {{
                    modelViewer.animationName = targetAnim
