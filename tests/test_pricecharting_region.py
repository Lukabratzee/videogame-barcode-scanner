import types
import pytest

# Import function under test
from modules.scrapers import _apply_region_to_game_url, _pricecharting_region_segment


def test_region_segment_mapping():
    assert _pricecharting_region_segment(None) is None
    assert _pricecharting_region_segment("US") is None
    assert _pricecharting_region_segment("usa") is None
    assert _pricecharting_region_segment("PAL") == "pal"
    assert _pricecharting_region_segment("EU") == "pal"
    assert _pricecharting_region_segment("JP") == "japan"
    assert _pricecharting_region_segment("Japan") == "japan"


def test_apply_region_to_game_url_basic():
    base = "https://www.pricecharting.com/game/playstation-2/ace-combat-04"
    assert _apply_region_to_game_url(base, None) == base
    assert _apply_region_to_game_url(base, "US") == base
    assert _apply_region_to_game_url(base, "PAL") == "https://www.pricecharting.com/pal/game/playstation-2/ace-combat-04"
    assert _apply_region_to_game_url(base, "JP") == "https://www.pricecharting.com/japan/game/playstation-2/ace-combat-04"


def test_apply_region_idempotent_when_already_prefixed():
    pal_url = "https://www.pricecharting.com/pal/game/playstation-2/ace-combat-04"
    assert _apply_region_to_game_url(pal_url, "PAL") == pal_url
    jp_url = "https://www.pricecharting.com/japan/game/playstation-2/ace-combat-04"
    assert _apply_region_to_game_url(jp_url, "JP") == jp_url
