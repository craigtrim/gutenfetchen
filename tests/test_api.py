"""Tests for the Gutendex API client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from gutenfetch.api import _parse_book, _parse_response, search_books


def test_parse_book(sample_api_response: dict) -> None:  # type: ignore[type-arg]
    item = sample_api_response["results"][0]
    book = _parse_book(item)
    assert book.id == 219
    assert book.title == "Heart of Darkness"
    assert len(book.authors) == 1
    assert book.authors[0].name == "Conrad, Joseph"
    assert book.download_count == 50000


def test_parse_response(sample_api_response: dict) -> None:  # type: ignore[type-arg]
    result = _parse_response(sample_api_response)
    assert result.count == 2
    assert len(result.books) == 2
    assert result.next_url is None


def test_parse_response_with_next() -> None:
    data = {
        "count": 100,
        "next": "https://gutendex.com/books/?page=2",
        "results": [],
    }
    result = _parse_response(data)
    assert result.next_url == "https://gutendex.com/books/?page=2"


@patch("gutenfetch.api.requests.get")
def test_search_books(mock_get: MagicMock, sample_api_response: dict) -> None:  # type: ignore[type-arg]
    mock_resp = MagicMock()
    mock_resp.json.return_value = sample_api_response
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = search_books("heart of darkness")

    mock_get.assert_called_once()
    call_kwargs = mock_get.call_args
    assert call_kwargs[1]["params"]["search"] == "heart of darkness"
    assert call_kwargs[1]["params"]["languages"] == "en"
    assert len(result.books) == 2
