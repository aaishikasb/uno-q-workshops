"""Export and check every possible eight-choice input against PyTorch."""

import hashlib
import itertools
import json
from importlib.metadata import version
from pathlib import Path

import torch
from executorch.backends.xnnpack.partition.xnnpack_partitioner import XnnpackPartitioner
from executorch.exir import to_edge_transform_and_lower
from executorch.runtime import Runtime

from train import HERE, model

DESTINATION = HERE.parent / "workshop-app" / "python" / "models"


def main():
    torch.set_num_threads(1)
    net = model().eval()
    net.load_state_dict(torch.load(HERE / "opponent.pt", weights_only=True))
    inputs = (torch.ones(1, 8),)
    program = to_edge_transform_and_lower(
        torch.export.export(net, inputs), partitioner=[XnnpackPartitioner()]
    ).to_executorch()
    delegates = [d.id for d in program.executorch_program.execution_plan[0].delegates]
    assert "XnnpackBackend" in delegates, delegates
    DESTINATION.mkdir(parents=True, exist_ok=True)
    # Validate the candidate before replacing the distributed artifact.
    candidate = DESTINATION / "opponent.tmp.pte"
    candidate.write_bytes(program.buffer)
    try:
        method = Runtime.get().load_program(str(candidate)).load_method("forward")
        fixtures, maximum_error = [], 0.0
        with torch.no_grad():
            for history in itertools.product((-1, 1), repeat=8):
                x = torch.tensor([history], dtype=torch.float32)
                expected = net(x)
                actual = method.execute([x])[0]
                torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-5)
                assert actual.argmax().item() == expected.argmax().item()
                maximum_error = max(maximum_error, (actual - expected).abs().max().item())
                fixtures.append({"history": history, "logits": expected[0].tolist()})
        metadata = {
            "version": 1, "input_shape": [1, 8], "input_dtype": "float32",
            "encoding": {"left": -1, "right": 1}, "labels": ["left", "right"],
            "history_order": "oldest_first", "delegates": delegates,
            "executorch": version("executorch"), "torch": version("torch").split("+")[0],
            "sha256": hashlib.sha256(program.buffer).hexdigest(),
            "parity_max_absolute_error": maximum_error,
        }
        candidate.replace(DESTINATION / "opponent.pte")
        (DESTINATION / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        (DESTINATION / "fixtures.json").write_text(json.dumps(fixtures, separators=(",", ":")) + "\n")
        print(f"Exported {len(program.buffer)} bytes; XNNPACK; all 256 histories agree; max error {maximum_error:.3g}")
    finally:
        candidate.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
