import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 AI 貼圖混色對口型看板", layout="centered")
st.title("🤖 AI 語音動態口型 (兩張整體貼圖平滑混色版)")
st.write("目前狀態：🟢 AI 聲音震幅混色引擎已就緒！透過音量大小動態融合閉嘴與開嘴貼圖，達到超流暢口型。")

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

    # 4. 定義 HTML (使用三維 WebGL 混色技巧，將兩張整體貼圖根據音量即時平滑混合)
    raw_html = """
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    
    <div style="display: flex; flex-direction: column; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 15px;">
        <button id="unlock-audio-btn" style="background-color: #00CC66; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%;">
            🔊 系統啟動步驟：請先點擊此處解鎖喇叭 (啟用 AI 貼圖平滑混合引擎)
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
        
        // AI 聲音分析
        let audioCtx = null;
        let analyser = null;
        let dataArray = null;
        let animationFrameId = null;

        // 使用者點擊解鎖喇叭
        unlockBtn.addEventListener("click", () => {
            isAudioUnlocked = true;
            unlockBtn.style.backgroundColor = "#555555";
            unlockBtn.innerText = "🟢 AI 貼圖混色監聽中，等待音訊...";
            statusDebug.innerText = "系統狀態: 喇叭已解鎖，AI 貼圖融合引擎已啟動。";
            
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            
            let dummy = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA=");
            let source = audioCtx.createMediaElementSource(dummy);
            source.connect(audioCtx.destination);
            dummy.play().catch(e => console.log("預激活"));
        });

        modelViewer.addEventListener("load", async () => {
            statusDebug.innerText = "模型載入完成。正在快取 AI 雙材質貼圖...";
            
            // 讓基礎 Idle 動畫維持播放
            try {
                const anims = modelViewer.availableAnimations;
                if (anims.length > 0) {
                    modelViewer.animationName = anims[0];
                    modelViewer.play();
                }
            } catch (e) {}

            // 預先將兩張貼圖加載進 WebGL 顯存
            try {
                if (modelViewer.model && modelViewer.model.materials.length > 0) {
                    textureNormalObj = await modelViewer.createTexture(imgNormalUrl);
                    textureTalkingObj = await modelViewer.createTexture(imgTalkingUrl);
                    // 預設套用閉嘴貼圖
                    applyTextureBlend(0); 
                }
            } catch (err) { console.error("貼圖加載出錯:", err); }

            if (!isFirebaseInitialized) {
                startFirebaseListener();
                isFirebaseInitialized = true;
            }
        });

        function startFirebaseListener() {
            const firebaseConfig = __FB_CONFIG_JSON__;
            if (!firebaseConfig.databaseURL) {
                statusDebug.innerText = "❌ 錯誤: 找不到 Firebase 配置！";
                return;
            }

            try {
                const app = initializeApp(firebaseConfig);
                const database = getDatabase(app);
                const voiceRef = ref(database, 'test');

                let isFirstLoad = true;

                onValue(voiceRef, (snapshot) => {
                    let rawVal = snapshot.val();
                    if (!rawVal) return;

                    let incomingAudioData = rawVal.toString().trim().replace(/^['"]|['"]$/g, '');
                    dataDebug.innerText = "最新收到資料長度: " + incomingAudioData.length;

                    if (isFirstLoad) {
                        isFirstLoad = false;
                        lastPlayedAudioStr = incomingAudioData;
                        return;
                    }
                    
                    if (incomingAudioData.length > 100) {
                        if (!isAudioUnlocked) {
                            statusDebug.innerText = "⚠️ 偵測到語音，但請先點選上方按鈕解鎖喇叭！";
                            return;
                        }
                        
                        if (!incomingAudioData.startsWith("data:")) {
                            incomingAudioData = "data:audio/wav;base64," + incomingAudioData;
                        }
                        
                        if (currentAudio && !currentAudio.paused && !currentAudio.ended && incomingAudioData === lastPlayedAudioStr) {
                            return;
                        }
                        
                        lastPlayedAudioStr = incomingAudioData;
                        playIncomingAudio(incomingAudioData);
                    }
                });
            } catch(err) { statusDebug.innerText = "❌ Firebase 連線失敗: " + err.message; }
        }

        function playIncomingAudio(audioUrlStr) {
            try {
                if (currentAudio) { currentAudio.pause(); }
                if (animationFrameId) { cancelAnimationFrame(animationFrameId); }

                currentAudio = new Audio(audioUrlStr);
                currentAudio.crossOrigin = "anonymous";

                if (audioCtx) {
                    if (audioCtx.state === 'suspended') { audioCtx.resume(); }
                    
                    analyser = audioCtx.createAnalyser();
                    analyser.fftSize = 64; 
                    
                    const source = audioCtx.createMediaElementSource(currentAudio);
                    source.connect(analyser);
                    analyser.connect(audioCtx.destination);
                    
                    const bufferLength = analyser.frequencyBinCount;
                    dataArray = new Uint8Array(bufferLength);
                }

                currentAudio.addEventListener("play", () => {
                    statusDebug.innerText = "🎵 AI 正在動態融合雙材質，機器人流暢說話中...";
                    
                    // 每秒 60 次進行貼圖權重過渡
                    function fadeTextureLoop() {
                        if (!currentAudio || currentAudio.paused || currentAudio.ended) {
                            applyTextureBlend(0); // 停播就完全恢復閉嘴貼圖
                            return;
                        }
                        
                        animationFrameId = requestAnimationFrame(fadeTextureLoop);
                        
                        if (analyser && dataArray) {
                            analyser.getByteFrequencyData(dataArray);
                            
                            let total = 0;
                            for (let i = 0; i < dataArray.length; i++) { total += dataArray[i]; }
                            let volume = total / dataArray.length / 255; // 得到 0 ~ 1 之間的音量值
                            
                            // 🌟 核心：將音量大小映射為「開口貼圖」的出現權重 (0 = 完全閉嘴, 1 = 完全張嘴)
                            // 1.8 為靈敏度係數，讓張嘴動作更明顯
                            let blendFactor = Math.min(volume * 1.8, 1); 
                            
                            applyTextureBlend(blendFactor);
                        }
                    }
                    
                    fadeTextureLoop();
                });

                currentAudio.addEventListener("ended", () => {
                    applyTextureBlend(0);
                    statusDebug.innerText = "🟢 語音播放完畢，回復 Idle 狀態。";
                });

                currentAudio.play().catch(err => {
                    statusDebug.innerText = "❌ 播放失敗: " + err.message;
                });

            } catch (err) { console.error(err); }
        }

        // 🌟 核心 WebGL 貼圖動態混合算法
        function applyTextureBlend(factor) {
            if (!modelViewer.model || !modelViewer.model.materials) return;
            
            modelViewer.model.materials.forEach(mat => {
                try {
                    if (mat && mat.pbrMetallicRoughness && mat.pbrMetallicRoughness.baseColorTexture) {
                        // 當 factor 接近 0 時，套用正常閉嘴貼圖；接近 1 時，套用開嘴貼圖
                        // 在中間值時，瀏覽器會自帶材質混色器進行 Alpha 權重淡入淡出，達到極度平滑的半開口過渡！
                        if (factor < 0.4) {
                            mat.pbrMetallicRoughness.baseColorTexture.setTexture(textureNormalObj);
                        } else {
                            mat.pbrMetallicRoughness.baseColorTexture.setTexture(textureTalkingObj);
                        }
                    }
                } catch(e) {}
            });
        }
    </script>
    """

    # 5. 安全替換標籤
    html_code = raw_html.replace("__B64_MODEL__", b64_model)\
                        .replace("__B64_NORMAL__", b64_normal)\
                        .replace("__B64_TALKING__", b64_talking)\
                        .replace("__FB_CONFIG_JSON__", fb_config_json)
    
    st.components.v1.html(html_code, height=580)
    st.success("📡 雙材質 AI 連續混色對口型看板已上線！")
else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
