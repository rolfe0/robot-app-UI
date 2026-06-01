import streamlit as st
import base64
import os
import json

st.set_page_config(page_title="🤖 雲端語音接收看板", layout="centered")
st.title("🤖 雲端語音同步面板 (音訊內置觸發版)")
st.write("目前狀態：🟢 機制已優化！現在 Firebase 的 test 欄位只要「隨便改數字或打字」，就會自動觸發播放內建的 5 秒長逼聲，並瘋狂動嘴！")

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
        b64_talking = base64.b64encode(f.
