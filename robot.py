import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音同步面板 (防閃爍張嘴穩定版)")
st.write("目前狀態：🟢 連續監聽核心已就緒！修正為說話時維持張嘴、不閃爍。")

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

# 2. 健壯的檔案讀取機制
def get_file_b64(filepath):
    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

b64_normal = get_file_b64(texture_normal) or ""
b64_talking = get_file_b64(texture_talking) or ""
b64_model = get_file_b64(model_filename)

if not b64_model:
    st.error(f"❌ 找不到模型檔案：{model_filename}。請檢查檔案是否已上傳到 GitHub 對應目錄。")
    st.stop() # 停止執行，避免後續報錯

# 3. 採用純字串定義 HTML
raw_html = """
<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>

<div style="display: flex; flex-direction: column; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 15px;">
    <button id="unlock-audio-btn" style="background-color: #00CC66; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%;">
        🔊 系統啟動步驟：請先點擊此處解鎖喇叭
    </button>

    <model-viewer 
        id="live-robot"
        src="data:application/octet-stream;base64,__B64_MODEL__" 
        alt="3D 機器人模型" 
        camera-controls 
        autoplay
        loop
        style="width: 100%; height: 420px;">
    </model-viewer>
    
    <div style="background-color: #000000; width: 100%; padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #444;">
        <p id="status-debug" style="color: #00FF00; font-size: 13px; font-family: monospace; margin: 0;">系統狀態: 等待點擊綠色按鈕解鎖音訊...</p>
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
    let textureNormalObj = null;
    let textureTalkingObj = null;
    let currentAudio = null;
    let isAudioUnlocked = false;
    let lastPlayedAudioStr = ""; 

    unlockBtn.addEventListener("click", () => {
        isAudioUnlocked = true;
        unlockBtn.style.backgroundColor = "#555555";
        unlockBtn.innerText = "🟢 喇叭已解鎖！等待指令...";
        statusDebug.innerText = "系統狀態: 喇叭已解鎖，即時監聽 Firebase 中...";
        let dummy = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA=");
        dummy.play().catch(e => {});
    });

    modelViewer.addEventListener("load", async () => {
        try {
            const anims = modelViewer.availableAnimations;
            let targetAnim = anims.find(name => name.toLowerCase().includes("mixamo")) || anims[0];
            if (targetAnim) {
                modelViewer.animationName = targetAnim;
                modelViewer.play();
            }
            textureNormalObj = await modelViewer.createTexture(imgNormalUrl);
            textureTalkingObj = await modelViewer.createTexture(imgTalkingUrl);
            safeApplyTexture(textureNormalObj);
        } catch (e) { }
        
        if (!isFirebaseInitialized) {
            startFirebaseListener();
            isFirebaseInitialized = true;
        }
    });

    function safeApplyTexture(targetTexture) {
        if (!targetTexture || !modelViewer.model) return;
        modelViewer.model.materials.forEach(mat => {
            if (mat.pbrMetallicRoughness && mat.pbrMetallicRoughness.baseColorTexture) {
                mat.pbrMetallicRoughness.baseColorTexture.setTexture(targetTexture);
            }
        });
    }

    function startFirebaseListener() {
        const firebaseConfig = __FB_CONFIG_JSON__;
        const app = initializeApp(firebaseConfig);
        const database = getDatabase(app);
        const voiceRef = ref(database, 'test');
        let isFirstLoad = true;

        onValue(voiceRef, (snapshot) => {
            let rawVal = snapshot.val();
            if (!rawVal) return;
            let incomingAudioData = rawVal.toString().trim().replace(/^['"]|['"]$/g, '');
            
            if (isFirstLoad) { isFirstLoad = false; lastPlayedAudioStr = incomingAudioData; return; }
            
            if (incomingAudioData.length > 100 && isAudioUnlocked) {
                if (!incomingAudioData.startsWith("data:")) incomingAudioData = "data:audio/wav;base64," + incomingAudioData;
                if (incomingAudioData !== lastPlayedAudioStr) {
                    lastPlayedAudioStr = incomingAudioData;
                    playIncomingAudio(incomingAudioData);
                }
            }
        });
    }

    function playIncomingAudio(audioUrlStr) {
        if (currentAudio) currentAudio.pause();
        currentAudio = new Audio(audioUrlStr);
        currentAudio.addEventListener("play", () => {
            statusDebug.innerText = "🎵 說話中 (張嘴)...";
            safeApplyTexture(textureTalkingObj);
        });
        currentAudio.addEventListener("ended", () => {
            statusDebug.innerText = "🟢 語音結束 (閉嘴)";
            safeApplyTexture(textureNormalObj);
        });
        currentAudio.play().catch(err => { statusDebug.innerText = "❌ 播放失敗"; });
    }
</script>
"""

# 4. 安全替換標籤
html_code = raw_html.replace("__B64_MODEL__", b64_model)\
                    .replace("__B64_NORMAL__", b64_normal)\
                    .replace("__B64_TALKING__", b64_talking)\
                    .replace("__FB_CONFIG_JSON__", fb_config_json)

st.components.v1.html(html_code, height=680)
st.success("📡 系統已成功載入並監聽 Firebase！")
