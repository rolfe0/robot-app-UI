function playIncomingAudio(audioUrlStr) {
            try {
                // 中斷前一條
                if (currentAudio) {
                    currentAudio.pause();
                    currentAudio = null;
                }

                currentAudio = new Audio(audioUrlStr);

                currentAudio.addEventListener("play", () => {
                    statusDebug.innerText = "🎵 雲端語音播放中，機器人張嘴說話中...";
                    // 🌟 這裡改成：播放時「一次性」切換為張嘴貼圖，不再使用 setInterval 閃爍
                    safeApplyTexture(textureTalkingObj);
                });

                currentAudio.addEventListener("ended", () => {
                    // 🌟 這裡改成：播放結束時切回閉嘴貼圖
                    safeApplyTexture(textureNormalObj);
                    statusDebug.innerText = "🟢 語音播放完畢，持續監聽...";
                });

                currentAudio.addEventListener("error", () => {
                    safeApplyTexture(textureNormalObj);
                    statusDebug.innerText = "❌ 音訊解碼失敗。";
                });

                currentAudio.play().catch(err => {
                    statusDebug.innerText = "❌ 播放失敗: " + err.message;
                });

            } catch (err) { console.error(err); }
        }
