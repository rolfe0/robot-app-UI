import streamlit as st
import base64
import os
import json

# 設定頁面
st.set_page_config(page_title="🤖 AI 語音動態口型", layout="centered")
st.title("🤖 AI 語音動態口型 (極速切換版)")

# 檔案定義
model_filename = "robot.glb"
texture_idle = "idle.png"
texture_talk = "talk.png"

# 讀取檔案函式
def get_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# 取得 Firebase 設定
firebase_secret_str = st.secrets.get("FIREBASE_KEY", "{}")
fb_config = json.loads(firebase_secret_str)

if os.path.exists(model_filename) and os.path.exists(texture_idle) and os.path.exists(texture_talk):
    b64_model = get_b64(model_filename)
    b64_idle = get_b64(texture_idle)
    b64_talk = get_b64(texture_talk)

    html_code = f"""
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    <model-viewer id="robot" src="data:application/octet-stream;base64,{b64_model}" 
                  style="width: 100%; height: 500px;" autoplay loop camera-controls></model-viewer>
    
    <script type="module">
        import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
        import {{ getDatabase, ref, onValue }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

        const viewer = document.querySelector('#robot');
        const idleTex = "data:image/png;base64,{b64_idle}";
        const talkTex = "data:image/png;base64,{b64_talk}";
        let idleObj, talkObj;

        viewer.addEventListener('load', async () => {{
            // 確保動畫正常播放
            viewer.animationName = viewer.availableAnimations[0];
            viewer.play();
            
            // 預先載入兩張貼圖
            idleObj = await viewer.createTexture(idleTex);
            talkObj = await viewer.createTexture(talkTex);
            
            // 初始狀態為閒置
            setTex(idleObj);
        }});

        function setTex(tex) {{
            viewer.model.materials.forEach(m => {{
                if(m.pbrMetallicRoughness.baseColorTexture)
                    m.pbrMetallicRoughness.baseColorTexture.setTexture(tex);
            }});
        }}

        // Firebase 監聽邏輯
        const app = initializeApp({json.dumps(fb_config)});
        const db = getDatabase(app);
        
        onValue(ref(db, 'test'), (snapshot) => {{
            const val = snapshot.val();
            if(val) {{
                // 切換為張嘴
                setTex(talkObj);
                // 0.1秒後切回閒置
                clearTimeout(window.talkTimer);
                window.talkTimer = setTimeout(() => setTex(idleObj), 100);
            }}
        }});
    </script>
    """
    st.components.v1.html(html_code, height=550)
    st.success("✅ 系統已啟動：偵測到語音訊號將以 0.1 秒速度切換口型。")
else:
    st.error("❌ 找不到模型檔案 (robot.glb) 或貼圖檔案 (idle.png / talk.png)，請確認檔案名稱正確。")
