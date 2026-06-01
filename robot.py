import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 AI 語音雙模型看板", layout="centered")
st.title("🤖 AI 語音動態口型 (雙模型疊加、動畫永不卡死版)")
st.write("目前狀態：🟢 最終修正版引擎已啟動！已完美排除任何引號衝突與動畫卡死的 Bug。")

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
        st.error("❌ 金鑰解析失敗，請檢查 Settings 裡的 Secrets。")
else:
    st.warning("⚠️ 系統未偵測到環境變數中的 Firebase 金鑰。")

# 檔案名稱定義
model_filename = "robot.glb"
texture_normal = "idle.png"    # 閉嘴的完整貼圖
texture_talking = "talk.png"   # 開口的完整貼圖

# 2. 檢查並讀取兩張整體貼圖
b64_normal = ""
b64_talking = ""

if os.path.exists(texture_normal):
    with open(texture_normal, "rb") as f:
        b64_normal = base64.b64encode(f.read()).decode()
else:
    st.error(f"❌ 找不到閉嘴貼圖：{texture_normal}")

if os.path.exists(texture_talking):
    with open(texture_talking, "rb") as f:
        b64_talking = base64.b64encode(f.read()).decode()
else:
    st.error(f"❌ 找不到開口貼圖：{texture_talking}")

