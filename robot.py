import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音與整體材質同步面板")
st.write("目前狀態：🟢 語音與整體材質核心已修復就緒。請修改 Firebase 控制台的 test 欄位進行測試。")

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

# 貼圖檔名
model_filename = "robot.glb"
texture_normal = "idle.png"
texture_talking = "talk.png"

# 2. 檢查並準備貼圖的 Base64 資料
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

    # 4. 嵌入 3D 渲染器與連動腳本
    html_code = f"""
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    
    <div style="display: flex; justify-content: center; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 10px;">
        <model-viewer 
            id="live-robot"
            src="data:application/octet-stream;base64,{b64_model}" 
            alt="3D 機器人模型" 
            camera-controls 
            autoplay
            loop
            time-scale="0.01"
            style="width: 100%; height: 500px;">
        </model-viewer>
    </div>

    <script type="module">
        import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
        import {{ getDatabase, ref, onValue }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

        const modelViewer = document.querySelector("#live-robot");
        
        // 將 Base64 轉換成 DataURL 字串
        const imgNormalUrl = "data:image/png;base64,{b64_normal}";
        const imgTalkingUrl = "data:image/png;base64,{b64_talking}";
        
        let isFirebaseInitialized = false;

        modelViewer.addEventListener("load", () => {{
            // 啟動低速動畫
            const anims = modelViewer.availableAnimations;
            let targetAnim = anims.find(name => name.toLowerCase().includes("mixamo.com.001")) ||
                             anims.find(name => name.toLowerCase().includes("armature.001")) ||
                             anims[0];
            if (targetAnim) {{
                modelViewer.animationName = targetAnim;
                setTimeout(() => {{ modelViewer.play(); }}, 100);
            }}

            // 初始化：先套用整張 idle.png 材質圖片
            changeGlobalTexture(imgNormalUrl);
            
            // 語音與資料庫監聽安全初始化
            if (!isFirebaseInitialized) {{
                startFirebaseListener();
                isFirebaseInitialized = true;
            }}
        }});

        # 💥 整體材質圖片更換函數：徹底重寫底層材質圖片的來源
        function changeGlobalTexture(textureDataUrl) {{
            if (!modelViewer.model) return;
            
            modelViewer.model.materials.forEach(material => {{
                if (material.pbrMetallicRoughness && 
                    material.pbrMetallicRoughness.baseColorTexture && 
                    material.pbrMetallicRoughness.baseColorTexture.texture && 
                    material.pbrMetallicRoughness.baseColorTexture.texture.source) {{
                    
                    // 🎯 直接修改底層唯一的材質圖片 URI (對付整體貼圖最有效)
                    material.pbrMetallicRoughness.baseColorTexture.texture.source.setURI(textureDataUrl);
                }}
            }});
        }}

        // Firebase 監聽
        function startFirebaseListener() {{
            const firebaseConfig = {fb_config_json};
            if (!firebaseConfig.databaseURL) return;

            const app = initializeApp(firebaseConfig);
            const database = getDatabase(app);
            const voiceRef = ref(database, 'test');

            let isFirstLoad = true;

            onValue(voiceRef, (snapshot) => {{
                const voiceText = snapshot.val();
                if (voiceText) {{
                    if (isFirstLoad) {{
                        isFirstLoad = false;
                        return;
                    }}
                    speakAndChangeFace(voiceText);
                }}
            }});
        }}

        function speakAndChangeFace(text) {{
            if (!('speechSynthesis' in window)) return;

            window.speechSynthesis.cancel();
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = "zh-TW";
            utterance.rate = 0.9;

            // 📣 說話開始 -> 將底層材質圖片一秒更換為 talk.png 
            utterance.onstart = () => {{
                changeGlobalTexture(imgTalkingUrl);
            }};

            // 🛑 說話結束 -> 將底層材質圖片切換回 idle.png
            utterance.onend = () => {{
                changeGlobalTexture(imgNormalUrl);
            }};
            utterance.onerror = () => {{
                changeGlobalTexture(imgNormalUrl);
            }};

            window.speechSynthesis.speak(utterance);
        }}
    </script>
    """
    
    st.components.v1.html(html_code, height=530)
    st.success("📡 雲端即時連動看板已完全就緒！")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
