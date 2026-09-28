from unittest.mock import Mock, patch

import pytest

from TeleOCR.src.model_output_to_middle_json import result_to_middle_json


def test_pages_and_document_close_after_success():
    pages = [Mock(), Mock()]
    document = Mock()
    document.__getitem__ = Mock(side_effect=pages)

    with patch(
        "TeleOCR.src.model_output_to_middle_json.blocks_to_page_info",
        side_effect=[{"page": 0}, {"page": 1}],
    ):
        result = result_to_middle_json([[], []], [{}, {}], document, Mock())

    assert result["pdf_info"] == [{"page": 0}, {"page": 1}]
    for page in pages:
        page.close.assert_called_once_with()
    document.close.assert_called_once_with()


def test_current_page_and_document_close_after_projection_failure():
    page = Mock()
    document = Mock()
    document.__getitem__ = Mock(return_value=page)

    with (
        patch(
            "TeleOCR.src.model_output_to_middle_json.blocks_to_page_info",
            side_effect=RuntimeError("projection failed"),
        ),
        pytest.raises(RuntimeError, match="projection failed"),
    ):
        result_to_middle_json([[]], [{}], document, Mock())

    page.close.assert_called_once_with()
    document.close.assert_called_once_with()
