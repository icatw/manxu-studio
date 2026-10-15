"""Minimal OpenAI-compatible chat completions stub for playground tests."""

from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _plan_payload(chapter_count: int) -> dict[str, object]:
    chapters = [
        {
            "title": f"第 {index} 话 · 试炼",
            "synopsis": f"主角在第 {index} 话面对新的冲突并推进主线。",
        }
        for index in range(1, chapter_count + 1)
    ]
    return {
        "title": "永夜图书馆",
        "world_setting": "漂浮在永夜海上的图书馆，馆员收集失踪旅人的梦境续写史书。",
        "characters": [
            {
                "name": "阿澜",
                "role": "馆员",
                "appearance": "瘦高青年，深蓝长袍",
                "hairstyle": "黑色短发",
                "outfit": "绣银线的馆员袍",
                "signature_traits": ["怀表形钥匙"],
                "personality": "克制、好奇",
            },
            {
                "name": "汐",
                "role": "失踪旅人",
                "appearance": "银发少女",
                "hairstyle": "及肩银发",
                "outfit": "旅行斗篷",
                "signature_traits": ["发光笔记本"],
                "personality": "直率",
            },
        ],
        "chapters": chapters,
        "threads": [
            {
                "text": "史书缺页与失踪旅人有关",
                "planted_in": 1,
                "payoff_in": min(3, chapter_count),
            }
        ],
    }


def _summary_payload() -> dict[str, object]:
    return {
        "summary": "本话中主角进入图书馆禁区，发现上一任馆员留下的未完成记录，并与汐达成暂时同盟。"
    }


def _character_draft_payload() -> dict[str, object]:
    return {
        "characters": [
            {
                "name": "阿澜",
                "role": "馆员 / 男主",
                "appearance": "瘦高青年，深蓝长袍，眼神沉静",
                "hairstyle": "黑色短发",
                "outfit": "绣银线的馆员袍",
                "signature_traits": ["怀表形钥匙"],
                "personality": "克制、好奇",
                "reference_image_prompt": "全身立绘，深蓝馆员袍，黑色短发，怀表钥匙，纯净浅色背景",
            },
            {
                "name": "汐",
                "role": "失踪旅人 / 女主",
                "appearance": "银发少女，神情直率",
                "hairstyle": "及肩银发",
                "outfit": "旅行斗篷",
                "signature_traits": ["发光笔记本"],
                "personality": "直率",
                "reference_image_prompt": "全身立绘，旅行斗篷，及肩银发，发光笔记本，纯净浅色背景",
            },
        ]
    }


def _extract_chapter_count(text: str) -> int:
    match = re.search(r"目标话数[：:]\s*(\d+)", text) or re.search(
        r"chapters 数量必须为\s*(\d+)", text
    )
    if match:
        return max(1, min(24, int(match.group(1))))
    return 3


def _completion_content(system_prompt: str, user_prompt: str) -> str:
    combined = f"{system_prompt}\n{user_prompt}"
    if "季策划" in combined or "world_setting" in combined or "chapters" in combined:
        return json.dumps(_plan_payload(_extract_chapter_count(combined)), ensure_ascii=False)
    if "摘要" in combined or "summary" in combined.lower():
        return json.dumps(_summary_payload(), ensure_ascii=False)
    if "reference_image_prompt" in combined or "角色阵容" in combined:
        return json.dumps(_character_draft_payload(), ensure_ascii=False)
    return json.dumps({"ok": True, "echo": user_prompt[:200]}, ensure_ascii=False)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def _json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/health", "/readyz", "/v1/models"}:
            self._json(200, {"status": "ok", "data": [{"id": "fake-text"}]})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            request = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return
        messages = request.get("messages") or []
        system_prompt = ""
        user_prompt = ""
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = message.get("role")
            content = message.get("content") or ""
            if role == "system":
                system_prompt = str(content)
            elif role == "user":
                user_prompt = str(content)
        content = _completion_content(system_prompt, user_prompt)
        self._json(
            200,
            {
                "id": "chatcmpl-fake",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
            },
        )


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"fake-llm listening on :{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
