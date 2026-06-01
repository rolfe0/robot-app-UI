import streamlit as st
import base64
import os
import json

# (保持您原本的 setup 與讀取邏輯不變)
st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音同步面板 (防閃爍穩定版)")

firebase_secret_str = st.secrets.get("FIREBASE_KEY")
fb_config_json = "{}"
if firebase_secret_str:
    config_data = json.loads(firebase_secret_str)
    fb_config_json = json.dumps({
        "apiKey": config_data.get("apiKey", ""),
        "authDomain": f"{config_data.get('project_id')}.firebaseapp.com",
        "databaseURL": f"https://{config_data.get('project_id')}-default-rtdb.firebaseio.com",
        "projectId": config_data.get("project_id"),
    })

model_filename = "robot.glb"
texture_normal = "idle.png"
texture_talking = "talk.png"

def get_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# 確保檔案存在，防止 AttributeError
if os.path.exists(model_filename) and os.path.exists(texture_normal) and os.path.exists(texture_talking):
    b64_model = get_b64(model_filename)
    b64_normal = get_b64(texture_normal)
    b64_talking = get_b64(texture_talking)

    raw_html = """
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    <div id="container" style="background:#1E1E24; padding:15px; border-radius:15px;">
        <button id="unlock-audio-btn" style="width:100%; padding:12px; background:#00CC66; color:white; border:none; border-radius:8px; cursor:pointer;">🔊 啟動音訊引擎</button>
        <model-viewer id="live-robot" src="data:application/octet-stream;base64,__B64_MODEL__" autoplay loop style="width:100%; height:420px;"></model-viewer>
        <p id="status-debug" style="color:#00FF00; font-family:monospace;"></p>
    </div>

    <script type="module">
        import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
        import { getDatabase, ref, onValue } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

        const modelViewer = document.querySelector("#live-robot");
        const statusDebug = document.querySelector("#status-debug");
        const imgNormal = "data:image/png;base64,__B64_NORMAL__";
        const imgTalking = "data:image/png;base64,__B64_TALKING__";
        let idleTex, talkTex, currentAudio;

        modelViewer.addEventListener("load", async () => {
            idleTex = await modelViewer.createTexture(imgNormal);
            talkTex = await modelViewer.createTexture(imgTalking);
            applyTex(idleTex);
        });

        function applyTex(tex) {
            modelViewer.model.materials.forEach(m => {
                if(m.pbrMetallicRoughness.baseColorTexture) m.pbrMetallicRoughness.baseColorTexture.setTexture(tex);
            });
        }

        // Firebase 監聽邏輯與播放控制
        document.querySelector("#unlock-audio-btn").onclick = () => {
            const app = initializeApp(__FB_CONFIG_JSON__);
            onValue(ref(getDatabase(app), 'test'), (snapshot) => {
                let data = snapshot.val();
                if(!data) return;
                
                // 這裡就是防閃爍的核心：播放時只執行一次切換，不使用 setInterval
                if(currentAudio) currentAudio.pause();
                currentAudio = new Audio("data:audio/wav;base64," + data.toString().trim());
                
                currentAudio.onplay = () => {
                    applyTex(talkTex); // 說話開始：切換張嘴 (不閃爍)
                    statusDebug.innerText = "說話中...";
                };
                currentAudio.onended = () => {
                    applyTex(idleTex); // 說話結束：切換閉嘴
                    statusDebug.innerText = "閒置中...";
                };
                currentAudio.play();
            });
        };
    </script>
    """
    html_code = raw_html.replace("__B64_MODEL__", b64_model).replace("__B64_NORMAL__", b64_normal).replace("__B64_TALKING__", b64_talking).replace("__FB_CONFIG_JSON__", fb_config_json)
    st.components.v1.html(html_code, height=600)
else:
    st.error("找不到檔案，請確認 robot.glb, idle.png, talk.png 是否都在同一目錄。")
    
