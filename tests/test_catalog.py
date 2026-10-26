from glzh.catalog import bundle_crcs, disable_crc
from glzh.game import LOCALES_BUNDLE, TURKISH_BUNDLE


def test_disable_crc_zeroes_only_named_bundles(game):
    text = game.catalog.read_text(encoding="utf-8")
    before = bundle_crcs(text)
    after = bundle_crcs(disable_crc(text, {TURKISH_BUNDLE, LOCALES_BUNDLE}))
    assert after[TURKISH_BUNDLE] == 0 and after[LOCALES_BUNDLE] == 0
    others = before.keys() - {TURKISH_BUNDLE, LOCALES_BUNDLE}
    assert len(others) > 10 and all(after[name] == before[name] != 0 for name in others)


def test_disable_crc_keeps_catalog_length(game):
    text = game.catalog.read_text(encoding="utf-8")
    assert len(disable_crc(text, {TURKISH_BUNDLE})) == len(text)


def test_disable_crc_rejects_unknown_bundle(game):
    import pytest

    with pytest.raises(ValueError, match="nope.bundle"):
        disable_crc(game.catalog.read_text(encoding="utf-8"), {"nope.bundle"})
