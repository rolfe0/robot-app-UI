import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音與貼圖即時同步面板")
st.write("目前狀態：🟢 系統已進入【雲端監聽模式】。只要其他人往 Firebase 資料庫發送語音，這裡就會自動發聲並切換口型。")

# --- 讀取 Firebase 秘密金鑰與設定變數 ---
firebase_secret_str = st.secrets.get("FIREBASE_KEY")
fb_config_json = "{}"

if firebase_secret_str:
    try:
        # 驗證金鑰格式
        config_data = json.loads(firebase_secret_str)
        st.success("🟢 Firebase 雲端監聽核心已安全啟動！")
        
        # 這裡我們需要把整個 Firebase 設定丟給前端 JavaScript 初始化
        # 包含 apiKey, authDomain, databaseURL, projectId 等
        # 如果你的 secrets 內只有私鑰，請確保內含基本的前端連線資訊
        # 為了方便瀏覽器連線，我們將其打包成字串傳給前端
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
# ------------------------------

# 設定 3D 模型與貼圖檔名
model_filename = "robot.glb"
texture_normal = "normal.png"
texture_talking = "talking.png"

# 2. 檢查並準備貼圖的 Base64 資料，方便前端 JavaScript 即時切換
b64_normal = ""
b64_talking = ""

if os.path.exists(texture_normal):
    with open(texture_normal, "rb") as f:
        b64_normal = base64.b64encode(f.read()).decode()
else:
    st.error(f"❌ 找不到待機貼圖【{texture_normal}】")

if os.path.exists(texture_talking):
    with open(texture_talking, "rb") as f:
        b64_talking = base64.b64encode(f.read()).decode()
else:
    st.error(f"❌ 找不到說話貼圖【{texture_talking}】")

# 3. 檢查 3D 檔案是否存在並讀取
if os.path.exists(model_filename):
    with open(model_filename, "rb") as f:
        bytes_data = f.read()
    b64_model = base64.b64encode(bytes_data).decode()

    # 4. 嵌入 3D 渲染器與 Firebase 即時監聽與語音切貼圖連動腳本
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
        
        // 貼圖 Base64 資料
        const imgNormalSrc = "data:image/png;base64,{b64_normal}";
        const imgTalkingSrc = "data:image/png;base64,{b64_talking}";
        
        let textureNormalObj = null;
        let textureTalkingObj = null;
        let isFirebaseInitialized = false;

        // 1. 模型載入後，先初始化動畫與預備貼圖物件
        modelViewer.addEventListener("load", async () => {{
            // 啟動低速動畫
            const anims = modelViewer.availableAnimations;
            let targetAnim = anims.find(name => name.toLowerCase().includes("mixamo.com.001")) ||
                             anims.find(name => name.toLowerCase().includes("armature.001")) ||
                             anims[0];
            if (targetAnim) {{
                modelViewer.animationName = targetAnim;
                setTimeout(() => {{ modelViewer.play(); }}, 100);
            }}

            // 預先將兩張貼圖載入成 model-viewer 的材質物件
            if (modelViewer.model) {{
                textureNormalObj = await modelViewer.createTexture(imgNormalSrc);
                textureTalkingObj = await modelViewer.createTexture(imgTalkingSrc);
                // 預設切換為正常待機臉
                changeFace(textureNormalObj);
            }}
            
            // 3D 準備好後，再啟動 Firebase 監聽，避免時間差報錯
            if (!isFirebaseInitialized) {{
                startFirebaseListener();
                isFirebaseInitialized = true;
            }}
        }});

        // 核心功能：切換材質貼圖的函數
        function changeFace(targetTexture) {{
            if (!targetTexture || !modelViewer.model) return;
            modelViewer.model.materials.forEach(material => {{
                const matName = material.name.toLowerCase();
                // 智慧匹配面部、螢幕或頭部材質
                if (matName.includes("face") || matName.includes("screen") || matName.includes("head") || matName.includes("emissive")) {{
                    if (material.pbrMetallicRoughness.baseColorTexture) {{
                        material.pbrMetallicRoughness.baseColorTexture.setTexture(targetTexture);
                    }}
                }}
            }});
        }}

        // 2. 💥 Firebase 即時監聽與語音連動核心
        function startFirebaseListener() {{
            const firebaseConfig = {fb_config_json};
            
            if (!firebaseConfig.databaseURL) {{
                console.error("Firebase 設定不完整，無法啟動即時監聽。");
                return;
            }}

            // 初始化 Firebase
            const app = initializeApp(firebaseConfig);
            const database = getDatabase(app);
            
            # 監聽的資料庫節點路徑：監聽 /current_voice 節點
            const voiceRef = ref(database, 'current_voice');

            let isFirstLoad = true; // 用於跳過網頁剛開啟時的舊資料，只接收開啟後的新語音

            onValue(voiceRef, (snapshot) => {{
                const data = snapshot.val();
                
                // 確保節點有資料，且不是網頁剛打開時的第一次讀取
                if (data && data.text) {{
                    if (isFirstLoad) {{
                        isFirstLoad = false;
                        console.log("Firebase 首次連線成功，等待全新語音指令...");
                        return;
                    }}

                    console.log("偵測到遠端新語音輸入:", data.text);
                    speakAndChangeFace(data.text);
                }}
            }});
        }}

        // 3. 💥 發聲並同步切換貼圖核心控制
        function speakAndChangeFace(text) {{
            if (!('speechSynthesis' in window)) return;

            window.speechSynthesis.cancel(); // 停止上一句，防止卡音
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = "zh-TW"; // 台灣中文
            utterance.rate = 0.9;     // 稍微慢一點點，配合貼圖

            // 📣 當語音「開始播放」時：切換成說話貼圖 (talking.png)
            utterance.onstart = () => {{
                changeFace(textureTalkingObj);
            }};

            // 🛑 當語音「播放結束」或「被中斷」時：自動切回待機貼圖 (normal.png)
            utterance.onend = () => {{
                changeFace(textureNormalObj);
            }};
            utterance.onerror = () => {{
                changeFace(textureNormalObj);
            }};

            // 讓瀏覽器說話
            window.speechSynthesis.speak(utterance);
        }}
    </script>
    """
    
    st.components.v1.html(html_code, height=530)
    st.success("📡 雲端即時監聽視窗已就緒！")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
