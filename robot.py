import streamlit as st
import base64
import os

# 1. 設定網頁標題與基本樣式
st.set_page_config(page_title="🤖 機器人控制台", layout="centered")
st.title("🤖 我的面板機器人")
st.write("目前狀態：🟢 鎖定骨架動畫 `armature.001` 進行引擎解鎖。")

# 設定你的 3D 模型檔名
model_filename = "robot.glb"

# 2. 檢查 3D 檔案是否存在並讀取
if os.path.exists(model_filename):
    with open(model_filename, "rb") as f:
        bytes_data = f.read()
    b64_model = base64.b64encode(bytes_data).decode()

    # 3. 嵌入 Google 3D 渲染器（加入強大的智慧名稱比對腳本）
    html_code = f"""
    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
    
    <div style="display: flex; justify-content: center; align-items: center; background-color: #1E1E24; border-radius: 15px; padding: 10px;">
        <model-viewer 
            id="blender-robot"
            src="data:application/octet-stream;base64,{b64_model}" 
            alt="3D 機器人模型" 
            camera-controls 
            style="width: 100%; height: 500px;">
        </model-viewer>
    </div>

    <script>
        const modelViewer = document.querySelector("#blender-robot");

        modelViewer.addEventListener("load", () => {{
            // 讀取這隻機器人身上所有被封裝進來的動畫名稱清單
            const anims = modelViewer.availableAnimations;
            console.log("模型內建動畫清單:", anims);

            // 智慧防錯比對：不管是小寫 armature.001、大寫 Armature.001 還是被打包成 Armature.001Action
            let matchedAnimation = anims.find(name => 
                name.toLowerCase().includes("armature.001")
            );

            // 如果找不到符合的，就直接抓第一個動畫（保底機制）
            if (!matchedAnimation && anims.length > 0) {{
                matchedAnimation = anims[0];
            }}

            if (matchedAnimation) {{
                // 鎖定動畫並設定循環播放
                modelViewer.animationName = matchedAnimation;
                modelViewer.loop = true;
                
                // 延遲 150 毫秒強制網頁底層渲染器推動 play()
                setTimeout(() => {{
                    modelViewer.play();
                }}, 150);
            }}
        }});
    </script>
    """
    
    # 4. 畫出 3D 畫面並維持高度
    st.components.v1.html(html_code, height=530)
    st.success("🟢 網頁 3D 核心已對接 Blender 動態軌道！")

else:
    st.error(f"❌ 系統在專案中找不到【{model_filename}】檔案！")