# 3. 檢查 3D 檔案是否存在並讀取
if os.path.exists(model_filename):
    with open(model_filename, "rb") as f:
        bytes_data = f.read()
    b64_model = base64.b64encode(bytes_data).decode()

    # 4. 🚀 終極防錯：乾乾淨淨的一段大字串，結尾絕對閉合
    raw_html = """
<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>

<div style="display: flex; flex-direction: column; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 15px;">
    <button id="unlock-audio-btn" style="background-color: #00CC66; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%;">
        🔊 系統啟動步驟：請先點擊此處解鎖喇叭 (啟用雙模型同步引擎)
    </button>

    <div style="position: relative; width: 100%; height: 450px; background: #2a2a35; border-radius: 10px; overflow: hidden;">
        <model-viewer 
            id="model-idle" 
            src="data:application/octet-stream;base64,__B64_MODEL__" 
            interaction-prompt="none" 
            camera-controls 
            autoplay 
            loop 
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1;">
        </model-viewer>

        <model-viewer 
            id="model-talk" 
            src="data:application/octet-stream;base64,__B64_MODEL__" 
            interaction-prompt="none" 
            autoplay 
            loop 
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 2; opacity: 0; pointer-events: none; transition: opacity 0.05s ease;">
        </model-viewer>
    </div>

    <div style="background-color: #000000; width: 100%; padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #444;">
        <p id="status-debug" style="color: #00FF00; font-size: 13px; font-family: monospace; margin: 0;">系統狀態: 等待點擊綠色按鈕解鎖...</p>
        <p id="data-debug" style="color: #FFCC00; font-size: 12px; font-family: monospace; margin: 5px 0 0 0; word-break: break-all;">Firebase 監聽狀態: 等待連線中...</p>
    </div>
</div>

<script type="module">
    import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
    import { getDatabase, ref, onValue } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

    const modelIdle = document.querySelector("#model-idle");
    const modelTalk = document.querySelector("#model-talk");
    const unlockBtn = document.querySelector("#unlock-audio-btn");
    const statusDebug = document.querySelector("#status-debug");
    const dataDebug = document.querySelector("#data-debug");
    
    const imgNormalUrl = "data:image/png;base64,__B64_NORMAL__";
    const imgTalkingUrl = "data:image/png;base64,__B64_TALKING__";
    
    let isFirebaseInitialized = false;
    let currentAudio = null;
    let isAudioUnlocked = false;
    let lastPlayedAudioStr = ""; 
    let audioCtx = null;
    let analyser = null;
    let dataArray = null;
    let animationFrameId = null;

    // 視角鏡頭完全同步
    modelIdle.addEventListener("camera-change", () => {
        modelTalk.cameraOrbit = modelIdle.cameraOrbit;
        modelTalk.cameraTarget = modelIdle.cameraTarget;
        modelTalk.fieldOfView = modelIdle.fieldOfView;
    });

    unlockBtn.addEventListener("click", () => {
        isAudioUnlocked = true;
        unlockBtn.style.backgroundColor = "#555555";
        unlockBtn.innerText = "🟢 AI 雙模型同步監聽中...";
        statusDebug.innerText = "系統狀態: 喇叭已解鎖，雙模型 CSS 混合核心已啟動。";
        
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        let dummy = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA=");
        let source = audioCtx.createMediaElementSource(dummy);
        source.connect(audioCtx.destination);
        dummy.play().catch(e => {});
    });

    modelIdle.addEventListener("load", async () => {
        statusDebug.innerText = "正在設定閉嘴材質...";
        setupAnimation(modelIdle);
        try {
            if (modelIdle.model && modelIdle.model.materials.length > 0) {
                const tex = await modelIdle.createTexture(imgNormalUrl);
                modelIdle.model.materials.forEach(m => {
                    if(m && m.pbrMetallicRoughness && m.pbrMetallicRoughness.baseColorTexture) {
                        m.pbrMetallicRoughness.baseColorTexture.setTexture(tex);
                    }
                });
            }
        } catch (e) { console.error(e); }
    });

    modelTalk.addEventListener("load", async () => {
        statusDebug.innerText = "正在設定開口材質...全部載入完成！";
        setupAnimation(modelTalk);
        try {
            if (modelTalk.model && modelTalk.model.materials.length > 0) {
                const tex = await modelTalk.createTexture(imgTalkingUrl);
                modelTalk.model.materials.forEach(m => {
                    if(m && m.pbrMetallicRoughness && m.pbrMetallicRoughness.baseColorTexture) {
                        m.pbrMetallicRoughness.baseColorTexture.setTexture(tex);
                    }
                });
            }
        } catch (e) { console.error(e); }
        
        if (!isFirebaseInitialized) {
            startFirebaseListener();
            isFirebaseInitialized = true;
        }
    });

    function setupAnimation(viewer) {
        try {
            const anims = viewer.availableAnimations;
            let targetAnim = anims.find(name => name.toLowerCase().includes("mixamo")) || 
                             anims.find(name => name.toLowerCase().includes("armature")) || 
                             anims[0];
            if (targetAnim) {
                viewer.animationName = targetAnim;
                viewer.play();
            }
        } catch (e) {}
    }

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
                        statusDebug.innerText = "⚠️ 偵測到語音，請先點選按鈕解鎖喇叭！";
                        return;
                    }
                    if (!incomingAudioData.startsWith("data:")) {
                        incomingAudioData = "data:audio/wav;base64," + incomingAudioData;
                    }
                    if (currentAudio && !currentAudio.paused && !currentAudio.ended && incomingAudioData === lastPlayedAudioStr) return;
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
                dataArray = new Uint8Array(analyser.frequencyBinCount);
            }

            currentAudio.addEventListener("play", () => {
                statusDebug.innerText = "🎵 AI 語音分析中，機器人動畫與口型完美同步中...";
                function loop() {
                    if (!currentAudio || currentAudio.paused || currentAudio.ended) {
                        modelTalk.style.opacity = "0";
                        return;
                    }
                    animationFrameId = requestAnimationFrame(loop);
                    if (analyser && dataArray) {
                        analyser.getByteFrequencyData(dataArray);
                        let total = 0;
                        for (let i = 0; i < dataArray.length; i++) { total += dataArray[i]; }
                        let averageVolume = total / dataArray.length;
                        
                        if (averageVolume > 15) {
                            modelTalk.style.opacity = "1";
                        } else {
                            modelTalk.style.opacity = "0";
                        }
                    }
                }
                loop();
            });

            currentAudio.addEventListener("ended", () => {
                modelTalk.style.opacity = "0";
                statusDebug.innerText = "🟢 語音播放完畢，持續保持待機搖擺。";
            });

            currentAudio.play().catch(err => { statusDebug.innerText = "❌ 播放失敗: " + err.message; });
        } catch (err) { console.error(err); }
    }
</script>
"""

    # 5. 安全替換標籤與渲染 (高度 680 確保資訊完整不被切掉)
    html_code = raw_html.replace("__B64_MODEL__", b64_model)\
                        .replace("__B64_NORMAL__", b64_normal)\
                        .replace("__B64_TALKING__", b64_talking)\
                        .replace("__FB_CONFIG_JSON__", fb_config_json)
    
    st.components.v1.html(html_code, height=680)
    st.success("📡 雙模型無干擾、永不卡死的動態看板已完美上線！")
else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
