import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音同步面板 (穩定說話貼圖版)")
st.write("目前狀態：🟢 連續監聽優化核心已就緒！說話時將固定顯示說話貼圖，不再閃爍。")

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
            🔊 系統啟動步驟：請先點擊此處解鎖喇叭 (只需點一次，即可連續接收語音)
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
        
        // 用來記錄最後一次「真正播放」的音訊字串
        let lastPlayedAudioStr = ""; 

        // 使用者點擊解鎖喇叭通道
        unlockBtn.addEventListener("click", () => {
            isAudioUnlocked = true;
            unlockBtn.style.backgroundColor = "#555555";
            unlockBtn.innerText = "🟢 喇叭已解鎖！隨時等待外部資料庫傳入連續語音 🟢";
            statusDebug.innerText = "系統狀態: 喇叭已解鎖，即時監聽 Firebase 中...";
            
            // 預激活音訊上下文
            let dummy = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA=");
            dummy.play().catch(e => console.log("預激活:", e));
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
            // WAV 檔案的標頭通常是 "UklGR" (RIFF 格式)
            return base64Str.startsWith('UklGR') || base64Str.startsWith('RIFF');
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

                    // 強制轉字串並清洗
                    let incomingAudioData = rawVal.toString().trim().replace(/^['"]|['"]$/g, '');
                    
                    // 顯示收到的原始資料開頭（用於除錯）
                    let displayPrefix = incomingAudioData.substring(0, 60);
                    dataDebug.innerText = "最新收到資料開頭: " + displayPrefix + "... (長度: " + incomingAudioData.length + ")";

                    // 第一次載入如果是網頁開啟前的舊資料，更新狀態後略過不播
                    if (isFirstLoad) {
                        isFirstLoad = false;
                        lastPlayedAudioStr = incomingAudioData;
                        statusDebug.innerText = "🟢 雲端同步完成！請嘗試更改 Firebase 資料庫觸發播音。";
                        return;
                    }
                    
                    // 檢查是否為有效的音訊資料（至少要夠長）
                    if (incomingAudioData.length > 100 && isValidWavBase64(incomingAudioData)) {
                        if (!isAudioUnlocked) {
                            statusDebug.innerText = "⚠️ 偵測到語音，但請先點選上方「綠色按鈕」解鎖喇叭！";
                            return;
                        }
                        
                        // 確保有正確的 data URL 前綴
                        let audioUrl;
                        if (incomingAudioData.startsWith("data:audio/")) {
                            audioUrl = incomingAudioData;
                        } else if (incomingAudioData.startsWith("http") || incomingAudioData.startsWith("blob:")) {
                            audioUrl = incomingAudioData;
                        } else {
                            // 假設是純 Base64，加上 WAV 的 MIME 類型
                            audioUrl = "data:audio/wav;base64," + incomingAudioData;
                        }
                        
                        statusDebug.innerText = "🎵 準備播放語音，資料長度: " + incomingAudioData.length;
                        
                        // 避免重複播放相同的語音
                        if (currentAudio && !currentAudio.paused && !currentAudio.ended && incomingAudioData === lastPlayedAudioStr) {
                            statusDebug.innerText = "🎵 收到重複語音訊號，保持目前音訊完整播放中...";
                            return;
                        }
                        
                        lastPlayedAudioStr = incomingAudioData;
                        playIncomingAudio(audioUrl);
                    } else {
                        statusDebug.innerText = "⚠️ 收到非標準 WAV 格式（開頭不是 UklGR 或 RIFF），請確認 Firebase 存入的是完整 WAV Base64 字串";
                        console.log("無效格式，開頭:", incomingAudioData.substring(0, 20));
                    }
                });
            } catch(err) { 
                statusDebug.innerText = "❌ Firebase 連線失敗: " + err.message;
                console.error(err);
            }
        }

        function playIncomingAudio(audioUrlStr) {
            try {
                // 中斷前一條音訊
                if (currentAudio) {
                    currentAudio.pause();
                    currentAudio = null;
                }

                currentAudio = new Audio(audioUrlStr);

                // 播放開始時：固定套用說話貼圖
                currentAudio.addEventListener("play", () => {
                    statusDebug.innerText = "🎵 雲端連續語音同步播放中，機器人說話中...";
                    safeApplyTexture(textureTalkingObj);
                });

                // 播放結束時：恢復一般貼圖
                currentAudio.addEventListener("ended", () => {
                    safeApplyTexture(textureNormalObj);
                    statusDebug.innerText = "🟢 當前語音播放完畢，持續監聽下一則指令...";
                    currentAudio = null;
                });

                // 播放錯誤時：恢復一般貼圖並顯示詳細錯誤
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
                    statusDebug.innerText = errorMsg + " 請檢查 Firebase 中的資料是否為完整 WAV Base64 字串。";
                    console.error("Audio Error:", currentAudio.error);
                    currentAudio = null;
                });

                const playPromise = currentAudio.play();
                if (playPromise !== undefined) {
                    playPromise.catch(err => {
                        safeApplyTexture(textureNormalObj);
                        statusDebug.innerText = "❌ 播放失敗: " + err.message + " (可能是瀏覽器自動播放政策)";
                        console.error("Play Error:", err);
                        currentAudio = null;
                    });
                }

            } catch (err) { 
                console.error(err);
                statusDebug.innerText = "❌ 建立音訊物件失敗: " + err.message;
            }
        }
    </script>
    """

    # 5. 安全替換標籤
    html_code = raw_html.replace("__B64_MODEL__", b64_model)\
                        .replace("__B64_NORMAL__", b64_normal)\
                        .replace("__B64_TALKING__", b64_talking)\
                        .replace("__FB_CONFIG_JSON__", fb_config_json)
    
    st.components.v1.html(html_code, height=580)
    st.success("📡 終極連續語音串流看板已完全就緒！(說話時不閃爍，固定顯示說話貼圖)")
    st.info("💡 提示：請確保 Firebase 中的 'test' 欄位存的是完整 WAV 檔案的 Base64 編碼字串（以 'UklGR' 開頭）")
else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
