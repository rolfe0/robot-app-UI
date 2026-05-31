import streamlit as st
import base64
import os
import json

st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音同步面板 (動態語音連續接收版)")
st.write("目前狀態：🟢 連續監聽核心已就緒！等待外部資料庫隨時寫入新的語音 Base64 檔案...")

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

    html_code = f"""
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    
    <div style="display: flex; flex-direction: column; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 15px;">
        <button id="unlock-audio-btn" style="background-color: #00CC66; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%;">
            🔊 系統啟動步驟：請先點擊此處解鎖喇叭 (只需點一次，即可接收無限次語音)
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
        let lastAudioData = ""; // 用來記錄上一次的語音，防止重複播放

        // 使用者點擊解鎖
        unlockBtn.addEventListener("click", () => {{
            unlockBtn.style.backgroundColor = "#555555";
            unlockBtn.innerText = "🟢 喇叭監聽中... 隨時等待外部資料庫傳入語音 🟢";
            console.log("喇叭已完全解鎖！穩定接收外部連續訊號中。");
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
            }} catch (e) {{ }}

            try {{
                if (modelViewer.model && modelViewer.model.materials.length > 0) {{
                    textureNormalObj = await modelViewer.createTexture(imgNormalUrl);
                    textureTalkingObj = await modelViewer.createTexture(imgTalkingUrl);
                    safeApplyTexture(textureNormalObj); 
                }}
            }} catch (err) {{ }}
            
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

        // 核心監聽：每次 Firebase 欄位變更，就會觸發一次這個 function
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
                    if (!incomingAudioData) return;

                    // 容錯清洗，去掉可能的換行與頭尾引號
                    incomingAudioData = incomingAudioData.trim().replace(/^"|"$/g, '');

                    // 第一次載入時如果是舊資料，略過不播
                    if (isFirstLoad) {{
                        isFirstLoad = false;
                        lastAudioData = incomingAudioData;
                        return;
                    }}
                    
                    // 檢查這是不是一串「全新傳進來」的語音
                    if (incomingAudioData.startsWith("data:audio") && incomingAudioData !== lastAudioData) {{
                        lastAudioData = incomingAudioData; // 更新歷史紀錄
                        playIncomingAudio(incomingAudioData); // 💥 立刻呼叫播放引擎！
                    }}
                }});
            }} catch(err) {{ console.error("Firebase 監聽失敗:", err); }}
        }}

        // 播音與口型換膚連續連動引擎
        function playIncomingAudio(audioUrlStr) {{
            try {{
                // 如果前一通電話還在播，強行中斷，改播最新傳過來的語音
                if (currentAudio) {{
                    currentAudio.pause();
                    currentAudio = null;
                }}
                if (mouthTimer) {{
                    clearInterval(mouthTimer);
                    mouthTimer = null;
                }}

                // 將全新傳入的語音丟入 HTML5 播放器
                currentAudio = new Audio(audioUrlStr);

                currentAudio.addEventListener("play", () => {{
                    let isTalkFace = true;
                    safeApplyTexture(textureTalkingObj);
                    
                    // 根據聲音長度，每 140 毫秒高速切換口型貼圖
                    mouthTimer = setInterval(() => {{
                        if (isTalkFace) {{
                            safeApplyTexture(textureNormalObj);
                        }} else {{
                            safeApplyTexture(textureTalkingObj);
                        }}
                        isTalkFace = !isTalkFace;
                    }}, 140);
                }});

                // 播放完畢，自動閉嘴，回復 idle 貼圖，並安靜等待下一通語音
                currentAudio.addEventListener("ended", () => {{
                    if (mouthTimer) {{
                        clearInterval(mouthTimer);
                        mouthTimer = null;
                    }}
                    safeApplyTexture(textureNormalObj);
                    console.log("當前語音播放完畢，回復靜止狀態。持續監聽下一則...");
                }});

                currentAudio.addEventListener("error", () => {{
                    if (mouthTimer) {{
                        clearInterval(mouthTimer);
                        mouthTimer = null;
                    }}
                    safeApplyTexture(textureNormalObj);
                    console.error("收到的 Base64 格式毀損，無法解碼。");
                }});

                currentAudio.play().catch(err => {{
                    console.error("播放被瀏覽器攔截，必須先點擊網頁上方的解鎖按鈕！", err);
                }});

            }} catch (err) {{ console.error("播放引擎初始化失敗:", err); }}
        }}
    </script>
    """
    
    st.components.v1.html(html_code, height=550)
    st.success("📡 終極連續語音串流看板已完全就緒！")
else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
