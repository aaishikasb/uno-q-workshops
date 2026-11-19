"""Run inside the same Python environment as the app; no Bridge required."""

import json
import math
import platform
import statistics
import time
from importlib.metadata import version
from pathlib import Path

from opponent import Opponent, choose


def check():
    opponent = Opponent()
    fixtures = json.loads((Path(__file__).parent / "models" / "fixtures.json").read_text())
    if len(fixtures) != 256:
        raise ValueError("Expected fixtures for all 256 possible histories")
    timings, error = [], 0.0
    for fixture in fixtures:
        start = time.perf_counter()
        actual = opponent.logits(fixture["history"])
        timings.append((time.perf_counter() - start) * 1000)
        expected = fixture["logits"]
        if not all(math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-5) for a, b in zip(actual, expected)):
            raise ValueError(f"Runtime parity failed for {fixture['history']}")
        if choose(actual) != choose(expected):
            raise ValueError("Runtime selected a different label")
        error = max(error, *(abs(a - b) for a, b in zip(actual, expected)))
    peak_mib = None
    if platform.system() != "Windows":
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak_mib = round(rss / (1024 ** 2 if platform.system() == "Darwin" else 1024), 1)
    report = {
        "platform": platform.platform(), "machine": platform.machine(),
        "python": platform.python_version(),
        "executorch": version("executorch"), "torch": version("torch"),
        "backend": "XnnpackBackend", "histories_checked": len(fixtures),
        "max_absolute_error": error, "load_ms": round(opponent.load_ms, 2),
        "warm_median_ms": round(statistics.median(timings), 3),
        "warm_p95_ms": round(sorted(timings)[int(len(timings) * 0.95)], 3),
        "process_peak_rss_mib": peak_mib,
    }
    os_release = Path("/etc/os-release")
    if os_release.exists():
        report["os_release"] = os_release.read_text()
    return report


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
