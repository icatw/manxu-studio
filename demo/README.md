# 汇报录屏（AI 旁白 + 真实产品画面）

本目录脚本、讲稿与成品会随仓库提交；`out/` 里只保留可复用交付物，中间编码缓存见 `out/.gitignore`。

## 仓库内成品

| 路径 | 说明 |
| --- | --- |
| `narration.txt` / `product-narration.txt` | 汇报 / 产品段讲稿 |
| `chapters.json` | 介绍页幻灯片文案 |
| `out/manxu-studio-demo-final.mp4` | 完整汇报片（旁白 + 字幕 + 真机录屏） |
| `out/narration.mp3` · `out/product-narration.mp3` | edge-tts 旁白 |
| `out/narration.srt` · `out/product-narration.srt` | 字幕 |
| `out/product-live.webm` | 主栈 headed Chrome 录屏素材 |
| `out/slides/` | 介绍页静态帧 |
| [`docs/media/`](../docs/media/) | README 用截图 + 压缩演示视频 |

合成时产品段按**旁白时长裁画面**，不再用静音垫齐。

## 重新生成

1. 主栈已启动（`./scripts/start.sh`，不是 playground）
2. 在 api 容器里为真实账户签发 cookie：

```sh
docker cp demo/mint_for_account.py kaiying-api-1:/tmp/
docker exec -w /app kaiying-api-1 uv run python /tmp/mint_for_account.py <account-uuid>
```

3. 有界面录屏（会弹出 Chrome）：

```sh
COOKIE_VALUE='…' PROJECT_ID='…' EPISODE_ID='…' node demo/record_live.mjs
```

4. 旁白与合成：

```sh
python3 demo/generate_voice.py
python3 demo/generate_voice.py --text demo/product-narration.txt --out demo/out/product-narration.mp3
python3 demo/render_slides.py
./demo/mux_final.sh
```

## 语音怎么生成的？

使用 Python 包 **edge-tts**：调用 **微软 Edge 在线神经 TTS**（与 Edge「大声朗读」同一类云端语音服务），默认音色 `zh-CN-YunxiNeural`。

- 需要联网；**不是**本地开源语音模型，也**不是** OpenAI / 通义的语音 API。
- 合成时同时拿到 Word/Sentence 边界，写成 `out/*.srt`，再烧录进视频当字幕。
- 换音色：`python3 demo/generate_voice.py --voice zh-CN-XiaoxiaoNeural`
