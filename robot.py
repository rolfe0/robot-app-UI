import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 AI 語音口型與動畫看板", layout="centered")
st.title("🤖 AI 語音動態口型 (待機動畫+雙材質融合版)")
st.write("目前狀態：🟢 連續監聽與動畫修復核心已就緒！已徹底根治待機動作卡死的 Bug。")

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

# 2. 檢查並讀取兩張整體貼圖
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

    # 4. 定義 HTML
    raw_html = """
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    
    <div style="display: flex; flex-direction: column; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 15px;">
        <button id="unlock-audio-btn" style="background-color: #00CC66; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%;">
            🔊 系統啟動步驟：請先點擊此處解鎖喇叭 (啟用待機動作與語音引擎)
        </button>

        <model-viewer 
            id="live-robot"
            src="data:application/octet-stream;base64,__B64_MODEL__" 
            alt="3D AI模型" 
            camera-controls
            autoplay
            loop
            style="width: 100%; height: 450px;">
        </model-viewer>
        
        <div style="background-color: #000000; width: 100%; padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #444;">
            <p id="status-debug" style="color: #00FF00; font-size: 13px; font-family: monospace; margin: 0;">系統狀態: 等待點擊綠色按鈕解鎖...</p>
            <p id="data-debug" style="color: #FFCC00; font-size: 12px; font-family: monospace; margin: 5px 0 0 0; word-break: break-all;">Firebase 監聽狀態: 等待連線中...</p>
        </div>
    </div>

    <script type="module">
        import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
        import { getDatabase, ref, onValue } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

        const modelViewer = document.querySelector("#live-robot");
        const unlockBtn = document.querySelector("#unlock-audio-btn");
        const statusDebug = document.querySelector("#status-debug");
        const dataDebug = document.querySelector("#data-debug");
        
        const imgNormalUrl = "data:image/png;base64,__B64_NORMAL__";
        const imgTalkingUrl = "data:image/png;base64,__B64_TALKING__";
        
        let isFirebaseInitialized = false;
        let currentAudio = null;
        let isAudioUnlocked = false;
        let lastPlayedAudioStr = ""; 
        
        // 貼圖物件快取
        let textureNormalObj = null;
        let textureTalkingObj = null;
        
        // 🌟 新增狀態鎖：用來阻止 WebGL 重複綁定材質導致動畫卡死
        let currentActiveFace = ""; 
        
        // AI 聲音分析
        let audioCtx = null;
        let analyser = null;
        let dataArray = null;
        let animationFrameId = null;

        // 使用者點擊解鎖喇叭
        unlockBtn.addEventListener("click", () => {
            isAudioUnlocked = true;
            unlockBtn.style.backgroundColor = "#555
