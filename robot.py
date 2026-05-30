import streamlit as st
import streamlit.components.v1 as components

# 1. 設定網頁標題
st.set_page_config(page_title="🤖 機器人控制台", layout="centered")
st.title("🤖 我的面板機器人")
st.write("系統提示：網頁正在從雲端載入 3D 模型，請稍等 3~5 秒...")

# =================【請檢查並修改下方兩個設定】=================
# 填入你的 GitHub 帳號名稱（大小寫要對）
github_username = "rolfe0"  

# 填入你在 GitHub 建立的英文專案名稱
github_repo = "robot-app-UI"       
# ==========================================================

# 自動生成 GitHub 原生檔案的公開下載連結
model_url = f"https://raw.githubusercontent.com/{github_username}/{github_repo}/main/robot.glb"

# 2. 嵌入 Google 開源的 3D 渲染器（直接讀取雲端網址，不吃網頁記憶體）
html_code = f"""
<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
<div style="display: flex; justify-content: center;">
    <model-viewer 
        src="{model_url}" 
        alt="3D 機器人模型" 
        auto-rotate 
        camera-controls 
        style="width: 100%; height: 500px; background-color: #1E1E24; border-radius: 15px; box-shadow: 0px 4px 12px rgba(0,0,0,0.3);">
    </model-viewer>
</div>
"""

# 將 3D 畫面畫在網頁上
components.html(html_code, height=530)

st.success("🟢 雲端連線成功！如果畫面仍未顯示，請確認 GitHub 專案是否已確實設定為 Public（公開）。")
