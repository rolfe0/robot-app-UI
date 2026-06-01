import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 AI 語音雙模型看板", layout="centered")
st.title("🤖 AI 語音動態口型 (雙模型疊加、動畫永不卡死版)")
st.write("目前狀態：🟢 最終修正版引擎已啟動！已完美排除任何引號衝突與動畫卡死的 Bug。")

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
        st.error("❌ 金鑰解析失敗，請檢查 Settings 裡的 Secrets。")
else:
    st.warning("⚠️ 系統未偵測到環境變數中的 Firebase 金鑰。")

# 檔案名稱定義
model_filename = "robot.glb"
texture_normal = "idle.png"    # 閉嘴的完整貼圖
texture_talking = "talk.png"   # 開口的完整貼圖

# 2. 檢查並讀取兩張整體貼圖
b64_normal = ""
b64_talking = ""

if os.path.exists(texture_normal):
    with open(texture_normal, "rb") as f:
        b64_normal = base64.b64encode(f.read()).decode()
else:
    st.error(f"❌ 找不到閉嘴貼圖：{texture_normal}")

if os.path.exists(texture_talking):
    with open(texture_talking, "rb") as f:
        b64_talking = base64.b64encode(f.read()).decode()
else:
    st.error(f"❌ 找不到開口貼圖：{texture_talking}")

# 3. 檢查 3D 檔案是否存在並讀取
if os.path.exists(model_filename):
    with open(model_filename, "rb") as f:
        bytes_data = f.read()
    b64_model = base64.b64encode(bytes_data).decode()

    # 4. 🚀 終極防錯：乾乾淨淨的一段大字串，結尾絕對閉合
    raw_html = """
<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>

<div style="display: flex; flex-direction: column; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 15px;">
    <button id="unlock-audio-btn" style="background-color: #00CC66; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; margin-bottom: 10px; font-weight: bold; width: 100%;">
        🔊 系統啟動步驟：請先點擊此處解鎖喇叭 (啟用雙模型同步引擎)
    </button>

    <div style="position: relative; width: 100%; height: 450px; background: #2a2a35; border-radius: 10px; overflow: hidden;">
        <model-viewer 
            id="model-idle" 
            src="data:application/octet-stream;base64,__B64_MODEL__" 
            interaction-prompt="none" 
            camera-controls 
            autoplay 
            loop 
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1;">
        </model-viewer>

        <model-viewer 
            id="model-talk" 
            src="data:application/octet-stream;base64,__B64_MODEL__" 
            interaction-prompt="none" 
            autoplay 
            loop 
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 2; opacity: 0; pointer-events: none; transition: opacity 0.05s ease;">
        </model-viewer>
    </div>

    <div style="background-color: #000000; width: 100%; padding: 10px; border-radius: 8px; margin-top: 10px; border: 1px solid #444;">
        <p id="status-debug" style="color: #00FF00; font-size: 13px; font-family: monospace; margin: 0;">系統狀態: 等待點擊綠色按鈕解鎖...</p>
        <p id="data-debug" style="color: #FFCC00; font-size: 12px; font-family: monospace; margin: 5px 0 0 0; word-break: break-all;">Firebase 監聽狀態: 等待連線中...</p>
    </div>
</div>

<script type="module">
    import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
    import { getDatabase, ref, onValue } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

    const model
