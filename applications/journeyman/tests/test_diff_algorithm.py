import io
import unittest

from PIL import Image

from journeyman.diff_algorithm import compute_diff


def _png(color, size=(40, 40)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class ComputeDiffTests(unittest.TestCase):
    def test_identical_images_have_zero_diff(self):
        img = _png((10, 20, 30))
        pct, diff_png = compute_diff(img, img)
        self.assertEqual(pct, 0.0)
        self.assertTrue(diff_png.startswith(b"\x89PNG"))

    def test_fully_different_images_have_full_diff(self):
        pct, _ = compute_diff(_png((0, 0, 0)), _png((255, 255, 255)))
        self.assertEqual(pct, 100.0)

    def test_partial_diff_is_between_bounds(self):
        base = Image.new("RGB", (40, 40), (0, 0, 0))
        current = base.copy()
        for x in range(20):
            for y in range(40):
                current.putpixel((x, y), (255, 255, 255))
        buf_a, buf_b = io.BytesIO(), io.BytesIO()
        base.save(buf_a, format="PNG")
        current.save(buf_b, format="PNG")
        pct, _ = compute_diff(buf_a.getvalue(), buf_b.getvalue())
        self.assertAlmostEqual(pct, 50.0, delta=1.0)

    def test_mismatched_sizes_do_not_crash(self):
        pct, diff_png = compute_diff(_png((1, 2, 3), (30, 30)), _png((1, 2, 3), (50, 50)))
        self.assertIsInstance(pct, float)
        self.assertTrue(diff_png.startswith(b"\x89PNG"))

    def test_small_noise_below_threshold_is_ignored(self):
        base = Image.new("RGB", (10, 10), (100, 100, 100))
        current = Image.new("RGB", (10, 10), (110, 110, 110))  # delta of 10, under the 24 threshold
        buf_a, buf_b = io.BytesIO(), io.BytesIO()
        base.save(buf_a, format="PNG")
        current.save(buf_b, format="PNG")
        pct, _ = compute_diff(buf_a.getvalue(), buf_b.getvalue())
        self.assertEqual(pct, 0.0)


if __name__ == "__main__":
    unittest.main()
