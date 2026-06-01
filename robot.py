import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 AI 語音雙模型看板", layout="centered")
st.title("🤖 AI 語音動態口型 (強制動畫啟動版)")
st.write("目前狀態：🟢 修正：加入強制播放權限，解決動畫不動問題。")

# --- 讀取 Firebase 秘密金鑰 ---
firebase_secret_str = st.secrets.get("FIREBASE_KEY")
fb_config_json = "{}"
if firebase_secret_str:
    config_data = json.loads(firebase_secret_str)
    fb_config_json = json.dumps({"apiKey": config_data.get("apiKey", ""), "projectId": config_data.get("project_id")})

# 檔案名稱定義
model_filename = "robot.glb"
texture_normal = "idle.png"
texture_talking = "talk.png"

# 2. 讀取貼圖與模型
b64_normal = base64.b64encode(open(texture_normal, "rb").read()).decode() if os.path.exists(texture_normal) else ""
b64_talking = base64.b64encode(open(texture_talking, "rb").read()).decode() if os.path.exists(texture_talking) else ""
b64_model = base64.b64encode(open(model_filename, "rb").read()).decode() if os.path.exists(model_filename) else ""

# 3. 終極防錯 HTML (強制啟用所有動畫旗標)
raw_html = """
<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>

<div style="display: flex; flex-direction: column; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 15px;">
    <button id="unlock-btn" style="background-color: #00CC66; color: white; padding: 15px; width: 100%; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">
        🚀 點擊啟動機器人 (強制初始化引擎)
    </button>

    <div style="position: relative; width: 100%; height: 450px; background: #1a1a20; border-radius: 10px;">
        <model-viewer id="m1" src="data:application/octet-stream;base64,__B64_MODEL__" autoplay loop ar-status="not-presenting" style="width: 100%; height: 100%; position: absolute; z-index: 1;"></model-viewer>
        <model-viewer id="m2" src="data:application/octet-stream;base64,__B64_MODEL__" autoplay loop style="width: 100%; height: 100%; position: absolute; z-index: 2; opacity: 0;"></model-viewer>
    </div>
</div>

<script>
    const m1 = document.querySelector("#m1");
    const m2 = document.querySelector("#m2");
    
    // 強制設定動畫名稱並播放
    function forcePlay(el) {
        el.animationName = el.availableAnimations[0];
        el.play();
    }

    document.querySelector("#unlock-btn").onclick = () => {
        // 設定材質
        m1.createTexture("data:image/png;base64,__B64_NORMAL__").then(t => m1.model.materials[0].pbrMetallicRoughness.baseColorTexture.setTexture(t));
        m2.createTexture("data:image/png;base64,__B64_TALKING__").then(t => m2.model.materials[0].pbrMetallicRoughness.baseColorTexture.setTexture(t));
        
        // 強制連續重置動畫
        setInterval(() => {
            forcePlay(m1);
            forcePlay(m2);
        }, 1000);
    };
</script>
"""

# 渲染
html_code = raw_html.replace("__B64_MODEL__", b64_model).replace("__B64_NORMAL__", b64_normal).replace("__B64_TALKING__", b64_talking)
st.components.v1.html(html_code, height=600)
