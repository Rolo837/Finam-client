import pytest

from finam_client.venue import (
    Venue,
    finam_board_from_venue,
    from_finam_venue,
    to_finam_venue,
)


def test_forts_translates_both_ways():
    assert to_finam_venue("MISX", "RFUD") == Venue("RTSX", "FUT")
    assert from_finam_venue("RTSX", "FUT") == Venue("MISX", "RFUD")


@pytest.mark.parametrize("board", ["TQBR", "CETS", ""])
def test_other_boards_map_to_themselves(board):
    assert to_finam_venue("MISX", board) == Venue("MISX", board)
    assert from_finam_venue("MISX", board) == Venue("MISX", board)


def test_codes_are_normalized_to_upper_case_but_not_tickers():
    assert to_finam_venue(" misx ", "rfud") == Venue("RTSX", "FUT")


def test_unknown_rtsx_board_folds_into_misx_like_bf_did():
    assert from_finam_venue("RTSX", "OTHER") == Venue("MISX", "OTHER")


def test_finam_board_from_venue_matches_legacy_bf_helper():
    assert finam_board_from_venue("MISX", "RFUD") == "FUT"
    assert finam_board_from_venue("MISX", "tqbr") == "TQBR"
    assert finam_board_from_venue("XNGS", "") == ""
