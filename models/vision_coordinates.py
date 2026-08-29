"""Vision coordinate utilities for working with images and bounding boxes.

When Claude returns pixel coordinates (bounding boxes, points, UI element
locations), those coordinates are in the reference frame of the **resized**
image that Claude actually sees — not necessarily the original image you
uploaded.  This module provides:

* The exact resize algorithm Claude applies (matches Anthropic's reference
  implementation).
* Helpers to pre-resize images before upload so coordinates map 1:1.
* Helpers to rescale returned coordinates back to the original image.
* Bounding-box utilities: intersection-over-union, cropping, drawing.
* Structured output schemas for requesting coordinates from the model.

References
----------
* https://platform.claude.com/docs/en/build-with-claude/vision-coordinates
* https://platform.claude.com/docs/en/build-with-claude/vision
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Resolution tiers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolutionTier:
    """Image-processing resolution limits for a model tier.

    Attributes:
        name: Human-readable tier name.
        max_edge: Maximum length of either edge in pixels.
        max_visual_tokens: Maximum visual token budget.
    """

    name: str
    max_edge: int
    max_visual_tokens: int


#: Standard resolution tier (most models).
STANDARD_TIER = ResolutionTier(
    name="standard",
    max_edge=1568,
    max_visual_tokens=1568,
)

#: High-resolution tier (select models).
HIGH_RESOLUTION_TIER = ResolutionTier(
    name="high_resolution",
    max_edge=2576,
    max_visual_tokens=4784,
)

#: Map of model-id prefix → resolution tier.
_MODEL_TIERS: Dict[str, ResolutionTier] = {
    "claude-opus-5": HIGH_RESOLUTION_TIER,
    "claude-opus-4-8": HIGH_RESOLUTION_TIER,
    "claude-opus-4-7": HIGH_RESOLUTION_TIER,
    "claude-mythos-5": HIGH_RESOLUTION_TIER,
    "claude-fable-5": HIGH_RESOLUTION_TIER,
    "claude-mythos-preview": HIGH_RESOLUTION_TIER,
}


def resolution_tier_for_model(model_id: str) -> ResolutionTier:
    """Return the resolution tier for *model_id*."""
    for prefix, tier in _MODEL_TIERS.items():
        if model_id.startswith(prefix):
            return tier
    return STANDARD_TIER


# ---------------------------------------------------------------------------
# Core resize math  (matches Anthropic's reference implementation exactly)
# ---------------------------------------------------------------------------


def count_image_tokens(width: int, height: int) -> int:
    """Visual tokens consumed by an image: one token per 28×28 pixel patch."""
    return math.ceil(width / 28) * math.ceil(height / 28)


def compute_resized_size(
    width: int,
    height: int,
    max_edge: int = STANDARD_TIER.max_edge,
    max_visual_tokens: int = STANDARD_TIER.max_visual_tokens,
) -> Tuple[int, int]:
    """Compute the size Claude resizes an image to (before padding).

    This is the reference implementation from Anthropic's documentation.
    Returns ``(resized_width, resized_height)``.  Images that already fit
    within both limits are returned unchanged.

    Args:
        width: Original image width in pixels.
        height: Original image height in pixels.
        max_edge: Maximum edge length for the target tier.
        max_visual_tokens: Maximum visual token budget for the target tier.

    Returns:
        ``(new_width, new_height)`` — the size Claude actually processes.
    """

    def fits(w: int, h: int) -> bool:
        return (
            math.ceil(w / 28) * 28 <= max_edge
            and math.ceil(h / 28) * 28 <= max_edge
            and count_image_tokens(w, h) <= max_visual_tokens
        )

    if fits(width, height):
        return (width, height)

    # Recurse with axes flipped when height > width so we always scale the
    # long edge downward.
    if height > width:
        rw, rh = compute_resized_size(height, width, max_edge, max_visual_tokens)
        return (rh, rw)

    aspect = width / height
    lo, hi = 1, width  # lo always fits; hi never fits
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        h_mid = max(1, round(mid / aspect))
        if fits(mid, h_mid):
            lo = mid
        else:
            hi = mid

    new_w = lo
    new_h = max(1, round(lo / aspect))
    return (new_w, new_h)


def compute_padded_size(
    resized_width: int,
    resized_height: int,
) -> Tuple[int, int]:
    """Compute the padded size Claude uses internally.

    Claude pads every image to the next multiple of 28 px on the bottom and
    right edges.  Coordinates are relative to the **resized** (not padded)
    dimensions, so you should normalize by ``resized_width`` / ``resized_height``,
    not the padded values.
    """
    pad_w = math.ceil(resized_width / 28) * 28
    pad_h = math.ceil(resized_height / 28) * 28
    return (pad_w, pad_h)


def compute_resized_size_for_model(
    width: int,
    height: int,
    model_id: str,
) -> Tuple[int, int]:
    """Compute the resized size for a specific model's tier."""
    tier = resolution_tier_for_model(model_id)
    return compute_resized_size(
        width, height,
        max_edge=tier.max_edge,
        max_visual_tokens=tier.max_visual_tokens,
    )


