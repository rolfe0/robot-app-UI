import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音同步面板 (安全播放優化版)")
st.write("目前狀態：🟢 遠端音訊動態接收核心已就緒！等待外部資料庫將語音 Base64 寫入 Firebase test 欄位...")

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

# 檔案名稱定義
model_filename = "robot.glb"
texture_normal = "idle.png"
texture_talking = "talk.png"

# 2. 檢查並準備貼圖
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
    
    <div style="display: flex; flex-direction: column; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 15px;">
        <!-- 🛠️ 強制解鎖按鈕：點擊這裡 100% 可以解除瀏覽器聲音封鎖 -->
        <button id="unlock-audio-btn" style="background-color: #00CC66; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%;">
            🔊 點擊此處：開啟並解鎖機器人音效喇叭 (測試前必點)
        </button>

        <model-viewer 
            id="live-robot"
            src="data:application/octet-stream;base64,{b64_model}" 
            alt="3D 機器人模型" 
            camera-controls 
            autoplay
            loop
            time-scale="0.01"
            style="width: 100%; height: 450px;">
        </model-viewer>
    </div>

    <script type="module">
        import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
        import {{ getDatabase, ref, onValue }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

        const modelViewer = document.querySelector("#live-robot");
        const unlockBtn = document.querySelector("#unlock-audio-btn");
        
        const imgNormalUrl = "data:image/png;base64,{b64_normal}";
        const imgTalkingUrl = "data:image/png;base64,{b64_talking}";
        
        let isFirebaseInitialized = false;
        let textureNormalObj = null;
        let textureTalkingObj = null;

        let mouthTimer = null; 
        let currentAudio = null;
        let isAudioUnlocked = false;

        // 🛠️ 監聽解鎖按鈕
        unlockBtn.addEventListener("click", () => {{
            isAudioUnlocked = true;
            unlockBtn.style.backgroundColor = "#555555";
            unlockBtn.innerText = "🟢 喇叭已解鎖！請去 Firebase 更改欄位測試";
            console.log("喇叭播放權限已由使用者點擊按鈕成功解鎖！");
        }});

        modelViewer.addEventListener("load", async () => {{
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

        function startFirebaseListener() {{
            const firebaseConfig = {fb_config_json};
            if (!firebaseConfig.databaseURL) return;

            try {{
                const app = initializeApp(firebaseConfig);
                const database = getDatabase(app);
                const voiceRef = ref(database, 'test');

                let isFirstLoad = true;

                onValue(voiceRef, (snapshot) => {{
                    let incomingAudioData = snapshot.val();
                    if (incomingAudioData) {{
                        // 容錯處理：移除可能的頭尾隱號與空白字元
                        incomingAudioData = incomingAudioData.trim().replace(/^"|"$/g, '');

                        if (isFirstLoad) {{
                            isFirstLoad = false;
                            return;
                        }}
                        
                        if (incomingAudioData.startsWith("data:audio")) {{
                            playIncomingAudio(incomingAudioData);
                        }} else {{
                            console.log("偵測到非音訊開頭資料，略過不播放。收到的資料開頭為:", incomingAudioData.substring(0, 20));
                        }}
                    }}
                }});
            }} catch(err) {{ console.error("Firebase 監聽啟動錯誤:", err); }}
        }}

        function playIncomingAudio(audioUrlStr) {{
            try {{
                if (currentAudio) {{
                    currentAudio.pause();
                    currentAudio = null;
                }}
                if (mouthTimer) {{
                    clearInterval(mouthTimer);
                    mouthTimer = null;
                }}

                currentAudio = new Audio(audioUrlStr);

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
                    }}, 140);
                }});

                currentAudio.addEventListener("ended", () => {{
                    if (mouthTimer) {{
                        clearInterval(mouthTimer);
                        mouthTimer = null;
                    }}
                    safeApplyTexture(textureNormalObj);
                }});

                currentAudio.addEventListener("error", (e) => {{
                    if (mouthTimer) {{
                        clearInterval(mouthTimer);
                        mouthTimer = null;
                    }}
                    safeApplyTexture(textureNormalObj);
                    console.error("音訊解碼播放失敗，可能 Base64 字串不完整。");
                }});

                currentAudio.play().catch(err => {{
                    console.error("播放被瀏覽器阻擋，請確保有點擊上方的綠色解鎖按鈕！", err);
                }});

            }} catch (err) {{ console.error("初始化音訊物件失敗:", err); }}
        }}
    </script>
    """
    
    st.components.v1.html(html_code, height=550)
    st.success("📡 安全版即時語音連動看板已完全就緒！")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
