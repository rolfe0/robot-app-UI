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
        <button id="unlock-audio-btn" style="background-color: #00CC66; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%; transition: 0.3s;">
            🔊 第一步：點擊此處激活音效喇叭 (測試前必點)
        </button>

        <model-viewer 
            id="live-robot"
            src="data:application/octet-stream;base64,{b64_model}" 
            alt="3D 機器人模型" 
            camera-controls 
            autoplay
            loop
            style="width: 100%; height: 450px;">
        </model-viewer>
        
        <p id="status-debug" style="color: #AAAAAA; font-size: 14px; margin-top: 10px; font-family: monospace;">系統狀態: 等待喇叭解鎖...</p>
    </div>

    <script type="module">
        import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
        import {{ getDatabase, ref, onValue }} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

        const modelViewer = document.querySelector("#live-robot");
        const unlockBtn = document.querySelector("#unlock-audio-btn");
        const statusDebug = document.querySelector("#status-debug");
        
        const imgNormalUrl = "data:image/png;base64,{b64_normal}";
        const imgTalkingUrl = "data:image/png;base64,{b64_talking}";
        
        let isFirebaseInitialized = false;
        let textureNormalObj = null;
        let textureTalkingObj = null;

        let mouthTimer = null; 
        // 🌟 關鍵改動：全域維護同一個唯一音訊播放器
        let globalAudio = new Audio(); 
        let isAudioUnlocked = false;

        // 🛠️ 按鈕點擊：由使用者主動觸發，這時瀏覽器會 100% 允許音訊播放
        unlockBtn.addEventListener("click", () => {{
            // 給予一個乾淨空音訊做為激活媒介
            globalAudio.src = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA=";
            globalAudio.play().then(() => {{
                isAudioUnlocked = true;
                unlockBtn.style.backgroundColor = "#555555";
                unlockBtn.innerText = "🟢 喇叭已成功解鎖！請去 Firebase 更改欄位測試";
                statusDebug.innerText = "系統狀態: 喇叭已解鎖，正在監聽 Firebase...";
                console.log("瀏覽器音訊通道已由使用者成功解鎖！");
            }}).catch(err => {{
                statusDebug.innerText = "❌ 喇叭解鎖失敗: " + err.message;
            }});
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
                        incomingAudioData = incomingAudioData.trim().replace(/^"|"$/g, '');

                        if (isFirstLoad) {{
                            isFirstLoad = false;
                            statusDebug.innerText = "系統狀態: 初始資料已略過，等待下一波更新...";
                            return;
                        }}
                        
                        if (incomingAudioData.startsWith("data:audio")) {{
                            if (!isAudioUnlocked) {{
                                statusDebug.innerText = "⚠️ 收到音訊但被阻擋！請先點擊上方綠色按鈕解鎖喇叭！";
                                return;
                            }}
                            playIncomingAudio(incomingAudioData);
                        }} else {{
                            statusDebug.innerText = "⚠️ 收到非音訊字串（例如: " + incomingAudioData.substring(0, 10) + "），略過不播放。";
                            console.log("偵測到非音訊開頭資料，略過不播放。");
                        }}
                    }}
                }});
            }} catch(err) {{ console.error("Firebase 監聽啟動錯誤:", err); }}
        }}

        function playIncomingAudio(audioUrlStr) {{
            try {{
                // 停止上一次的所有嘴型計時器
                if (mouthTimer) {{
                    clearInterval(mouthTimer);
                    mouthTimer = null;
                }}

                // 🌟 關鍵改動：直接對已解鎖的 globalAudio 變更音訊來源
                globalAudio.pause();
                globalAudio.src = audioUrlStr;

                // 綁定動嘴事件
                let hasStartedMouth = false;
                
                globalAudio.onplay = () => {{
                    statusDebug.innerText = "🎵 語音同步播放中...";
                    let isTalkFace = true;
                    safeApplyTexture(textureTalkingObj);
                    
                    if(!hasStartedMouth) {{
                        hasStartedMouth = true;
                        mouthTimer = setInterval(() => {{
                            if (globalAudio.paused || globalAudio.ended) {{
                                clearInterval(mouthTimer);
                                mouthTimer = null;
                                safeApplyTexture(textureNormalObj);
                            }} else {{
                                isTalkFace = !isTalkFace;
                                safeApplyTexture(isTalkFace ? textureTalkingObj : textureNormalObj);
                            }}
                        }}, 140);
                    }}
                }};

                globalAudio.onended = () => {{
                    if (mouthTimer) {{
                        clearInterval(mouthTimer);
                        mouthTimer = null;
                    }}
                    safeApplyTexture(textureNormalObj);
                    statusDebug.innerText = "🟢 播放完畢，等待下一波語音...";
                }};

                globalAudio.onerror = (e) => {{
                    if (mouthTimer) {{
                        clearInterval(mouthTimer);
                        mouthTimer = null;
                    }}
                    safeApplyTexture(textureNormalObj);
                    statusDebug.innerText = "❌ 音訊解碼失敗，請確認 Python 端寫入的 Base64 格式是否完整。";
                }};

                // 執行播放
                globalAudio.play().catch(err => {{
                    statusDebug.innerText = "❌ 播放失敗: " + err.message;
                }});

            }} catch (err) {{ console.error("處理音訊播放失敗:", err); }}
        }}
    </script>
    """
    
    st.components.v1.html(html_code, height=580)
    st.success("📡 安全版即時語音連動看板已完全就緒！")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
