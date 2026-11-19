"""Reproducible synthetic training and evaluation; no player data is collected."""

import json
import random
from pathlib import Path

import torch
from torch import nn

HERE = Path(__file__).resolve().parent
FAMILIES = ("repeat", "alternate", "pairs", "biased", "noisy", "switch", "random")


def model():
    return nn.Sequential(nn.Linear(8, 32), nn.ReLU(), nn.Linear(32, 2))


def sequences(seed, family, count=64):
    rng = random.Random(seed)
    for _ in range(count):
        side = rng.choice((-1, 1))
        patterns = {
            "repeat": [side], "alternate": [side, -side],
            "pairs": [side, side, -side, -side],
            "unseen_triplets": [side] * 3 + [-side] * 3,
        }
        pattern = patterns.get(family, rng.choice([[side], [side, -side], [side, side, -side, -side]]))
        offset = rng.randrange(len(pattern))
        row = []
        for i in range(72):
            value = pattern[(i + offset) % len(pattern)]
            if family == "random":
                value = rng.choice((-1, 1))
            elif family == "biased":
                value = side if rng.random() < 0.8 else -side
            elif family == "noisy" and rng.random() < 0.12:
                value = -value
            elif family == "switch" and i >= 36:
                value = side if i % 2 else -side
            row.append(value)
        yield row


def dataset(seed, families=FAMILIES):
    rows, targets = [], []
    # Assign seeds to whole sequences before extracting overlapping windows.
    for index, family in enumerate(families):
        for sequence in sequences(seed + index, family):
            for end in range(8, len(sequence)):
                rows.append(sequence[end - 8:end])
                targets.append(int(sequence[end] == 1))
    return torch.tensor(rows, dtype=torch.float32), torch.tensor(targets)


def evaluate(net):
    report = {}
    for index, family in enumerate((*FAMILIES, "unseen_triplets")):
        x, y = dataset(9000 + index, (family,))
        rng = random.Random(300 + index)
        with torch.no_grad():
            predictions = net(x).argmax(1)
        choices = {
            "model": predictions,
            "repeat": (x[:, -1] == 1).long(),
            "opposite": (x[:, -1] == -1).long(),
            "random": torch.tensor([rng.randrange(2) for _ in y]),
        }
        report[family] = {name: round((values == y).float().mean().item(), 4)
                          for name, values in choices.items()}
        report[family]["examples"] = len(y)
    return report


def main():
    torch.manual_seed(301)
    torch.set_num_threads(1)
    net = model()
    x, y = dataset(3010)
    optimizer = torch.optim.Adam(net.parameters(), lr=0.01)
    for _ in range(600):
        optimizer.zero_grad()
        loss = nn.functional.cross_entropy(net(x), y)
        loss.backward()
        optimizer.step()
    net.eval()
    report = evaluate(net)
    assert all(report[f]["model"] > 0.9 for f in ("repeat", "alternate", "pairs"))
    assert 0.45 < report["random"]["model"] < 0.55
    torch.save(net.state_dict(), HERE / "opponent.pt")
    (HERE / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
