"""Dependency-free feature extraction and classification for knob gestures."""

import json
import math
from pathlib import Path


MODEL_VERSION = 1
SHAPE_POINTS = 12


def _resample(values, point_count):
    if not values:
        return [0.0] * point_count
    if len(values) == 1:
        return [float(values[0])] * point_count

    result = []
    final_index = len(values) - 1
    for point in range(point_count):
        position = point * final_index / (point_count - 1)
        left = int(math.floor(position))
        right = min(left + 1, final_index)
        fraction = position - left
        value = values[left] + (values[right] - values[left]) * fraction
        result.append(float(value))
    return result


def extract_features(samples):
    """Convert raw knob positions into a fixed-length gesture representation."""
    if len(samples) < 3:
        raise ValueError("A gesture needs at least three samples")

    values = [float(value) for value in samples]
    deltas = [values[index] - values[index - 1] for index in range(1, len(values))]
    active = [index for index, delta in enumerate(deltas, start=1) if abs(delta) >= 1.0]
    if not active:
        raise ValueError("No knob movement detected")

    start = max(0, active[0] - 1)
    end = min(len(values) - 1, active[-1] + 1)
    path = values[start : end + 1]
    relative_path = [value - path[0] for value in path]
    path_deltas = [
        relative_path[index] - relative_path[index - 1]
        for index in range(1, len(relative_path))
    ]

    travel = sum(abs(delta) for delta in path_deltas)
    if travel < 1.0:
        raise ValueError("Gesture movement is too small")

    amplitude = max(max(abs(value) for value in relative_path), 1.0)
    normalized_path = [value / amplitude for value in relative_path]
    shape = _resample(normalized_path, SHAPE_POINTS)

    nonzero_signs = [1 if delta > 0 else -1 for delta in path_deltas if abs(delta) >= 1.0]
    reversals = sum(
        1
        for index in range(1, len(nonzero_signs))
        if nonzero_signs[index] != nonzero_signs[index - 1]
    )

    net = relative_path[-1]
    peak_step = max(abs(delta) for delta in path_deltas)
    duration = min(len(path) / 32.0, 1.0)

    return shape + [
        net / travel,
        min(reversals, 6) / 6.0,
        duration,
        peak_step / travel,
    ]


def _distance(left, right):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)) / len(left))


def _standardize(features, means, scales):
    return [
        (value - mean) / scale
        for value, mean, scale in zip(features, means, scales)
    ]


def train(examples):
    """Train a nearest-centroid classifier from {label: feature rows}."""
    labels = sorted(examples)
    if len(labels) < 2:
        raise ValueError("At least two gesture labels are required")

    rows = [row for label in labels for row in examples[label]]
    if not rows or any(not examples[label] for label in labels):
        raise ValueError("Every gesture label needs at least one example")

    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("All feature rows must have the same length")

    means = [sum(row[index] for row in rows) / len(rows) for index in range(width)]
    scales = []
    for index, mean in enumerate(means):
        variance = sum((row[index] - mean) ** 2 for row in rows) / len(rows)
        scales.append(max(math.sqrt(variance), 0.05))

    standardized = {
        label: [_standardize(row, means, scales) for row in examples[label]]
        for label in labels
    }

    centroids = {}
    radii = {}
    for label in labels:
        label_rows = standardized[label]
        centroid = [
            sum(row[index] for row in label_rows) / len(label_rows)
            for index in range(width)
        ]
        distances = [_distance(row, centroid) for row in label_rows]
        centroids[label] = centroid
        radii[label] = max(max(distances), 0.35)

    return {
        "version": MODEL_VERSION,
        "labels": labels,
        "means": means,
        "scales": scales,
        "centroids": centroids,
        "radii": radii,
    }


def predict(model, features):
    """Return label, confidence, distance, and whether the sample is in-distribution."""
    standardized = _standardize(features, model["means"], model["scales"])
    distances = {
        label: _distance(standardized, model["centroids"][label])
        for label in model["labels"]
    }
    ordered = sorted(distances, key=distances.get)
    label = ordered[0]
    best_distance = distances[label]

    minimum = min(distances.values())
    scores = {
        candidate: math.exp(-2.0 * (distance - minimum))
        for candidate, distance in distances.items()
    }
    score_total = sum(scores.values())
    confidence = scores[label] / score_total
    in_distribution = best_distance <= model["radii"][label] * 2.0 + 0.5

    return {
        "label": label,
        "confidence": confidence,
        "distance": best_distance,
        "accepted": confidence >= 0.58 and in_distribution,
        "distances": distances,
    }


def save(model, path):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(model, indent=2), encoding="utf-8")
    temporary.replace(destination)


def load(path):
    source = Path(path)
    if not source.exists():
        return None

    model = json.loads(source.read_text(encoding="utf-8"))
    if model.get("version") != MODEL_VERSION:
        raise ValueError("Saved gesture model uses an unsupported version")
    return model
