"""Tests for the brand assets of the integration."""

from __future__ import annotations

from pathlib import Path
import struct

import pytest

BRAND_PATH = Path(__file__).parents[2] / "custom_components" / "feedparser" / "brand"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
RGBA_COLOR_TYPE = 6


@pytest.mark.parametrize(("name", "size"), [("icon.png", 256), ("icon@2x.png", 512)])
def test_brand_icon_is_a_square_png_with_transparency(name: str, size: int) -> None:
    """Test that each brand icon is an RGBA PNG of the square size that HACS and Home Assistant expect."""
    data = (BRAND_PATH / name).read_bytes()

    assert data.startswith(PNG_SIGNATURE)
    # The IHDR chunk follows the signature: length and type (8 bytes), then width, height, depth, color type.
    width, height, _depth, color_type = struct.unpack(">IIBB", data[16:26])
    assert (width, height, color_type) == (size, size, RGBA_COLOR_TYPE)