# ---------------------------------------------------------------------------
# Coordinate rescaling
# ---------------------------------------------------------------------------


def rescale_coordinates(
    coords: Union[Tuple[float, float], List[float]],
    resized_width: int,
    resized_height: int,
    original_width: int,
    original_height: int,
) -> Tuple[float, float]:
    """Rescale a single ``(x, y)`` coordinate from the resized to the original image.

    Args:
        coords: ``(x, y)`` pixel coordinates in the resized image's frame.
        resized_width: Width Claude resized the image to.
        resized_height: Height Claude resized the image to.
        original_width: Original image width.
        original_height: Original image height.

    Returns:
        ``(x, y)`` in the original image's pixel frame.
    """
    x, y = float(coords[0]), float(coords[1])
    scale_x = original_width / resized_width
    scale_y = original_height / resized_height
    return (x * scale_x, y * scale_y)


def rescale_bbox(
    bbox: Union[Tuple[float, float, float, float], List[float]],
    resized_width: int,
    resized_height: int,
    original_width: int,
    original_height: int,
) -> Tuple[float, float, float, float]:
    """Rescale a bounding box ``[x1, y1, x2, y2]`` from resized to original.

    Args:
        bbox: ``[x1, y1, x2, y2]`` in resized-image pixel coordinates.
        resized_width: Width Claude resized the image to.
        resized_height: Height Claude resized the image to.
        original_width: Original image width.
        original_height: Original image height.

    Returns:
        ``(x1, y1, x2, y2)`` in original-image pixel coordinates.
    """
    x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    scale_x = original_width / resized_width
    scale_y = original_height / resized_height
    return (x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y)


def rescale_bboxes(
    bboxes: List[Union[Tuple, List]],
    resized_width: int,
    resized_height: int,
    original_width: int,
    original_height: int,
) -> List[Tuple[float, float, float, float]]:
    """Rescale a list of bounding boxes from the resized to the original frame."""
    return [
        rescale_bbox(bb, resized_width, resized_height, original_width, original_height)
        for bb in bboxes
    ]


# ---------------------------------------------------------------------------
# Bounding box utilities
# ---------------------------------------------------------------------------


