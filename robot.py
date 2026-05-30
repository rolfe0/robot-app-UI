import streamlit as st
import base64
import os

# 1. 設定網頁標題與基本樣式
st.set_page_config(page_title="🤖 機器人控制台", layout="centered")
st.title("🤖 我的面板機器人")
st.write("目前狀態：🟢 動畫速度已調慢至 0.0001 極致定格慢動作播放中。")

# 設定你的 3D 模型檔名
model_filename = "robot.glb"

# 2. 檢查 3D 檔案是否存在並讀取
if os.path.exists(model_filename):
    with open(model_filename, "rb") as f:
        bytes_data = f.read()
    b64_model = base64.b64encode(bytes_data).decode()

    # 3. 嵌入 Google 3D 渲染器（將 time-scale 設定為 0.0001）
    html_code = f"""
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    
    <div style="display: flex; justify-content: center; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 10px;">
        <model-viewer 
            id="ultra-slow-robot"
            src="data:application/octet-stream;base64,{b64_model}" 
            alt="3D 機器人模型" 
            camera-controls 
            autoplay
            loop
            time-scale="0.0001"
            style="width: 100%; height: 500px;">
        </model-viewer>
    </div>

    <script>
        const modelViewer = document.querySelector("#ultra-slow-robot");

        modelViewer.addEventListener("load", () => {{
            const anims = modelViewer.availableAnimations;
            console.log("網頁偵測到的動畫清單:", anims);

            // 優先尋找 mixamo.com.001
            let targetAnim = anims.find(name => name.toLowerCase().includes("mixamo.com.001"));

            // 備案尋找 armature.001
            if (!targetAnim) {{
                targetAnim = anims.find(name => name.toLowerCase().includes("armature.001"));
            }}

            // 終極保底：抓第一個動畫
            if (!targetAnim && anims.length > 0) {{
                targetAnim = anims[0];
            }}

            if (targetAnim) {{
                modelViewer.animationName = targetAnim;
                
                // 延遲強制播放
                setTimeout(() => {{
                    modelViewer.play();
                }}, 150);
            }}
        }});
    </script>
    """
    
    # 4. 畫出 3D 畫面並維持高度
    st.components.v1.html(html_code, height=530)
    st.success("🟢 網頁 3D 核心已更新至 0.0001 倍速！")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
