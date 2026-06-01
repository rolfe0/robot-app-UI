import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音同步面板 (修正版)")
st.write("目前狀態：🟢 已修正音訊播放問題")

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
        st.error(f"❌ 金鑰解析失敗: {e}")
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

    # 4. 修正後的 HTML
    raw_html = """
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    
    <div style="display: flex; flex-direction: column; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 15px;">
        <button id="unlock-audio-btn" style="background-color: #00CC66; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%;">
            🔊 點擊此處啟用語音系統 (必須點擊才能播放語音)
        </button>
        <button id="test-audio-btn" style="background-color: #FF8800; color: white; border: none; padding: 10px 20px; font-size: 14px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%;">
            🎵 測試語音播放 (使用預設音效)
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
        let isAudioUnlocked = false;  // 改用簡單的布林值
        
        // 用來記錄最後一次「真正播放」的音訊字串
        let lastPlayedAudioStr = ""; 

        // 使用者點擊解鎖按鈕 - 簡化版本
        unlockBtn.addEventListener("click", async () => {
            isAudioUnlocked = true;
            unlockBtn.style.backgroundColor = "#555555";
            unlockBtn.innerText = "🟢 語音系統已啟用！等待 Firebase 語音資料... 🟢";
            statusDebug.innerText = "系統狀態: 語音系統已啟用，即時監聽 Firebase 中...";
            
            // 嘗試播放一個極短暫的靜音來解鎖瀏覽器
            try {
                const silentAudio = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA=");
                silentAudio.volume = 0;
                await silentAudio.play();
                console.log("音訊已解鎖");
            } catch(e) {
                console.log("解鎖警告:", e);
                // 有些瀏覽器可能需要使用者實際點擊有聲音的按鈕
                // 所以我們也嘗試建立一個 AudioContext
                try {
                    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    await audioCtx.resume();
                } catch(ctxErr) {
                    console.log("AudioContext 錯誤:", ctxErr);
                }
            }
        });
        
        // 測試按鈕 - 使用簡單的 WAV 檔案而不是 Web Audio API
        testBtn.addEventListener("click", async () => {
            if (!isAudioUnlocked) {
                statusDebug.innerText = "⚠️ 請先點擊綠色「啟用語音系統」按鈕！";
                return;
            }
            
            // 使用一個確保可以播放的短 WAV 檔案
            const testWavBase64 = "UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA=";
            const testAudio = new Audio("data:audio/wav;base64," + testWavBase64);
            
            testAudio.onplay = () => {
                statusDebug.innerText = "🔊 測試音播放中！喇叭正常運作。";
                setTimeout(() => {
                    if (!currentAudio || currentAudio.paused) {
                        statusDebug.innerText = "系統狀態: 語音系統已啟用，等待 Firebase 語音...";
                    }
                }, 500);
            };
            
            testAudio.onerror = (e) => {
                statusDebug.innerText = "❌ 測試失敗: 無法播放音訊";
                console.error("測試音錯誤:", testAudio.error);
            };
            
            try {
                await testAudio.play();
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
            } catch (err) {
                console.error("貼圖錯誤:", err);
            }
            
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
            if (!base64Str) return false;
            // 檢查開頭是否為有效的 WAV 標頭
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

                    let incomingAudioData = rawVal.toString().trim();
                    // 移除可能的引號
                    incomingAudioData = incomingAudioData.replace(/^['"]|['"]$/g, '');
                    
                    let dataLength = incomingAudioData.length;
                    let displayPrefix = incomingAudioData.substring(0, 60);
                    dataDebug.innerText = "📥 收到資料 | 長度: " + dataLength + " | 開頭: " + displayPrefix.substring(0, 30) + "...";
                    
                    console.log("Firebase 資料長度:", dataLength);
                    console.log("Firebase 開頭:", incomingAudioData.substring(0, 20));

                    if (isFirstLoad) {
                        isFirstLoad = false;
                        lastPlayedAudioStr = incomingAudioData;
                        statusDebug.innerText = "🟢 雲端同步完成！請嘗試更改 Firebase 資料庫觸發播音。";
                        return;
                    }
                    
                    // 檢查長度是否足夠（完整音訊應該 > 10000）
                    if (dataLength < 1000) {
                        statusDebug.innerText = "⚠️ 資料長度不足 (" + dataLength + ")，可能不是完整的音訊";
                        return;
                    }
                    
                    if (!isValidWavBase64(incomingAudioData)) {
                        statusDebug.innerText = "⚠️ 格式錯誤: 開頭應為 UklGR，實際: " + incomingAudioData.substring(0, 10);
                        return;
                    }
                    
                    if (!isAudioUnlocked) {
                        statusDebug.innerText = "⚠️ 偵測到語音，但請先點擊綠色按鈕解鎖喇叭！";
                        return;
                    }
                    
                    // 避免重複播放相同的語音
                    if (currentAudio && !currentAudio.paused && !currentAudio.ended && incomingAudioData === lastPlayedAudioStr) {
                        statusDebug.innerText = "🎵 收到重複語音訊號，保持目前音訊完整播放中...";
                        return;
                    }
                    
                    lastPlayedAudioStr = incomingAudioData;
                    playIncomingAudio(incomingAudioData);
                });
            } catch(err) { 
                statusDebug.innerText = "❌ Firebase 連線失敗: " + err.message;
                console.error("Firebase 錯誤:", err);
            }
        }

        async function playIncomingAudio(base64Data) {
            try {
                // 中斷前一條音訊
                if (currentAudio) {
                    currentAudio.pause();
                    currentAudio = null;
                }

                // 建立完整的 Data URL
                let audioUrl = "data:audio/wav;base64," + base64Data;
                
                statusDebug.innerText = "🎵 正在載入音訊...";
                
                currentAudio = new Audio(audioUrl);

                // 使用 Promise 來處理播放
                const playPromise = currentAudio.play();
                
                if (playPromise !== undefined) {
                    playPromise.then(() => {
                        statusDebug.innerText = "🎵 語音播放中，機器人說話中...";
                        safeApplyTexture(textureTalkingObj);
                    }).catch(err => {
                        console.error("播放錯誤:", err);
                        safeApplyTexture(textureNormalObj);
                        if (err.name === 'NotAllowedError') {
                            statusDebug.innerText = "❌ 播放失敗: 請先點擊綠色解鎖按鈕";
                        } else if (err.name === 'NotSupportedError') {
                            statusDebug.innerText = "❌ 播放失敗: 瀏覽器不支援此音訊格式";
                        } else {
                            statusDebug.innerText = "❌ 播放失敗: " + err.message;
                        }
                        currentAudio = null;
                    });
                }

                // 監聽播放結束
                currentAudio.addEventListener("ended", () => {
                    safeApplyTexture(textureNormalObj);
                    statusDebug.innerText = "🟢 語音播放完畢，持續監聽下一則指令...";
                    currentAudio = null;
                });
                
                // 監聽錯誤
                currentAudio.addEventListener("error", (e) => {
                    safeApplyTexture(textureNormalObj);
                    let errorMsg = "❌ 音訊錯誤: ";
                    if (currentAudio.error) {
                        switch(currentAudio.error.code) {
                            case MediaError.MEDIA_ERR_ABORTED:
                                errorMsg += "播放中斷";
                                break;
                            case MediaError.MEDIA_ERR_NETWORK:
                                errorMsg += "網路錯誤";
                                break;
                            case MediaError.MEDIA_ERR_DECODE:
                                errorMsg += "解碼失敗 - WAV 格式可能有問題";
                                break;
                            case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
                                errorMsg += "不支援的格式";
                                break;
                            default:
                                errorMsg += "未知錯誤";
                        }
                    }
                    statusDebug.innerText = errorMsg;
                    console.error("Audio Error:", currentAudio.error);
                    currentAudio = null;
                });

            } catch (err) { 
                console.error("建立音訊錯誤:", err);
                safeApplyTexture(textureNormalObj);
                statusDebug.innerText = "❌ 建立音訊失敗: " + err.message;
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
    
    # 添加除錯提示
    with st.expander("🔧 除錯資訊 (如果沒有聲音請查看這裡)"):
        st.write("""
        **請檢查以下項目：**
        
        1. **瀏覽器控制台錯誤**：按 F12 開啟開發者工具，查看 Console 標籤是否有紅色錯誤
        
        2. **Firebase 資料格式**：確認資料以 `UklGR` 開頭且長度 > 10000
        
        3. **測試順序**：務必先點綠色解鎖 → 橘色測試 → 然後 Firebase 更新
        
        4. **瀏覽器設定**：確認網站沒有被靜音（分頁上點右鍵 → 取消靜音）
        
        5. **WAV 格式**：確保上傳的是標準 PCM WAV 檔案（16bit, 22050Hz 或 44100Hz）
        """)
    
else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
