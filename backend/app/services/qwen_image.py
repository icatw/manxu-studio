import asyncio
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.security import validate_public_https_url


async def generate_qwen_image(
    *, api_key: str, model: str, prompt: str, asset_id: UUID, base_url: str | None = None
) -> str:
    settings = get_settings()
    configured_base_url = base_url or settings.qwen_image_base_url
    await validate_public_https_url(configured_base_url)
    configured = urlsplit(configured_base_url)
    path = configured.path.rstrip("/")
    if path.endswith("/compatible-mode/v1"):
        path = path[: -len("/compatible-mode/v1")]
    if not path.endswith("/api/v1"):
        path = f"{path}/api/v1" if path else "/api/v1"
    base_url = urlunsplit((configured.scheme, configured.netloc, path, "", "")).rstrip("/")
    endpoint = f"{base_url}/services/aigc/image-generation/generation"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    timeout = httpx.Timeout(45, connect=10)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        response = await client.post(
            endpoint,
            headers=headers,
            json={
                "model": model,
                "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
                "parameters": {"size": "1024*1024", "prompt_extend": True},
            },
        )
        if not response.is_success:
            if response.status_code in {401, 403}:
                raise ValueError("Qwen Image 认证失败，请检查图像 API Key")
            raise ValueError(f"Qwen Image 提交失败（HTTP {response.status_code}）")
        task_id = response.json().get("output", {}).get("task_id")
        if not task_id:
            raise ValueError("Qwen Image 未返回异步任务编号")

        image_url = ""
        for _ in range(120):
            await asyncio.sleep(5)
            task_response = await client.get(
                f"{base_url}/tasks/{task_id}", headers={"Authorization": f"Bearer {api_key}"}
            )
            if not task_response.is_success:
                raise ValueError(f"查询 Qwen Image 任务失败（HTTP {task_response.status_code}）")
            output = task_response.json().get("output", {})
            status = output.get("task_status")
            if status == "SUCCEEDED":
                choices = output.get("choices") or []
                content = choices[0].get("message", {}).get("content", []) if choices else []
                image_item = next((item for item in content if item.get("image")), None)
                if image_item:
                    image_url = str(image_item["image"])
                break
            if status in {"FAILED", "CANCELED", "UNKNOWN"}:
                raise ValueError("Qwen Image 生成失败，请检查提示词和账户额度后重试")
        if not image_url:
            raise ValueError("Qwen Image 任务超时或未返回图像")

        await validate_public_https_url(image_url)
        download = await client.get(image_url)
        if not download.is_success:
            raise ValueError("下载 Qwen Image 结果失败")
        content_type = download.headers.get("content-type", "").split(";", 1)[0].lower()
        extensions = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
        extension = extensions.get(content_type)
        if not extension or len(download.content) > 20 * 1024 * 1024:
            raise ValueError("Qwen Image 返回了不支持的图片格式或过大的文件")

    output_dir = await asyncio.to_thread(Path(settings.image_storage_dir).resolve)
    await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)
    target = output_dir / f"{asset_id}{extension}"
    await asyncio.to_thread(target.write_bytes, download.content)
    return f"/api/v1/assets/{asset_id}"
