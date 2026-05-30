import streamlit as st
import base64
import os

# 1. 設定網頁標題與基本樣式
st.set_page_config(page_title="🤖 機器人控制台", layout="centered")
st.title("🤖 我的面板機器人")
st.write("目前狀態：🟢 正在嘗試精準匹配動畫軌道 `mixamo.com.001`。")

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
            id="mixamo-robot"
            src="data:application/octet-stream;base64,{b64_model}" 
            alt="3D 機器人模型" 
            camera-controls 
            style="width: 100%; height: 500px;">
        </model-viewer>
    </div>

    <script>
        const modelViewer = document.querySelector("#mixamo-robot");

        modelViewer.addEventListener("load", () => {{
            const anims = modelViewer.availableAnimations;
            console.log("網頁偵測到的動畫清單:", anims);

            // 💥 鎖定你說的特定名稱（忽略大小寫，並檢查是否包含 mixamo.com.001）
            let targetAnim = anims.find(name => 
                name.toLowerCase().includes("mixamo.com.001")
            );

            // 如果找不到，就用原本的 armature.001 或是第一個動畫當備案，確保絕對不會卡死
            if (!targetAnim) {{
                targetAnim = anims.find(name => name.toLowerCase().includes("armature.001")) || anims[0];
            }}

            if (targetAnim) {{
                modelViewer.animationName = targetAnim;
                modelViewer.loop = true;
                
                // 延遲 150 毫秒強力解鎖播放
                setTimeout(() => {{
                    modelViewer.play();
                }}, 150);
            }}
        }});
    </script>
    """
    
    # 4. 畫出 3D 畫面並維持高度
    st.components.v1.html(html_code, height=530)
    st.success("🟢 網頁 3D 核心已重新載入！")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
