import streamlit as st
import base64
import os
import json

st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音同步面板 (支援重複播放)")
st.write("目前狀態：🟢 支援相同語音重複播放（透過時間戳）")

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
    st.warning("⚠️ 系統未偵測到 Firebase 金鑰")

# 檔案名稱定義
model_filename = "robot.glb"
texture_normal = "idle.png"
texture_talking = "talk.png"

b64_normal = ""
b64_talking = ""

if os.path.exists(texture_normal):
    with open(texture_normal, "rb") as f:
        b64_normal = base64.b64encode(f.read()).decode()
if os.path.exists(texture_talking):
    with open(texture_talking, "rb") as f:
        b64_talking = base64.b64encode(f.read()).decode()

if os.path.exists(model_filename):
    with open(model_filename, "rb") as f:
        bytes_data = f.read()
    b64_model = base64.b64encode(bytes_data).decode()

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
        
        let lastPlayedTimestamp = 0;  // 記錄上次的時間戳

        unlockBtn.addEventListener("click", () => {
            isAudioUnlocked = true;
            unlockBtn.style.backgroundColor = "#555555";
            unlockBtn.innerText = "🟢 喇叭已解鎖！隨時等待外部資料庫傳入連續語音 🟢";
            statusDebug.innerText = "系統狀態: 喇叭已解鎖，即時監聽 Firebase 中...";
            
            let dummy = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA=");
            dummy.play().catch(e => console.log("預激活"));
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

                    // ========== 🔥 關鍵修改：處理兩種資料格式 ==========
                    let incomingAudioData = "";
                    let incomingTimestamp = 0;
                    
                    // 檢查是否是物件格式（包含 audio 和 timestamp）
                    if (typeof rawVal === 'object' && rawVal !== null) {
                        incomingAudioData = rawVal.audio || "";
                        incomingTimestamp = rawVal.timestamp || 0;
                        dataDebug.innerText = `📦 收到物件格式 | 時間戳: ${incomingTimestamp} | 音訊長度: ${incomingAudioData.length}`;
                    } else {
                        // 相容舊的純字串格式
                        incomingAudioData = rawVal.toString().trim();
                        incomingTimestamp = Date.now();
                        dataDebug.innerText = `📝 收到純文字格式 | 音訊長度: ${incomingAudioData.length}`;
                    }
                    // ==================================================
                    
                    incomingAudioData = incomingAudioData.toString().trim().replace(/^['"]|['"]$/g, '');
                    
                    let displayPrefix = incomingAudioData.substring(0, 50);
                    dataDebug.innerText += " | 開頭: " + displayPrefix + "...";

                    if (isFirstLoad) {
                        isFirstLoad = false;
                        lastPlayedTimestamp = incomingTimestamp;
                        statusDebug.innerText = "🟢 雲端同步完成！請嘗試更改 Firebase 資料庫觸發播音。";
                        return;
                    }
                    
                    if (incomingAudioData.length > 100) {
                        if (!isAudioUnlocked) {
                            statusDebug.innerText = "⚠️ 偵測到語音，但請先點選上方「綠色按鈕」解鎖喇叭！";
                            return;
                        }
                        
                        if (!incomingAudioData.startsWith("data:")) {
                            incomingAudioData = "data:audio/wav;base64," + incomingAudioData;
                        }
                        
                        // 中斷目前播放
                        if (currentAudio && !currentAudio.paused && !currentAudio.ended) {
                            currentAudio.pause();
                            currentAudio = null;
                        }
                        
                        lastPlayedTimestamp = incomingTimestamp;
                        playIncomingAudio(incomingAudioData);
                    } else {
                        statusDebug.innerText = "⚠️ 收到非音訊格式（字串過短），已略過。";
                    }
                });
            } catch(err) { statusDebug.innerText = "❌ Firebase 連線失敗: " + err.message; }
        }

        function playIncomingAudio(audioUrlStr) {
            try {
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

                currentAudio.addEventListener("error", () => {
                    safeApplyTexture(textureNormalObj);
                    statusDebug.innerText = "❌ 音訊解碼失敗。請確認寫入的 Base64 格式是否正確。";
                    currentAudio = null;
                });

                currentAudio.play().catch(err => {
                    safeApplyTexture(textureNormalObj);
                    statusDebug.innerText = "❌ 播放失敗: " + err.message;
                    currentAudio = null;
                });

            } catch (err) { console.error(err); }
        }
    </script>
    """

    html_code = raw_html.replace("__B64_MODEL__", b64_model)\
                        .replace("__B64_NORMAL__", b64_normal)\
                        .replace("__B64_TALKING__", b64_talking)\
                        .replace("__FB_CONFIG_JSON__", fb_config_json)
    
    st.components.v1.html(html_code, height=580)
    st.success("📡 語音串流看板已完全就緒！")
    
    # 顯示使用說明
    with st.expander("📖 如何讓相同語音重複播放"):
        st.markdown("""
        ### 🔥 現在支援兩種資料格式：
        
        **格式 1：純文字（相容舊版）**
        ```json
        test: "UklGRjSxAgBXQVZFZm10IB..."
