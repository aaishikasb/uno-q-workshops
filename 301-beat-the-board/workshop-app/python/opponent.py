import hashlib
import json
import math
import time
from importlib.metadata import version
from pathlib import Path


def validate_history(history):
    if len(history) != 8 or any(type(v) is not int or v not in (-1, 1) for v in history):
        raise ValueError("History must contain exactly eight left (-1) or right (+1) choices")


def choose(logits):
    if len(logits) != 2 or not all(math.isfinite(v) for v in logits):
        raise ValueError("The model must return two finite logits")
    return -1 if logits[0] >= logits[1] else 1


class Opponent:
    def __init__(self, directory=None):
        import torch
        from executorch.runtime import Runtime

        started = time.perf_counter()
        directory = Path(directory) if directory else Path(__file__).parent / "models"
        self.metadata = json.loads((directory / "metadata.json").read_text())
        required = {
            "version": 1, "input_shape": [1, 8], "input_dtype": "float32",
            "encoding": {"left": -1, "right": 1}, "labels": ["left", "right"],
            "history_order": "oldest_first", "executorch": version("executorch"),
            "torch": version("torch").split("+")[0],
            "delegates": ["XnnpackBackend"],
        }
        if any(self.metadata.get(key) != value for key, value in required.items()):
            raise ValueError("Model contract or runtime version mismatch; restore the supplied model and requirements")
        path = directory / "opponent.pte"
        if hashlib.sha256(path.read_bytes()).hexdigest() != self.metadata.get("sha256"):
            raise ValueError("Model checksum mismatch; copy opponent.pte and metadata.json together")
        runtime = Runtime.get()
        if not runtime.backend_registry.is_available("XnnpackBackend"):
            raise RuntimeError("This ExecuTorch installation has no XNNPACK backend")
        torch.set_num_threads(1)
        self.torch = torch
        self.method = runtime.load_program(str(path)).load_method("forward")
        self.logits([-1] * 8)
        self.load_ms = (time.perf_counter() - started) * 1000

    def logits(self, history):
        validate_history(history)
        x = self.torch.tensor([history], dtype=self.torch.float32)
        outputs = self.method.execute([x])
        if len(outputs) != 1 or tuple(outputs[0].shape) != (1, 2):
            raise ValueError("Unexpected model output shape")
        values = outputs[0][0].tolist()
        choose(values)
        return values

    def predict(self, history):
        return choose(self.logits(history))
