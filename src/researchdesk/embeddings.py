"""Local ONNX MiniLM, attention-mask mean pooling, L2 normalization."""

import json
from functools import lru_cache

import numpy as np
import onnxruntime as ort
from huggingface_hub import snapshot_download
from tokenizers import Tokenizer

from .config import settings

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
ort.disable_telemetry_events()


def download_embeddings() -> str:
    path = snapshot_download(
        EMBED_MODEL,
        revision=EMBED_REVISION,
        allow_patterns=["tokenizer.json", "onnx/model_qint8_arm64.onnx", "LICENSE", "README.md"],
        cache_dir=settings.data_dir / "models" / "hf",
    )
    metadata = {
        "model": EMBED_MODEL,
        "revision": path.split("/")[-1],
        "file": "onnx/model_qint8_arm64.onnx",
        "license": "Apache-2.0",
        "pooling": "attention-mask mean; L2 normalization",
        "max_tokens": 256,
    }
    target = settings.data_dir / "runtime" / "embeddings.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({**metadata, "path": path}, indent=2))
    return path


class Embedder:
    def __init__(self):
        config = json.loads((settings.data_dir / "runtime" / "embeddings.json").read_text())
        path = config["path"]
        self.tokenizer = Tokenizer.from_file(f"{path}/tokenizer.json")
        self.tokenizer.enable_truncation(max_length=256)
        self.tokenizer.enable_padding()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self.session = ort.InferenceSession(
            f"{path}/onnx/model_qint8_arm64.onnx", options, providers=["CPUExecutionProvider"]
        )

    def encode(self, texts: list[str]) -> list[list[float]]:
        result = []
        for i in range(0, len(texts), 24):
            enc = self.tokenizer.encode_batch(texts[i : i + 24])
            data = {
                "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
                "token_type_ids": np.array([e.type_ids for e in enc], dtype=np.int64),
            }
            data = {x.name: data[x.name] for x in self.session.get_inputs()}
            tokens = self.session.run(None, data)[0]
            mask = data["attention_mask"][..., None]
            pooled = (tokens * mask).sum(axis=1) / mask.sum(axis=1).clip(min=1)
            pooled /= np.linalg.norm(pooled, axis=1, keepdims=True).clip(min=1e-12)
            result.extend(pooled.astype(float).tolist())
        return result


@lru_cache(maxsize=1)
def embedder() -> Embedder:
    return Embedder()
