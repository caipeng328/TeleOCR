"""Validation shared by synchronous and asynchronous region extraction."""

import math


class RegionExtractionError(ValueError):
    """A detected region could not be safely submitted for recognition."""


def validate_bbox(bbox, width, height, index):
    if not isinstance(bbox, (list, tuple)) or len(bbox) < 4 or len(bbox) % 2:
        raise RegionExtractionError(f"Region {index}: invalid coordinate count")
    if any(not isinstance(v, (int, float)) or isinstance(v, bool)
           or not math.isfinite(v) or not 0 <= v <= 1 for v in bbox):
        raise RegionExtractionError(f"Region {index}: coordinates must be finite and normalized")
    points = [(int(bbox[i] * width), int(bbox[i + 1] * height))
              for i in range(0, len(bbox), 2)]
    if len(points) == 2:
        valid = points[1][0] > points[0][0] and points[1][1] > points[0][1]
    else:
        area = sum(x * points[(i + 1) % len(points)][1]
                   - points[(i + 1) % len(points)][0] * y
                   for i, (x, y) in enumerate(points))
        valid = area != 0
    if not valid:
        raise RegionExtractionError(f"Region {index}: crop has zero area or reversed bounds")
    return points


def validate_output_count(indices, outputs):
    # Validate before assigning any output, so a mismatch cannot partially
    # mutate the page and masquerade as a successful recognition.
    if len(indices) != len(outputs):
        raise RegionExtractionError(
            f"Recognition result count mismatch: expected {len(indices)}, got {len(outputs)}"
        )
