#!/usr/bin/env python3
"""End-to-end tests for the Nemo Folder Preview thumbnailer.

Run from the repository root with: python3 tests/test_engine.py
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "cover-thumbnailer.py"


class ThumbnailerIntegrationTests(unittest.TestCase):
    """Exercise the public thumbnailer command with temporary user data."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="nfp-test-")
        self.home = Path(self.tmpdir.name) / "home"
        self.pictures = self.home / "Pictures"
        self.pictures.mkdir(parents=True)
        config_dir = self.home / ".config" / "nemo-folder-preview"
        config_dir.mkdir(parents=True)
        (config_dir / "config.conf").write_text(
            "[PICTURES]\n"
            "enabled = Yes\n"
            "keepdefaulticon = No\n"
            "usegnomefolder = No\n"
            "maxthumbs = 4\n"
            "theme = \"Mint-Y-Blue\"\n"
            'path = "{}"\n'.format(self.pictures),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def make_folder(self, name, images):
        folder = self.pictures / name
        folder.mkdir()
        for index, (extension, color) in enumerate(images, start=1):
            Image.new("RGB", (180, 120), color).save(folder / f"photo-{index}.{extension}")
        return folder

    def generate(self, folder, size=128):
        output = folder.parent / f"{folder.name}-{size}.png"
        environment = os.environ.copy()
        environment.update(DEVEL="1", HOME=str(self.home))
        result = subprocess.run(
            [sys.executable, str(ENGINE), str(folder), str(output), str(size)],
            cwd=ROOT, env=environment, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertTrue(output.is_file(), "The thumbnailer did not create an output PNG")
        with Image.open(output) as image:
            image.load()
            self.assertEqual(image.size, (size, size))
            self.assertEqual(image.mode, "RGBA")
            return image.copy()

    def assert_contains_color(self, image, color):
        red, green, blue = color
        found = any(
            alpha > 200 and abs(r - red) < 25 and abs(g - green) < 25 and abs(b - blue) < 25
            for r, g, b, alpha in image.getdata()
        )
        self.assertTrue(found, "Expected photo colour %r was not present" % (color,))

    def test_one_to_four_photos_are_rendered(self):
        colors = [(220, 40, 40), (40, 180, 60), (45, 90, 220), (235, 180, 30)]
        for number in range(1, 5):
            folder = self.make_folder("case-%d" % number, [("png", c) for c in colors[:number]])
            thumbnail = self.generate(folder)
            for color in colors[:number]:
                self.assert_contains_color(thumbnail, color)

    def test_webp_is_used_as_a_photo_preview(self):
        color = (205, 30, 185)
        thumbnail = self.generate(self.make_folder("webp", [("webp", color)]))
        self.assert_contains_color(thumbnail, color)

    def test_requested_nemo_thumbnail_sizes_are_generated(self):
        folder = self.make_folder("sizes", [("jpg", (30, 160, 210))])
        for size in (128, 256, 512):
            self.assertIsNotNone(self.generate(folder, size).getbbox())


if __name__ == "__main__":
    if not ENGINE.is_file():
        raise SystemExit("Run this test file from the Nemo Folder Preview repository.")
    unittest.main(verbosity=2)
