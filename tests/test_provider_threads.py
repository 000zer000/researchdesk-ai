import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from researchdesk.provider import MLXProvider


def isolated_provider(monkeypatch, tmp_path, generation):
    import researchdesk.provider as module

    (tmp_path / "runtime").mkdir()
    (tmp_path / "runtime/llm.json").write_text(json.dumps({"path": "EXPLICIT TEST DOUBLE"}))
    monkeypatch.setattr(module.settings, "data_dir", tmp_path)

    def load(self):
        self.owner = threading.get_ident()

    monkeypatch.setattr(MLXProvider, "_load", load)
    monkeypatch.setattr(MLXProvider, "_generate", generation)
    return MLXProvider()


def test_loading_and_generations_stay_on_the_same_owner_thread(monkeypatch, tmp_path):
    seen = []

    def generate(self, messages, timeout):
        seen.append(threading.get_ident())
        assert seen[-1] == self.owner
        return "explicit simulated output", {}

    p = isolated_provider(monkeypatch, tmp_path, generate)
    try:
        for _ in range(2):
            with ThreadPoolExecutor(max_workers=1) as caller:
                assert caller.submit(p.generate, []).result()[0] == "explicit simulated output"
        assert len(seen) == 2 and seen[0] == seen[1]
    finally:
        p.executor.shutdown(wait=True)


def test_busy_owner_rejects_a_second_generation(monkeypatch, tmp_path):
    entered, release = threading.Event(), threading.Event()

    def generate(self, messages, timeout):
        entered.set()
        assert release.wait(3)
        return "explicit simulated output", {}

    p = isolated_provider(monkeypatch, tmp_path, generate)
    try:
        with ThreadPoolExecutor(max_workers=1) as caller:
            pending = caller.submit(p.generate, [])
            assert entered.wait(3)
            try:
                with pytest.raises(RuntimeError, match="busy"):
                    p.generate([])
            finally:
                release.set()
            pending.result()
    finally:
        p.executor.shutdown(wait=True)


def test_cached_model_must_match_selected_runtime(monkeypatch, tmp_path):
    import researchdesk.provider as module

    (tmp_path / "runtime").mkdir()
    (tmp_path / "runtime/llm.json").write_text(
        json.dumps({"model": "different-model", "path": "EXPLICIT TEST DOUBLE"})
    )
    monkeypatch.setattr(module.settings, "data_dir", tmp_path)
    with pytest.raises(ValueError, match="Cached model differs"):
        MLXProvider()
