"""Local adapters only. No credentials, paid calls, or model-written tools."""

import json
import threading
import time
from functools import lru_cache
from urllib.parse import urlparse

import httpx
from huggingface_hub import snapshot_download

from .config import settings


def download_llm() -> str:
    if settings.llm_model != "mlx-community/Qwen2.5-1.5B-Instruct-4bit":
        raise ValueError("Model downloader is restricted to the reviewed default model and license")
    path = snapshot_download(
        settings.llm_model,
        revision="8b403126fc14f14cfc99bb4cfa72ecbc129ea677",
        cache_dir=settings.data_dir / "models" / "hf",
    )
    target = settings.data_dir / "runtime" / "llm.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "model": settings.llm_model,
                "revision": path.split("/")[-1],
                "license": "Apache-2.0",
                "path": path,
                "quantization": "4bit MLX",
            },
            indent=2,
        )
    )
    return path


class MLXProvider:
    def __init__(self):
        # Import/load only on first inference. The health endpoint never loads a model.
        from mlx_lm import load

        self.metadata = json.loads((settings.data_dir / "runtime" / "llm.json").read_text())
        self.model, self.tokenizer = load(self.metadata["path"])
        self.lock = threading.Lock()

    def generate(
        self, messages: list[dict], timeout_seconds: float | None = None
    ) -> tuple[str, dict]:
        from mlx_lm import stream_generate
        from mlx_lm.sample_utils import make_sampler

        if not self.lock.acquire(blocking=False):
            raise RuntimeError("Local model is busy; retry after the current request")
        try:
            prompt = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            start = time.monotonic()
            chunks, last = [], None
            for part in stream_generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=settings.llm_max_tokens,
                sampler=make_sampler(temp=0),
            ):
                if time.monotonic() - start > (timeout_seconds or settings.llm_timeout):
                    raise TimeoutError("Local model exceeded the inference time budget")
                chunks.append(part.text)
                last = part
            return "".join(chunks), {
                "provider": "mlx",
                **{k: v for k, v in self.metadata.items() if k != "path"},
                "temperature": 0,
                "max_tokens": settings.llm_max_tokens,
                "elapsed_seconds": time.monotonic() - start,
                "prompt_tokens": last.prompt_tokens if last else 0,
                "generation_tokens": last.generation_tokens if last else 0,
            }
        finally:
            self.lock.release()


class LocalHTTPProvider:
    def generate(self, messages, timeout_seconds=None):
        parsed = urlparse(settings.local_llm_url)
        if parsed.hostname not in ("127.0.0.1", "localhost", "::1", "host.docker.internal"):
            raise ValueError("Hosted providers require separate authorization and are disabled")
        start = time.monotonic()
        response = httpx.post(
            settings.local_llm_url,
            json={
                "model": settings.llm_model,
                "messages": messages,
                "temperature": 0,
                "max_tokens": settings.llm_max_tokens,
            },
            timeout=timeout_seconds or settings.llm_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"], {
            "provider": "local-http",
            "model": settings.llm_model,
            "elapsed_seconds": time.monotonic() - start,
            "usage": payload.get("usage"),
            "temperature": 0,
        }


@lru_cache(maxsize=1)
def provider():
    if settings.llm_backend == "mlx":
        return MLXProvider()
    if settings.llm_backend == "local-http":
        return LocalHTTPProvider()
    raise RuntimeError("No authorized local model backend configured")
