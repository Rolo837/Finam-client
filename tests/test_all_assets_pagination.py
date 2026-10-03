from types import SimpleNamespace
from unittest.mock import MagicMock

from finam_client.client import FinamApiClient


def _page(assets, next_cursor: int):
    return SimpleNamespace(assets=assets, next_cursor=next_cursor)


def test_iter_all_assets_follows_next_cursor():
    client = MagicMock(spec=FinamApiClient)
    client.all_assets = MagicMock(
        side_effect=[
            _page([SimpleNamespace(ticker="A")], 100),
            _page([SimpleNamespace(ticker="B")], 200),
            _page([SimpleNamespace(ticker="C")], 0),
        ]
    )
    tickers = [a.ticker for a in FinamApiClient.iter_all_assets(client, only_active=True)]
    assert tickers == ["A", "B", "C"]
    assert client.all_assets.call_args_list[0].kwargs == {"cursor": 0, "only_active": True}
    assert client.all_assets.call_args_list[1].kwargs["cursor"] == 100
    assert client.all_assets.call_args_list[2].kwargs["cursor"] == 200


def test_iter_all_assets_starts_at_cursor_zero():
    client = MagicMock(spec=FinamApiClient)
    client.all_assets = MagicMock(return_value=_page([], 0))
    list(FinamApiClient.iter_all_assets(client))
    client.all_assets.assert_called_once_with(cursor=0, only_active=True)
