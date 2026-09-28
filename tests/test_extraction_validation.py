import unittest

from TeleOCR.vlm_utils.extraction_validation import (
    RegionExtractionError,
    validate_bbox,
    validate_output_count,
)


class ExtractionValidationTests(unittest.TestCase):
    def test_valid_rectangles_and_polygons(self):
        for box in ([0, 0, 1, 1], [0.1, 0.2, 0.9, 0.8],
                    [0, 0, 1, 0, 1, 1, 0, 1], [0, 0, 0, 1, 1, 0]):
            with self.subTest(box=box):
                validate_bbox(box, 32, 32, 0)

    def test_zero_height_layout_regression(self):
        # A normalized rectangle emitted for a text-free raster image.
        with self.assertRaisesRegex(RegionExtractionError, "Region 2.*zero area"):
            validate_bbox([0.648, 0.0, 0.885, 0.0], 32, 32, 2)

    def test_other_degenerate_regions(self):
        for box in ([0.5, 0, 0.5, 1], [0.8, 0.2, 0.1, 0.9],
                    [0.1, 0.1, 0.101, 0.9], [0, 0, 0.5, 0.5, 1, 1]):
            with self.subTest(box=box):
                with self.assertRaises(RegionExtractionError):
                    validate_bbox(box, 32, 32, 0)

    def test_invalid_coordinate_shapes_and_values(self):
        for box in (None, [], [0, 0, 1], [0, 0, 1, 1, 0],
                    [0, 0, float("nan"), 1], [0, 0, float("inf"), 1],
                    [-0.1, 0, 1, 1], [0, 0, 1.1, 1], [False, 0, 1, 1],
                    ["0", 0, 1, 1]):
            with self.subTest(box=box):
                with self.assertRaises(RegionExtractionError):
                    validate_bbox(box, 32, 32, 0)

    def test_missing_and_extra_results_are_rejected(self):
        for outputs in ([], ["first"], ["first", "second", "extra"]):
            with self.subTest(outputs=outputs):
                with self.assertRaisesRegex(RegionExtractionError, "count mismatch"):
                    validate_output_count([0, 1], outputs)

    def test_empty_recognition_is_not_missing_recognition(self):
        validate_output_count([0], [""])
        validate_output_count([], [])

    def test_matching_batch_indices(self):
        validate_output_count([(0, 1), (1, 2)], ["first", "second"])


if __name__ == "__main__":
    unittest.main()
