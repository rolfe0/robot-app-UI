import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音同步面板 (GitHub 音訊優化版)")
st.write("目前狀態：🟢 免費音訊機制已就緒！只要修改 Firebase 的 test 欄位，就會自動播放專案中的 talk.mp3 並頻繁動嘴。")

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
audio_filename = "talk.mp3"  # 👈 你的語音檔名

# 2. 檢查並準備貼圖與音訊的 Base64 資料
b64_normal = ""
b64_talking = ""
b64_audio = ""

if os.path.exists(texture_normal):
    with open(texture_normal, "rb") as f:
        b64_normal = base64.b64encode(f.read()).decode()
if os.path.exists(texture_talking):
    with open(texture_talking, "rb") as f:
        b64_talking = base64.b64encode(f.read()).decode()

# 🛠️ 關鍵改動：如果專案目錄下有 talk.mp3，直接將它轉成 Base64 內嵌進網頁，速度最快！
if os.path.exists(audio_filename):
    with open(audio_filename, "rb") as f:
        b64_audio = base64.b64encode(f.read()).decode()
else:
    st.error(f"⚠️ 專案中找不到【{audio_filename}】語音檔！請記得將語音檔上傳到 GitHub。")

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
        
        // 內嵌的語音檔案音訊來源
        const audioSourceUrl = "data:audio/mp3;base64,{b64_audio}";
        
        let isFirebaseInitialized = false;
        let textureNormalObj = null;
        let textureTalkingObj = null;

        let mouthTimer = null; 
        let currentAudio = null;

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
                    const val = snapshot.val();
                    if (val !== null) {{
                        if (isFirstLoad) {{
                            isFirstLoad = false;
                            return;
                        }}
                        // 🛠️ 只要 Firebase test 有動靜，就直接引爆播放內建的 talk.mp3
                        playLocalAudio();
                    }}
                }});
            }} catch(err) {{ console.error(err); }}
        }}

        // 💥 直接撥放內嵌音訊，並觸發頻繁切換口型
        function playLocalAudio() {{
            try {{
                if (currentAudio) {{
                    currentAudio.pause();
                    currentAudio = null;
                }}
                if (mouthTimer) {{
                    clearInterval(mouthTimer);
                    mouthTimer = null;
                }}

                currentAudio = new Audio(audioSourceUrl);

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

                currentAudio.addEventListener("error", () => {{
                    if (mouthTimer) {{
                        clearInterval(mouthTimer);
                        mouthTimer = null;
                    }}
                    safeApplyTexture(textureNormalObj);
                }});

                currentAudio.play().catch(err => console.log(err));

            }} catch (err) {{ console.error(err); }}
        }}
    </script>
    """
    
    st.components.v1.html(html_code, height=530)
    st.success("📡 雲端即時語音連動看板 (GitHub 音訊優化版) 已完全就緒！")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