@dataclass
class BoundingBox:
    """An axis-aligned bounding box.

    Attributes:
        x1: Left edge (pixels).
        y1: Top edge (pixels).
        x2: Right edge (pixels).
        y2: Bottom edge (pixels).
        label: Optional label for this box.
        confidence: Optional detection confidence (0–1).
    """

    x1: float
    y1: float
    x2: float
    y2: float
    label: str = ""
    confidence: Optional[float] = None

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def as_list(self) -> List[float]:
        """Return ``[x1, y1, x2, y2]``."""
        return [self.x1, self.y1, self.x2, self.y2]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "width": self.width,
            "height": self.height,
            "label": self.label,
            "confidence": self.confidence,
        }

    def iou(self, other: "BoundingBox") -> float:
        """Compute Intersection-over-Union with *other*."""
        inter_x1 = max(self.x1, other.x1)
        inter_y1 = max(self.y1, other.y1)
        inter_x2 = min(self.x2, other.x2)
        inter_y2 = min(self.y2, other.y2)
        inter_area = max(0.0, inter_x2 - inter_x1) * max(0.0, inter_y2 - inter_y1)
        union_area = self.area + other.area - inter_area
        if union_area <= 0:
            return 0.0
        return inter_area / union_area

    def rescale(
        self,
        resized_width: int,
        resized_height: int,
        original_width: int,
        original_height: int,
    ) -> "BoundingBox":
        """Return a new BoundingBox rescaled to the original image frame."""
        x1, y1, x2, y2 = rescale_bbox(
            [self.x1, self.y1, self.x2, self.y2],
            resized_width, resized_height,
            original_width, original_height,
        )
        return BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2,
                           label=self.label, confidence=self.confidence)

    @classmethod
    def from_list(
        cls,
        coords: Union[List[float], Tuple[float, ...]],
        label: str = "",
        confidence: Optional[float] = None,
    ) -> "BoundingBox":
        """Create a BoundingBox from a ``[x1, y1, x2, y2]`` sequence."""
        return cls(x1=coords[0], y1=coords[1], x2=coords[2], y2=coords[3],
                   label=label, confidence=confidence)


# ---------------------------------------------------------------------------
# Image pre-resize helpers
# ---------------------------------------------------------------------------


def resize_image_to_claude_size(
    image_bytes: bytes,
    model_id: str = "",
    tier: Optional[ResolutionTier] = None,
) -> Tuple[bytes, int, int]:
    """Resize *image_bytes* to exactly the size Claude would process it at.

    Requires ``Pillow`` (``pip install Pillow``).

    Args:
        image_bytes: Raw image data.
        model_id: Claude model ID (used to pick the resolution tier).
        tier: Override the resolution tier.

    Returns:
        ``(resized_bytes, new_width, new_height)`` — the resized image and
        its exact dimensions.  The returned image will have its coordinate
        frame match Claude's output coordinates 1:1.
    """
    try:
        from PIL import Image
        import io
    except ImportError:
        raise ImportError(
            "Pillow is required for image resizing. "
            "Install it with: pip install Pillow"
        )

    t = tier or (resolution_tier_for_model(model_id) if model_id else STANDARD_TIER)
    img = Image.open(io.BytesIO(image_bytes))
    orig_w, orig_h = img.size

    new_w, new_h = compute_resized_size(orig_w, orig_h, t.max_edge, t.max_visual_tokens)

    if (new_w, new_h) == (orig_w, orig_h):
        # No resize needed
        return image_bytes, orig_w, orig_h

    resized = img.resize((new_w, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    fmt = img.format or "PNG"
    resized.save(buf, format=fmt)
    return buf.getvalue(), new_w, new_h


# ---------------------------------------------------------------------------
# Structured output schemas
# ---------------------------------------------------------------------------


#: JSON schema for a single bounding box (x1, y1, x2, y2 in pixel coords).
BBOX_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "x1": {"type": "number", "description": "Left edge in pixels"},
        "y1": {"type": "number", "description": "Top edge in pixels"},
        "x2": {"type": "number", "description": "Right edge in pixels"},
        "y2": {"type": "number", "description": "Bottom edge in pixels"},
        "label": {"type": "string", "description": "Label for this region"},
    },
    "required": ["x1", "y1", "x2", "y2"],
}

#: JSON schema for a list of bounding boxes.
BBOX_LIST_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "bounding_boxes": {
            "type": "array",
            "items": BBOX_SCHEMA,
            "description": "Detected regions with pixel coordinates (x1,y1,x2,y2)",
        }
    },
    "required": ["bounding_boxes"],
}

#: JSON schema for a single (x, y) point.
POINT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "x": {"type": "number", "description": "X coordinate in pixels"},
        "y": {"type": "number", "description": "Y coordinate in pixels"},
        "label": {"type": "string"},
    },
    "required": ["x", "y"],
}

#: Prompt fragment to request absolute pixel coordinates from Claude.
COORDINATE_PROMPT = (
    "Return all coordinates as absolute pixel coordinates in the image you see. "
    "Use the format [x1, y1, x2, y2] for bounding boxes (top-left and bottom-right "
    "corners), where (0, 0) is the top-left of the image."
)
