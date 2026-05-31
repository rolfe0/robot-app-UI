import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音檔案接收與動態口型面板")
st.write("目前狀態：🟢 語音檔案播放核心已就緒！只要 Firebase 的 test 欄位寫入音訊網址，這裡就會自動播放並高頻動嘴。")

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

# 貼圖與模型檔名
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

    # 4. 嵌入 3D 渲染器與音訊連動腳本
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
        
        const imgNormalUrl = "data:image/png;base64,{b64_normal}";
        const imgTalkingUrl = "data:image/png;base64,{b64_talking}";
        
        let isFirebaseInitialized = false;
        let textureNormalObj = null;
        let textureTalkingObj = null;

        let mouthTimer = null; 
        let currentAudio = null; // 用於存放 HTML5 Audio 物件

        modelViewer.addEventListener("load", async () => {{
            // 動態安全啟動
            try {{
                const anims = modelViewer.availableAnimations;
                let targetAnim = anims.find(name => name.toLowerCase().includes("mixamo.com.001")) ||
                                 anims.find(name => name.toLowerCase().includes("armature.001")) ||
                                 anims[0];
                if (targetAnim) {{
                    modelViewer.animationName = targetAnim;
                    setTimeout(() => {{ modelViewer.play(); }}, 100);
                }}
            }} catch (e) {{ console.log("動畫延遲"); }}

            // 材質初始化
            try {{
                if (modelViewer.model && modelViewer.model.materials.length > 0) {{
                    textureNormalObj = await modelViewer.createTexture(imgNormalUrl);
                    textureTalkingObj = await modelViewer.createTexture(imgTalkingUrl);
                    safeApplyTexture(textureNormalObj); 
                }}
            }} catch (err) {{ console.log("材質初始化略過零件"); }}
            
            if (!isFirebaseInitialized) {{
                startFirebaseListener();
                isFirebaseInitialized = true;
            }}
        }});

        function safeApplyTexture(targetTexture) {{
            if (!targetTexture || !modelViewer.model || !modelViewer.model.materials) return;
            modelViewer.model.materials.forEach(mat => {{
                try {{
                    if (mat && mat.pbrMetallicRoughness && mat.pbrMetallicRoughness.baseColorTexture) {{
                        mat.pbrMetallicRoughness.baseColorTexture.setTexture(targetTexture);
                    }}
                }} catch(e) {{ }}
            }});
        }}

        // Firebase 監聽
        function startFirebaseListener() {{
            const firebaseConfig = {fb_config_json};
            if (!firebaseConfig.databaseURL) return;

            try {{
                const app = initializeApp(firebaseConfig);
                const database = getDatabase(app);
                const voiceRef = ref(database, 'test');

                let isFirstLoad = true;

                onValue(voiceRef, (snapshot) => {{
                    const audioUrl = snapshot.val(); // 這裡拿到的會是語音檔的網路網址
                    if (audioUrl) {{
                        if (isFirstLoad) {{
                            isFirstLoad = false;
                            return;
                        }}
                        // 🛠️ 呼叫「真·語音檔播放與口型連動」函數
                        playAudioAndChangeMouth(audioUrl);
                    }}
                }});
            }} catch(err) {{ console.error(err); }}
        }}

        // 💥 核心功能：播放真實語音檔，並利用音訊事件精準連動口型
        function playAudioAndChangeMouth(url) {{
            try {{
                // 1. 如果前一個語音還在播，先強制停止並清空定時器
                if (currentAudio) {{
                    currentAudio.pause();
                    currentAudio = null;
                }}
                if (mouthTimer) {{
                    clearInterval(mouthTimer);
                    mouthTimer = null;
                }}

                // 2. 建立新音訊物件並載入傳入的網址
                currentAudio = new Audio(url);
                currentAudio.crossOrigin = "anonymous"; // 允許跨網域音訊播放

                // 📣 當音訊「開始播放」時：開啟定時器讓嘴巴高頻動起來
                currentAudio.addEventListener("play", () => {{
                    let isTalkFace = true;
                    safeApplyTexture(textureTalkingObj);
                    
                    mouthTimer = setInterval(() => {{
                        if (isTalkFace) {{
                            safeApplyTexture(textureNormalObj);
                        }} else {{
                            safeApplyTexture(textureTalkingObj);
                        }}
                        isTalkFace = !isTalkFace;
                    }}, 140); // 稍微調快到 140ms，讓口型看起來更緊湊自然
                }});

                // 🛑 當音訊「播放結束」時：清除定時器，強制閉嘴回 idle.png
                currentAudio.addEventListener("ended", () => {{
                    if (mouthTimer) {{
                        clearInterval(mouthTimer);
                        mouthTimer = null;
                    }}
                    safeApplyTexture(textureNormalObj);
                }});

                // 錯誤處理保底
                currentAudio.addEventListener("error", () => {{
                    if (mouthTimer) {{
                        clearInterval(mouthTimer);
                        mouthTimer = null;
                    }}
                    safeApplyTexture(textureNormalObj);
                    console.error("語音檔載入或播放失敗，網址可能無效");
                }});

                // 3. 執行播放
                currentAudio.play().catch(err => {{
                    console.log("瀏覽器阻擋自動播放，需要使用者先點擊網頁:", err);
                }});

            }} catch (err) {{ console.error("音訊初始化失敗:", err); }}
        }}
    </script>
    """
    
    st.components.v1.html(html_code, height=530)
    st.success("📡 雲端即時語音音訊監聽看板已完全就緒！")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
