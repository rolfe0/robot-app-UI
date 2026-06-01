import streamlit as st
import base64
import os
import json

st.set_page_config(page_title="🤖 AI 語音雙圖切換看板", layout="centered")
st.title("🤖 AI 語音動態口型 (雙整體貼圖精準切換版)")
st.write("目前狀態：🟢 雙圖精準切換引擎已啟動！當聲音響起時，會直接將模型材質替換成開口貼圖檔案。")

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

model_filename = "robot.glb"
texture_normal = "idle.png"
texture_talking = "talk.png"

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

if os.path.exists(model_filename):
    with open(model_filename, "rb") as f:
        bytes_data = f.read()
    b64_model = base64.b64encode(bytes_data).decode()

    html_parts = []
    html_parts.append('<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>')
    html_parts.append('<div style="display: flex; flex-direction: column; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 15px;">')
    html_parts.append('<button id="unlock-audio-btn" style="background-color: #00CC66; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%;">🔊 系統啟動步驟：請先點擊此處解鎖喇叭 (啟用雙圖切換引擎)</button>')
    html_parts.append('<model-viewer id="live-robot" src="data:application/octet-stream;base64,MODEL_PLACEHOLDER" alt="3D AI模型" camera-controls autoplay loop style="width: 100%; height: 450px;"></model-viewer>')
    html_parts.append('<div style="background-color: #000000; width: 100%; padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #444;">')
    html_parts.append('<p id="status-debug" style="color: #00FF00; font-size: 13px; font-family: monospace; margin: 0;">系統狀態: 等待點擊綠色按鈕解鎖...</p>')
    html_parts.append('<p id="data-debug" style="color: #FFCC00; font-size: 12px; font-family: monospace; margin: 5px 0 0 0; word-break: break-all;">Firebase 監聽狀態: 等待連線中...</p>')
    html_parts.append('</div>')
    html_parts.append('</div>')

    js_code = '''
<script type="module">
    import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
    import { getDatabase, ref, onValue } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

    const modelViewer = document.querySelector("#live-robot");
    const unlockBtn = document.querySelector("#unlock-audio-btn");
    const statusDebug = document.querySelector("#status-debug");
    const dataDebug = document.querySelector("#data-debug");

    const imgNormalUrl = "data:image/png;base64,NORMAL_PLACEHOLDER";
    const imgTalkingUrl = "data:image/png;base64,TALKING_PLACEHOLDER";

    let isFirebaseInitialized = false, currentAudio = null, isAudioUnlocked = false, lastPlayedAudioStr = "";
    let textureNormalObj = null, textureTalkingObj = null, currentActiveFace = "";
    let audioCtx = null, analyser = null, dataArray = null, animationFrameId = null;

    unlockBtn.addEventListener("click", () => {
        isAudioUnlocked = true;
        unlockBtn.style.backgroundColor = "#555555";
        unlockBtn.innerText = "🟢 AI 雙圖監聽引擎已啟動，等待音訊...";
        statusDebug.innerText = "系統狀態: 喇叭已解鎖，正在接收語音並切換材質。";
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        let dummy = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA=");
        let source = audioCtx.createMediaElementSource(dummy);
        source.connect(audioCtx.destination);
        dummy.play().catch(e => console.log("預激活"));
    });

    modelViewer.addEventListener("load", async () => {
        statusDebug.innerText = "模型載入完成。正在快取雙貼圖檔案...";
        try {
            const anims = modelViewer.availableAnimations;
            let targetAnim = anims.find(name => name.toLowerCase().includes("mixamo")) || anims[0];
            if (targetAnim) { modelViewer.animationName = targetAnim; modelViewer.play(); }
        } catch (e) {}
        try {
            if (modelViewer.model && modelViewer.model.materials.length > 0) {
                textureNormalObj = await modelViewer.createTexture(imgNormalUrl);
                textureTalkingObj = await modelViewer.createTexture(imgTalkingUrl);
                forceApplyTexture("NORMAL");
            }
        } catch (err) { console.error(err); }
        if (!isFirebaseInitialized) { startFirebaseListener(); isFirebaseInitialized = true; }
    });

    function startFirebaseListener() {
        const firebaseConfig = FB_CONFIG_PLACEHOLDER;
        if (!firebaseConfig.databaseURL) { statusDebug.innerText = "❌ 錯誤: 找不到 Firebase 配置！"; return; }
        try {
            const app = initializeApp(firebaseConfig);
            const database = getDatabase(app);
            const voiceRef = ref(database, "test");
            let isFirstLoad = true;
            onValue(voiceRef, (snapshot) => {
                let rawVal = snapshot.val();
                if (!rawVal) return;
                let incomingAudioData = rawVal.toString().trim().replace(/^[\'"]|[\'"]$/g, "");
                dataDebug.innerText = "最新收到資料長度: " + incomingAudioData.length;
                if (isFirstLoad) { isFirstLoad = false; lastPlayedAudioStr = incomingAudioData; return; }
                if (incomingAudioData.length > 100) {
                    if (!isAudioUnlocked) { statusDebug.innerText = "⚠️ 偵測到語音，請先點選上方按鈕解鎖喇叭！"; return; }
                    if (!incomingAudioData.startsWith("data:")) { incomingAudioData = "data:audio/wav;base64," + incomingAudioData; }
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
                if (audioCtx.state === "suspended") { audioCtx.resume(); }
                analyser = audioCtx.createAnalyser();
                analyser.fftSize = 64;
                const source = audioCtx.createMediaElementSource(currentAudio);
                source.connect(analyser);
                analyser.connect(audioCtx.destination);
                dataArray = new Uint8Array(analyser.frequencyBinCount);
            }
            currentAudio.addEventListener("play", () => {
                statusDebug.innerText = "🎵 AI 正在根據聲音即時切換整體貼圖檔案...";
                function loop() {
                    if (!currentAudio || currentAudio.paused || currentAudio.ended) { forceApplyTexture("NORMAL"); return; }
                    animationFrameId = requestAnimationFrame(loop);
                    if (analyser && dataArray) {
                        analyser.getByteFrequencyData(dataArray);
                        let total = 0;
                        for (let i = 0; i < dataArray.length; i++) { total += dataArray[i]; }
                        let averageVolume = total / dataArray.length;
                        if (averageVolume > 15) { forceApplyTexture("TALK"); } else { forceApplyTexture("NORMAL"); }
                    }
                }
                loop();
            });
            currentAudio.addEventListener("ended", () => {
                forceApplyTexture("NORMAL");
                statusDebug.innerText = "🟢 語音播放完畢，已恢復閉嘴待機貼圖。";
            });
            currentAudio.play().catch(err => { statusDebug.innerText = "❌ 播放失敗: " + err.message; });
        } catch (err) { console.error(err); }
    }

    function forceApplyTexture(faceType) {
        if (!modelViewer.model || !modelViewer.model.materials) return;
        if (currentActiveFace === faceType) return;
        currentActiveFace = faceType;
        let targetTextureObj = (faceType === "NORMAL") ? textureNormalObj : textureTalkingObj;
        modelViewer.model.materials.forEach(mat => {
            try {
                if (mat && mat.pbrMetallicRoughness && mat.pbrMetallicRoughness.baseColorTexture) {
                    mat.pbrMetallicRoughness.baseColorTexture.setTexture(targetTextureObj);
                }
            } catch(e) {}
        });
    }
</script>
'''

    html_code = "".join(html_parts) + js_code
    html_code = html_code.replace("MODEL_PLACEHOLDER", b64_model)
    html_code = html_code.replace("NORMAL_PLACEHOLDER", b64_normal)
    html_code = html_code.replace("TALKING_PLACEHOLDER", b64_talking)
    html_code = html_code.replace("FB_CONFIG_PLACEHOLDER", fb_config_json)

    st.components.v1.html(html_code, height=680)
    st.success("📡 雙整體貼圖精準切換看板已上線！")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
