import streamlit as st
import base64
import os
import json

st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音同步面板 (修正重複播放版)")
st.write("目前狀態：🟢 修正刪除後再次輸入相同語音無法播放的問題")

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
        import { getDatabase, ref, onValue, set } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

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
        
        let database = null;
        let voiceRef = null;
        let isPlaying = false;
        
        // 🔥 移除 isFirstLoad 機制，改用記錄上次播放的資料
        let lastPlayedData = null;

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

        async function deleteFirebaseData() {
            if (!voiceRef) return;
            try {
                await set(voiceRef, null);
                console.log("✅ Firebase 資料已刪除");
                dataDebug.innerText = "🗑️ 資料已自動刪除 | 可以再次輸入相同語音";
            } catch(e) {
                console.error("刪除失敗:", e);
            }
        }

        function startFirebaseListener() {
            const firebaseConfig = __FB_CONFIG_JSON__;
            if (!firebaseConfig.databaseURL) {
                statusDebug.innerText = "❌ 錯誤: 找不到 Firebase 資料庫配置！";
                return;
            }

            try {
                const app = initializeApp(firebaseConfig);
                database = getDatabase(app);
                voiceRef = ref(database, 'test');

                // 🔥 關鍵修正：每次都處理，不跳過第一次
                onValue(voiceRef, (snapshot) => {
                    let rawVal = snapshot.val();
                    
                    // 顯示當前資料狀態
                    if (!rawVal) {
                        dataDebug.innerText = "📭 Firebase 狀態: test 欄位為空 (null) - 等待輸入";
                        return;
                    }

                    let incomingAudioData = "";
                    
                    // 支援物件格式或純文字格式
                    if (typeof rawVal === 'object' && rawVal !== null) {
                        incomingAudioData = rawVal.audio || "";
                        dataDebug.innerText = "📦 收到物件 | 長度: " + incomingAudioData.length;
                    } else {
                        incomingAudioData = rawVal.toString().trim();
                        dataDebug.innerText = "📝 收到文字 | 長度: " + incomingAudioData.length;
                    }
                    
                    incomingAudioData = incomingAudioData.toString().trim().replace(/^['"]|['"]$/g, '');
                    
                    dataDebug.innerText += " | 開頭: " + incomingAudioData.substring(0, 40) + "...";
                    
                    // 🔥 重要：檢查是否是有效音訊（長度 > 100）
                    if (incomingAudioData.length < 100) {
                        statusDebug.innerText = "⚠️ 資料長度不足 (" + incomingAudioData.length + ")，不是完整音訊";
                        return;
                    }
                    
                    if (!isAudioUnlocked) {
                        statusDebug.innerText = "⚠️ 偵測到語音，但請先點擊綠色按鈕解鎖喇叭！";
                        return;
                    }
                    
                    // 如果正在播放中，先中斷
                    if (isPlaying && currentAudio) {
                        statusDebug.innerText = "⏸️ 中斷目前播放，播放新語音...";
                        currentAudio.pause();
                        currentAudio = null;
                        isPlaying = false;
                    }
                    
                    if (!incomingAudioData.startsWith("data:")) {
                        incomingAudioData = "data:audio/wav;base64," + incomingAudioData;
                    }
                    
                    // 🔥 記錄播放的資料
                    lastPlayedData = incomingAudioData;
                    playIncomingAudio(incomingAudioData);
                });
            } catch(err) { 
                statusDebug.innerText = "❌ Firebase 連線失敗: " + err.message;
                console.error(err);
            }
        }

        function playIncomingAudio(audioUrlStr) {
            try {
                currentAudio = new Audio(audioUrlStr);
                isPlaying = true;

                currentAudio.addEventListener("play", () => {
                    statusDebug.innerText = "🎵 語音播放中，機器人說話中...";
                    safeApplyTexture(textureTalkingObj);
                });

                currentAudio.addEventListener("ended", async () => {
                    safeApplyTexture(textureNormalObj);
                    statusDebug.innerText = "🟢 語音播放完畢，正在刪除 Firebase 資料...";
                    isPlaying = false;
                    currentAudio = null;
                    
                    // 🔥 播放完成後刪除 Firebase 資料
                    await deleteFirebaseData();
                    statusDebug.innerText = "🟢 就緒，可以再次輸入相同語音";
                });

                currentAudio.addEventListener("error", async (e) => {
                    safeApplyTexture(textureNormalObj);
                    let errorMsg = "❌ 音訊錯誤";
                    if (currentAudio.error) {
                        switch(currentAudio.error.code) {
                            case 1: errorMsg = "❌ 播放中斷"; break;
                            case 2: errorMsg = "❌ 網路錯誤"; break;
                            case 3: errorMsg = "❌ 解碼失敗 - Base64 可能損毀"; break;
                            case 4: errorMsg = "❌ 不支援的格式"; break;
                        }
                    }
                    statusDebug.innerText = errorMsg;
                    isPlaying = false;
                    currentAudio = null;
                    
                    await deleteFirebaseData();
                });

                currentAudio.play().catch(async (err) => {
                    safeApplyTexture(textureNormalObj);
                    statusDebug.innerText = "❌ 播放失敗: " + err.message;
                    isPlaying = false;
                    currentAudio = null;
                    
                    await deleteFirebaseData();
                });

            } catch (err) { 
                console.error(err);
                isPlaying = false;
            }
        }
    </script>
    """

    html_code = raw_html.replace("__B64_MODEL__", b64_model)
    html_code = html_code.replace("__B64_NORMAL__", b64_normal)
    html_code = html_code.replace("__B64_TALKING__", b64_talking)
    html_code = html_code.replace("__FB_CONFIG_JSON__", fb_config_json)
    
    st.components.v1.html(html_code, height=600)
    st.success("📡 語音串流看板已完全就緒！")
    
    st.info("""
    💡 **修正說明**：
    
    - ✅ 移除了 `isFirstLoad` 機制，現在**每次** Firebase 有資料都會播放
    - ✅ 語音播放完成後自動刪除資料
    - ✅ 刪除後可以**重複輸入相同的語音**
    
    **測試流程**：
    1. 點擊綠色按鈕解鎖
    2. 寫入語音到 Firebase → 播放
    3. 播放完成 → 自動刪除（顯示 null）
    4. **再次寫入相同的語音** → 再次播放 ✅
    """)
    
else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
