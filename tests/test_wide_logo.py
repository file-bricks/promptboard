"""Regression tests for U7: the wide store logo is proportional, not stretched."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    module_path = ROOT / "_tools" / "store_release.py"
    spec = importlib.util.spec_from_file_location("store_release", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _content_bbox_wh(path):
    im = Image.open(path).convert("RGBA")
    bbox = im.getbbox()
    return im.size, bbox, (bbox[2] - bbox[0], bbox[3] - bbox[1])


def test_regenerate_wide_logo_is_proportional_and_centered(tmp_path):
    module = load_module()
    source = ROOT / "PromptBoard.png"
    dst = tmp_path / "Wide310x150Logo.png"
    out = module.regenerate_wide_logo(source=source, target=dst)

    im = Image.open(out).convert("RGBA")
    assert im.size == (310, 150)
    # transparent background (not a stretched fill)
    assert im.getpixel((0, 0))[3] == 0
    assert im.getpixel((309, 149))[3] == 0

    bbox = im.getbbox()
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # The motif keeps (roughly) its source aspect ratio instead of being
    # stretched to fill the 310px width.
    src_im = Image.open(source).convert("RGBA")
    sbbox = src_im.getbbox()
    src_aspect = (sbbox[2] - sbbox[0]) / (sbbox[3] - sbbox[1])
    assert abs((w / h) - src_aspect) < 0.15

    # horizontally centered on the 310px canvas
    center_x = (bbox[0] + bbox[2]) / 2
    assert abs(center_x - 155) < 8


def test_committed_wide_logo_is_not_stretched():
    size, _bbox, (w, h) = _content_bbox_wh(ROOT / "store_assets" / "Wide310x150Logo.png")
    assert size == (310, 150)
    # A stretched square motif filled ~284x137 (aspect ~2.1); a proportional
    # fit stays near square.
    assert (w / h) < 1.4
