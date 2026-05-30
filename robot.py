import streamlit as st
import streamlit.components.v1 as components
import base64
import os

# 1. 設定網頁標題
st.set_page_config(page_title="🤖 機器人控制台", layout="centered")
st.title("🤖 我的面板機器人")
st.write("目前狀態：安全本地連線中...")

# 設定你的 3D 模型檔名
model_filename = "robot.glb"

# 2. 檢查檔案是否存在，並直接讀取（因為 19KB 非常小，這種讀取方式最穩最快）
if os.path.exists(model_filename):
    with open(model_filename, "rb") as f:
        bytes_data = f.read()
    b64_model = base64.b64encode(bytes_data).decode()

    # 3. 嵌入 Google 3D 渲染器
    html_code = f"""
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    <div style="display: flex; justify-content: center;">
        <model-viewer 
            src="data:application/octet-stream;base64,{b64_model}" 
            alt="3D 機器人模型" 
            auto-rotate 
            camera-controls 
            style="width: 100%; height: 500px; background-color: #1E1E24; border-radius: 15px; box-shadow: 0px 4px 12px rgba(0,0,0,0.3);">
        </model-viewer>
    </div>
    """
    # 將 3D 畫面畫在網頁上
    components.html(html_code, height=530)
    st.success("🟢 3D 模型本地載入成功！請用滑鼠拖曳轉動它看看。")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！請確認它有確實上傳到 GitHub 的最外層目錄。")
