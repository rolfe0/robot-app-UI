import streamlit as st
import base64
import os
import json

st.set_page_config(page_title="🤖 AI 語音雙模型看板", layout="centered")
st.title("🤖 AI 語音動態口型 (雙模型疊加版)")
st.write("目前狀態：🟢 CSS 透明度切換引擎已就緒！")

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

    html_lines = [
        '<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>',
        '<div style="display: flex; flex-direction: column; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 15px;">',
        '  <button id="unlock-audio-btn" style="background-color: #00CC66; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%;">🔊 請先點擊此處解鎖喇叭</button>',
        '  <div style="position: relative; width: 100%; height: 450px; background: #2a2a35; border-radius: 10px; overflow: hidden;">',
        '    <model-viewer id="model-idle" src="data:application/octet-stream;base64,MODEL_PLACEHOLDER" camera-controls autoplay loop style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1;"></model-viewer>',
        '    <model-viewer id="model-talk" src="data:application/octet-stream;base64,MODEL_PLACEHOLDER" autoplay loop style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 2; opacity: 0; pointer-events: none; transition: opacity 0.05s ease;"></model-viewer>',
        '  </div>',
        '  <div style="background-color: #000; width: 100%; padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #444;">',
        '    <p id="status-debug" style="color: #00FF00; font-size: 13px; font-family: monospace; margin: 0;">系統狀態: 等待點擊綠色按鈕解鎖...</p>',
        '    <p id="data-debug" style="color: #FFCC00; font-size: 12px; font-family: monospace; margin: 5px 0 0 0; word-break: break-all;">Firebase 監聽狀態: 等待連線中...</p>',
        '  </div>',
        '</div>',
    ]

    js_lines = [
        '<script type="module">',
        '  import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";',
        '  import { getDatabase, ref, onValue } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";',
        '  const modelIdle = document.querySelector("#model-idle");',
        '  const modelTalk = document.querySelector("#model-talk");',
        '  const unlockBtn = document.querySelector("#unlock-audio-btn");',
        '  const statusDebug = document.querySelector("#status-debug");',
        '  const dataDebug = document.querySelector("#data-debug");',
        '  let isAudioUnlocked = false, currentAudio = null, lastPlayedAudioStr = "";',
        '  let audioCtx = null, analyser = null, dataArray = null, animationFrameId = null;',
        '  let isTalking = false;',

        # 貼圖疊加在 model-talk 上
        '  const imgTalkingUrl = "data:image/png;base64,TALKING_PLACEHOLDER";',
        '  const imgNormalUrl = "data:image/png;base64,NORMAL_PLACEHOLDER";',

        # 啟動動畫
        '  function startAnim(mv) {',
        '    mv.addEventListener("load", () => {',
        '      const anims = mv.availableAnimations;',
        '      if (anims && anims.length > 0) {',
        '        mv.animationName = anims[0];',
        '        mv.play({repetitions: Infinity});',
        '      }',
        '    });',
        '  }',
        '  startAnim(modelIdle);',
        '  startAnim(modelTalk);',

        # 套用貼圖到 model-talk
        '  modelTalk.addEventListener("load", async () => {',
        '    try {',
        '      const tex = await modelTalk.createTexture(imgTalkingUrl);',
        '      modelTalk.model.materials.forEach(mat => {',
        '        try { mat.pbrMetallicRoughness.baseColorTexture.setTexture(tex); } catch(e) {}',
        '      });',
        '    } catch(e) { console.error(e); }',
        '  });',

        # 切換顯示
        '  function showTalking(on) {',
        '    if (on === isTalking) return;',
        '    isTalking = on;',
        '    modelTalk.style.opacity = on ? "1" : "0";',
        '  }',

        # 解鎖音訊
        '  unlockBtn.addEventListener("click", () => {',
        '    isAudioUnlocked = true;',
        '    unlockBtn.style.backgroundColor = "#555";',
        '    unlockBtn.innerText = "🟢 引擎已啟動，等待音訊...";',
        '    statusDebug.innerText = "系統狀態: 喇叭已解鎖，監聽中。";',
        '    audioCtx = new (window.AudioContext || window.webkitAudioContext)();',
        '    let dummy = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA=");',
        '    let src = audioCtx.createMediaElementSource(dummy);',
        '    src.connect(audioCtx.destination);',
        '    dummy.play().catch(e => {});',
        '    startFirebase();',
        '  });',

        # Firebase
        '  function startFirebase() {',
        '    const cfg = FB_CONFIG_PLACEHOLDER;',
        '    if (!cfg.databaseURL) { statusDebug.innerText = "❌ 找不到 Firebase 配置！"; return; }',
        '    try {',
        '      const app = initializeApp(cfg);',
        '      const db = getDatabase(app);',
        '      const voiceRef = ref(db, "test");',
        '      let isFirst = true;',
        '      onValue(voiceRef, (snap) => {',
        '        let val = snap.val();',
        '        if (!val) return;',
        '        let audio = val.toString().trim().replace(/^[\'"]|[\'"]$/g, "");',
        '        dataDebug.innerText = "收到資料長度: " + audio.length;',
        '        if (isFirst) { isFirst = false; lastPlayedAudioStr = audio; return; }',
        '        if (audio.length > 100) {',
        '          if (!audio.startsWith("data:")) audio = "data:audio/wav;base64," + audio;',
        '          if (currentAudio && !currentAudio.paused && !currentAudio.ended && audio === lastPlayedAudioStr) return;',
        '          lastPlayedAudioStr = audio;',
        '          playAudio(audio);',
        '        }',
        '      });',
        '    } catch(e) { statusDebug.innerText = "❌ Firebase 連線失敗: " + e.message; }',
        '  }',

        # 播放音訊
        '  function playAudio(url) {',
        '    try {',
        '      if (currentAudio) currentAudio.pause();',
        '      if (animationFrameId) cancelAnimationFrame(animationFrameId);',
        '      currentAudio = new Audio(url);',
        '      currentAudio.crossOrigin = "anonymous";',
        '      if (audioCtx) {',
        '        if (audioCtx.state === "suspended") audioCtx.resume();',
        '        analyser = audioCtx.createAnalyser();',
        '        analyser.fftSize = 64;',
        '        const src = audioCtx.createMediaElementSource(currentAudio);',
        '        src.connect(analyser);',
        '        analyser.connect(audioCtx.destination);',
        '        dataArray = new Uint8Array(analyser.frequencyBinCount);',
        '      }',
        '      currentAudio.addEventListener("play", () => {',
        '        statusDebug.innerText = "🎵 播放中，即時切換模型...";',
        '        function loop() {',
        '          if (!currentAudio || currentAudio.paused || currentAudio.ended) { showTalking(false); return; }',
        '          animationFrameId = requestAnimationFrame(loop);',
        '          if (analyser && dataArray) {',
        '            analyser.getByteFrequencyData(dataArray);',
        '            let total = 0;',
        '            for (let i = 0; i < dataArray.length; i++) total += dataArray[i];',
        '            showTalking((total / dataArray.length) > 15);',
        '          }',
        '        }',
        '        loop();',
        '      });',
        '      currentAudio.addEventListener("ended", () => {',
        '        showTalking(false);',
        '        statusDebug.innerText = "🟢 播放完畢，恢復待機。";',
        '      });',
        '      currentAudio.play().catch(e => { statusDebug.innerText = "❌ 播放失敗: " + e.message; });',
        '    } catch(e) { console.error(e); }',
        '  }',
        '</script>',
    ]

    html_code = "\n".join(html_lines + js_lines)
    html_code = html_code.replace("MODEL_PLACEHOLDER", b64_model)
    html_code = html_code.replace("NORMAL_PLACEHOLDER", b64_normal)
    html_code = html_code.replace("TALKING_PLACEHOLDER", b64_talking)
    html_code = html_code.replace("FB_CONFIG_PLACEHOLDER", fb_config_json)

    st.components.v1.html(html_code, height=680)
    st.success("📡 雙模型疊加看板已上線！")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
