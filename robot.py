import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音同步面板 (穩定說話貼圖版)")
st.write("目前狀態：🟢 已優化瀏覽器自動播放政策相容性！")

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

    # 4. 採用純字串定義 HTML
    raw_html = """
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    
    <div style="display: flex; flex-direction: column; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 15px;">
        <button id="unlock-audio-btn" style="background-color: #00CC66; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%;">
            🔊 點擊此處啟用語音系統 (必須點擊才能播放語音)
        </button>
        <button id="test-audio-btn" style="background-color: #FF8800; color: white; border: none; padding: 10px 20px; font-size: 14px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%;">
            🎵 測試語音播放 (檢查喇叭是否正常)
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
            <p id="status-debug" style="color: #00FF00; font-size: 13px; font-family: monospace; margin: 0;">系統狀態: 請點擊綠色按鈕啟用語音系統...</p>
            <p id="data-debug" style="color: #FFCC00; font-size: 12px; font-family: monospace; margin: 5px 0 0 0; word-break: break-all;">Firebase 監聽狀態: 等待連線中...</p>
        </div>
    </div>

    <script type="module">
        import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
        import { getDatabase, ref, onValue } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

        const modelViewer = document.querySelector("#live-robot");
        const unlockBtn = document.querySelector("#unlock-audio-btn");
        const testBtn = document.querySelector("#test-audio-btn");
        const statusDebug = document.querySelector("#status-debug");
        const dataDebug = document.querySelector("#data-debug");
        
        const imgNormalUrl = "data:image/png;base64,__B64_NORMAL__";
        const imgTalkingUrl = "data:image/png;base64,__B64_TALKING__";
        
        let isFirebaseInitialized = false;
        let textureNormalObj = null;
        let textureTalkingObj = null;

        let currentAudio = null;
        let isAudioContextReady = false;  // 追蹤音訊系統是否已啟用
        
        // 用來記錄最後一次「真正播放」的音訊字串
        let lastPlayedAudioStr = ""; 

        // 創建一個隱藏的 AudioContext 來"解鎖"瀏覽器的音訊系統
        let audioContext = null;
        
        // 初始化音訊上下文 (必須在使用者點擊後才能建立)
        function initAudioContext() {
            if (audioContext) return;
            try {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                // 建立一個空的、無聲的 GainNode 來激活音訊系統
                const emptySource = audioContext.createBufferSource();
                const emptyBuffer = audioContext.createBuffer(1, 1, 22050);
                emptySource.buffer = emptyBuffer;
                emptySource.connect(audioContext.destination);
                emptySource.start();
                // 不要立即 resume，讓後續的 play 觸發
                console.log("AudioContext 已建立");
            } catch(e) {
                console.error("建立 AudioContext 失敗:", e);
            }
        }
        
        // 真正的音訊解鎖函數
        async function unlockAudio() {
            if (isAudioContextReady) return true;
            
            try {
                if (audioContext && audioContext.state === 'suspended') {
                    await audioContext.resume();
                }
                isAudioContextReady = true;
                return true;
            } catch(e) {
                console.error("解鎖音訊失敗:", e);
                return false;
            }
        }

        // 使用者點擊解鎖按鈕
        unlockBtn.addEventListener("click", async () => {
            // 建立 AudioContext
            initAudioContext();
            
            // 嘗試播放一個極短暫的靜音來解鎖
            const silentAudio = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA=");
            silentAudio.volume = 0;  // 靜音
            await silentAudio.play().catch(e => console.log("預激活靜音:", e));
            
            // 解鎖 AudioContext
            const unlocked = await unlockAudio();
            
            if (unlocked) {
                unlockBtn.style.backgroundColor = "#555555";
                unlockBtn.innerText = "🟢 語音系統已啟用！等待 Firebase 語音資料... 🟢";
                statusDebug.innerText = "系統狀態: 語音系統已啟用，即時監聽 Firebase 中...";
                isAudioContextReady = true;
            } else {
                statusDebug.innerText = "⚠️ 語音系統啟用失敗，請再次點擊按鈕";
            }
        });
        
        // 測試按鈕：播放一個簡單的提示音來確認音訊可用
        testBtn.addEventListener("click", async () => {
            if (!isAudioContextReady) {
                statusDebug.innerText = "⚠️ 請先點擊綠色「啟用語音系統」按鈕！";
                return;
            }
            
            // 建立一個簡單的嗶嗶聲 (使用 Web Audio API 產生，不依賴外部檔案)
            try {
                if (audioContext && audioContext.state === 'suspended') {
                    await audioContext.resume();
                }
                
                const testCtx = audioContext || new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = testCtx.createOscillator();
                const gain = testCtx.createGain();
                oscillator.connect(gain);
                gain.connect(testCtx.destination);
                oscillator.type = 'sine';
                oscillator.frequency.value = 880;
                gain.gain.value = 0.3;
                oscillator.start();
                gain.gain.exponentialRampToValueAtTime(0.00001, testCtx.currentTime + 0.5);
                oscillator.stop(testCtx.currentTime + 0.5);
                
                statusDebug.innerText = "🔊 測試音播放中！喇叭正常運作。";
                setTimeout(() => {
                    if (!currentAudio || currentAudio.paused) {
                        statusDebug.innerText = "系統狀態: 語音系統已啟用，等待 Firebase 語音...";
                    }
                }, 1000);
            } catch(e) {
                statusDebug.innerText = "❌ 測試失敗: " + e.message;
            }
        });

        modelViewer.addEventListener("load", async () => {
            try {
                const anims = modelViewer.availableAnimations;
                let targetAnim = anims.find(name => name.toLowerCase().includes("mixamo.com.001")) ||
                                 anims.find(name => name.toLowerCase().includes("armature.001")) ||
                                 anims[0];
                if (targetAnim) {
                    modelViewer.animationName = targetAnim;
                    setTimeout(() => { modelViewer.play(); }, 100);
                }
            } catch (e) { }

            try {
                if (modelViewer.model && modelViewer.model.materials.length > 0) {
                    textureNormalObj = await modelViewer.createTexture(imgNormalUrl);
                    textureTalkingObj = await modelViewer.createTexture(imgTalkingUrl);
                    safeApplyTexture(textureNormalObj); 
                }
            } catch (err) {}
            
            if (!isFirebaseInitialized) {
                startFirebaseListener();
                isFirebaseInitialized = true;
            }
        });

        function safeApplyTexture(targetTexture) {
            if (!targetTexture || !modelViewer.model || !modelViewer.model.materials) return;
            modelViewer.model.materials.forEach(mat => {
                try {
                    if (mat && mat.pbrMetallicRoughness && mat.pbrMetallicRoughness.baseColorTexture) {
                        mat.pbrMetallicRoughness.baseColorTexture.setTexture(targetTexture);
                    }
                } catch(e) { }
            });
        }

        // 驗證 Base64 是否為有效的 WAV 格式
        function isValidWavBase64(base64Str) {
            return base64Str && (base64Str.startsWith('UklGR') || base64Str.startsWith('RIFF'));
        }

        function startFirebaseListener() {
            const firebaseConfig = __FB_CONFIG_JSON__;
            if (!firebaseConfig.databaseURL) {
                statusDebug.innerText = "❌ 錯誤: 找不到 Firebase 資料庫配置！";
                return;
            }

            try {
                const app = initializeApp(firebaseConfig);
                const database = getDatabase(app);
                const voiceRef = ref(database, 'test');

                let isFirstLoad = true;

                onValue(voiceRef, (snapshot) => {
                    let rawVal = snapshot.val();
                    if (!rawVal) {
                        dataDebug.innerText = "Firebase 狀態: 目前 'test' 欄位為空值 (null)";
                        return;
                    }

                    let incomingAudioData = rawVal.toString().trim().replace(/^['"]|['"]$/g, '');
                    
                    let displayPrefix = incomingAudioData.substring(0, 60);
                    dataDebug.innerText = "最新收到資料開頭: " + displayPrefix + "... (長度: " + incomingAudioData.length + ")";

                    if (isFirstLoad) {
                        isFirstLoad = false;
                        lastPlayedAudioStr = incomingAudioData;
                        statusDebug.innerText = "🟢 雲端同步完成！請嘗試更改 Firebase 資料庫觸發播音。";
                        return;
                    }
                    
                    if (incomingAudioData.length > 100 && isValidWavBase64(incomingAudioData)) {
                        if (!isAudioContextReady) {
                            statusDebug.innerText = "⚠️ 偵測到語音，但請先點擊綠色「啟用語音系統」按鈕解鎖喇叭！";
                            return;
                        }
                        
                        // 確保 AudioContext 已恢復
                        if (audioContext && audioContext.state === 'suspended') {
                            audioContext.resume().catch(e => console.log("resume 失敗:", e));
                        }
                        
                        let audioUrl;
                        if (incomingAudioData.startsWith("data:audio/")) {
                            audioUrl = incomingAudioData;
                        } else {
                            audioUrl = "data:audio/wav;base64," + incomingAudioData;
                        }
                        
                        if (currentAudio && !currentAudio.paused && !currentAudio.ended && incomingAudioData === lastPlayedAudioStr) {
                            statusDebug.innerText = "🎵 收到重複語音訊號，保持目前音訊完整播放中...";
                            return;
                        }
                        
                        lastPlayedAudioStr = incomingAudioData;
                        playIncomingAudio(audioUrl);
                    } else {
                        statusDebug.innerText = "⚠️ 收到非標準 WAV 格式，開頭: " + incomingAudioData.substring(0, 20);
                    }
                });
            } catch(err) { 
                statusDebug.innerText = "❌ Firebase 連線失敗: " + err.message;
            }
        }

        async function playIncomingAudio(audioUrlStr) {
            try {
                if (currentAudio) {
                    currentAudio.pause();
                    currentAudio = null;
                }

                // 確保音訊系統已解鎖
                if (audioContext && audioContext.state === 'suspended') {
                    await audioContext.resume();
                }

                currentAudio = new Audio(audioUrlStr);

                currentAudio.addEventListener("play", () => {
                    statusDebug.innerText = "🎵 雲端連續語音同步播放中，機器人說話中...";
                    safeApplyTexture(textureTalkingObj);
                });

                currentAudio.addEventListener("ended", () => {
                    safeApplyTexture(textureNormalObj);
                    statusDebug.innerText = "🟢 當前語音播放完畢，持續監聽下一則指令...";
                    currentAudio = null;
                });

                currentAudio.addEventListener("error", (e) => {
                    safeApplyTexture(textureNormalObj);
                    let errorMsg = "❌ 音訊解碼失敗。";
                    if (currentAudio.error) {
                        switch(currentAudio.error.code) {
                            case 1: errorMsg += " 用戶端中止。"; break;
                            case 2: errorMsg += " 網路錯誤。"; break;
                            case 3: errorMsg += " 解碼失敗，可能 Base64 資料損毀。"; break;
                            case 4: errorMsg += " 不支援的格式。"; break;
                            default: errorMsg += " 未知錯誤。";
                        }
                    }
                    statusDebug.innerText = errorMsg;
                    currentAudio = null;
                });

                // 重要：使用 await 處理 play 的 Promise
                await currentAudio.play();
                
            } catch (err) { 
                console.error("Play Error:", err);
                safeApplyTexture(textureNormalObj);
                if (err.name === 'NotAllowedError') {
                    statusDebug.innerText = "❌ 播放失敗: 瀏覽器自動播放政策限制。請點擊綠色按鈕重新啟用語音系統。";
                } else {
                    statusDebug.innerText = "❌ 播放失敗: " + err.message;
                }
                currentAudio = null;
            }
        }
    </script>
    """

    # 5. 安全替換標籤
    html_code = raw_html.replace("__B64_MODEL__", b64_model)\
                        .replace("__B64_NORMAL__", b64_normal)\
                        .replace("__B64_TALKING__", b64_talking)\
                        .replace("__FB_CONFIG_JSON__", fb_config_json)
    
    st.components.v1.html(html_code, height=620)
    st.success("📡 終極連續語音串流看板已完全就緒！")
    st.info("💡 **使用說明**：\n\n1️⃣ 先點擊綠色「啟用語音系統」按鈕解鎖瀏覽器音訊\n\n2️⃣ 點擊橘色「測試語音播放」確認喇叭正常\n\n3️⃣ 然後 Firebase 的語音資料就會自動播放")
else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
