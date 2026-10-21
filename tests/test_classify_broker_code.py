from finam_client.client import _classify_broker_code


def test_insufficient_funds_real_broker_text():
    detail = "[145]No enough coverage. You need 396831.50 RUR\x0cНедостаток обеспечения в сумме 396831.50 RUR"
    assert _classify_broker_code(detail) == "insufficient_funds"


def test_auction_only_still_classified():
    assert _classify_broker_code("(14302) FOK и IOC заявки запрещены в аукционе открытия") == "auction_only"


def test_unrelated_detail_unclassified():
    assert _classify_broker_code("Invalid price step") is None
