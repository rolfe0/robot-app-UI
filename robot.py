import streamlit as st
import base64
import os

# 1. 設定網頁標題與基本樣式
st.set_page_config(page_title="🤖 機器人控制台", layout="centered")
st.title("🤖 我的面板機器人")
st.write("目前狀態：🟢 透過指定動畫名稱強制執行播放。")

# 設定你的 3D 模型檔名
model_filename = "robot.glb"

# 2. 檢查 3D 檔案是否存在並讀取
if os.path.exists(model_filename):
    with open(model_filename, "rb") as f:
        bytes_data = f.read()
    b64_model = base64.b64encode(bytes_data).decode()

    # 3. 嵌入 Google 3D 渲染器
    html_code = f"""
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    
    <div style="display: flex; justify-content: center; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 10px;">
        <model-viewer 
            id="precise-robot"
            src="data:application/octet-stream;base64,{b64_model}" 
            alt="3D 機器人模型" 
            autoplay
            loop
            camera-controls 
            style="width: 100%; height: 500px;">
        </model-viewer>
    </div>

    <script>
        const modelViewer = document.querySelector("#precise-robot");
        
        // 💥 使用你指定的精準名稱：armature.001
        const targetAnimation = "armature.001";

        modelViewer.addEventListener("load", () => {{
            // 強制將渲染器的動畫名稱指向它
            modelViewer.animationName = targetAnimation;
            modelViewer.loop = true;
            
            // 稍作延遲強制引擎啟動
            setTimeout(() => {{
                modelViewer.play();
            }}, 100);
        }});
    </script>
    """
    
    # 4. 畫出 3D 畫面並維持高度
    st.components.v1.html(html_code, height=530)
    st.success(f"🟢 網頁 3D 視區已同步！已嘗試強制播放：{targetAnimation}")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
