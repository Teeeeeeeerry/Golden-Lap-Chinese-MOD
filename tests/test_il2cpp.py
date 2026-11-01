import pytest

from glzh.fonts import BORROWED_CLASSES, BorrowedTypeTrees, class_nodes


class FakeNode:
    pass


def test_generator_serves_only_the_borrowed_classes():
    font, label = FakeNode(), FakeNode()
    trees = BorrowedTypeTrees({"TMP_FontAsset": font, "FunTextTMP": label})
    assert trees.get_nodes_up("Unity.TextMeshPro", "TMPro.TMP_FontAsset") is font
    assert trees.get_nodes_up("Funselektor.FunCore.Runtime", "FunTextTMP") is label
    assert trees.get_nodes_up("UnityEngine.UI", "UnityEngine.UI.Image") is None


def test_missing_class_stops_before_anything_is_written():
    with pytest.raises(ValueError, match="FunTextTMP"):
        BorrowedTypeTrees({"TMP_FontAsset": FakeNode()})


def test_real_ui_bundle_embeds_every_borrowed_class(game):
    if not game.il2cpp:
        pytest.skip("只有 IL2CPP 版需要借用 typetree")
    assert set(class_nodes(game.ui.read_bytes())) >= set(BORROWED_CLASSES)
