import streamlit as st
import base64
import os
import json

# 1. 設定網頁標題與外觀
st.set_page_config(page_title="🤖 AI 語音雙圖切換看板", layout="centered")
st.title("🤖 AI 語音動態口型 (雙整體貼圖精準切換版)")
st.write("目前狀態：🟢 雙圖精準切換引擎已啟動！當聲音響起時，會直接將模型材質替換成開口貼圖檔案。")

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

# 檔案名稱定義（請確保專案目錄下有這兩個完整的貼圖檔案）
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

    # 4. 定義 HTML 網頁核心
    raw_html = """
    <script type="module" src="
