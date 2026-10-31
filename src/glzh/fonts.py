"""字体：让界面字体能显示中文。

游戏自带思源黑体（NotoSansSC-Black，约 3 万字形）及其动态 TMP 字体 `NotoSansSC-Black SDF`，运行时按需生成字形。
注入只需把它追加到同一文件内其余 TMP 字体的后备链末尾，开启它的多图集，并把它的行度量按 Figtree 的比例对齐，
不分发字体（见 ADR 0003、0006）。除下面的专用字体外不新增对象（见 ADR 0008）。

需要处理两处，各有一套独立的 TMP 字体：
- Addressables 的 `ui_assets_all` 包：自带类型信息；
- Resources 目录的 `resources.assets`：没有内嵌类型信息，需用游戏程序集现场生成 typetree，
  且其 MonoBehaviour 引用 `globalgamemanagers.assets` 中的脚本，读取时要一并加载。

排行榜的状态标签另有专用字体：标签关闭了 maskable 才露在遮罩面板外，而后备字体和多图集第 2 张起
都走 TMP 的子网格，子网格不继承 maskable，中文会被裁掉。所以标签的主字体要自带中文字形，
且只用一张图集（见 ADR 0008）。
"""

import copy
import io
from dataclasses import dataclass
from pathlib import PurePath

import UnityPy
from fontTools.ttLib import TTFont
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

from glzh.bundles import PACKER, mono_behaviours
from glzh.game import GameFiles

CJK_FONT_ASSET = "NotoSansSC-Black SDF"
FIGTREE_BOLD = "Figtree-Bold SDF"  # 状态标签原本的字体，也是挂中文后备的主字体之一；Figtree 各字重行度量相同
LINE_METRICS = ("m_AscentLine", "m_DescentLine", "m_LineHeight")
DYNAMIC = 1  # m_AtlasPopulationMode：运行时按需生成字形
STATUS_LABEL = "StatusLabelText"  # 排行榜状态标签的文本组件所在的 GameObject
STATUS_FONT_ASSET = "GoldenLapZH-StatusLabel SDF"
STYLE_FIELD = "reflectedTextStyleField"  # FunTextTMP 的文本样式绑定，运行时按样式重设字体


@dataclass(frozen=True)
class StatusFont:
    """专用字体及其材质的 path_id。"""

    font: int
    material: int


def required_chars(texts) -> set[str]:
    """译文实际用到的非 ASCII 字符（需要中文字体提供字形的部分）。"""
    return {ch for text in texts for ch in text if ord(ch) > 0x7F and not ch.isspace()}


def font_assets(container) -> list:
    """资源包或序列化文件中的 TMP 字体：[(对象, typetree)]。TMP 的 Sprite Asset 也有 m_FaceInfo，但没有字体后备链，排除。"""
    return [
        (obj, tree)
        for obj, tree in mono_behaviours(container)
        if "m_FaceInfo" in tree and "m_FallbackFontAssetTable" in tree
    ]


def _cjk_font(fonts: list):
    matches = [(obj, tree) for obj, tree in fonts if tree["m_Name"] == CJK_FONT_ASSET]
    if len(matches) != 1:
        raise ValueError(f"应恰好有一个 {CJK_FONT_ASSET}，实际 {len(matches)} 个；游戏可能已不再自带思源黑体")
    obj, tree = matches[0]
    if tree["m_AtlasPopulationMode"] != DYNAMIC:
        # 静态图集只含预烘的字，按源字体检查覆盖就不成立了
        raise ValueError(f"{CJK_FONT_ASSET} 不再是动态字体，无法按需生成中文字形")
    return obj, tree


def _missing(cjk_obj, cjk: dict, chars: set[str]) -> set[str]:
    source_id = cjk["m_SourceFontFile"]["m_PathID"]  # 源字体与 TMP 字体在同一文件内（m_FileID 为 0）
    font = cjk_obj.assets_file.objects[source_id].read_typetree()
    cmap = TTFont(io.BytesIO(bytes(font["m_FontData"]))).getBestCmap()
    return {ch for ch in chars if ord(ch) not in cmap}


def ensure_glyphs(missing: set[str]) -> None:
    if missing:
        raise ValueError(f"中文字体缺少这些字的字形：{''.join(sorted(missing))}")


def _has_fallback(tree: dict, cjk_id: int) -> bool:
    return any(ref["m_FileID"] == 0 and ref["m_PathID"] == cjk_id for ref in tree["m_FallbackFontAssetTable"])


def _append_fallback(fonts: list, cjk_id: int) -> None:
    for obj, tree in fonts:
        if obj.path_id == cjk_id or _has_fallback(tree, cjk_id):
            continue
        chain = tree["m_FallbackFontAssetTable"]
        chain.append({"m_FileID": 0, "m_PathID": cjk_id})
        obj.save_typetree(tree)


def _enable_multi_atlas(cjk_obj, cjk: dict) -> None:
    """单张 1024² 动态图集只装得下约 90 个中文字，写满后新字显示为方框；开启后 TMP 写满即加开新图集（见 ADR 0003）。"""
    if not cjk["m_IsMultiAtlasTexturesEnabled"]:
        cjk["m_IsMultiAtlasTexturesEnabled"] = 1
        cjk_obj.save_typetree(cjk)


def _figtree_bold(fonts: list) -> dict:
    refs = [tree for _, tree in fonts if tree["m_Name"] == FIGTREE_BOLD]
    if len(refs) != 1:
        raise ValueError(f"应恰好有一个 {FIGTREE_BOLD}，实际 {len(refs)} 个；中文字体的行度量要与它对齐")
    return refs[0]


def _align_line_metrics(fonts: list, cjk_obj, cjk: dict) -> None:
    """把中文字体的上沿、下沿、行高改成与 Figtree 相同的比例（见 ADR 0006）。

    TMP 排一行时取各字形所属字体的最大上沿，思源黑体上沿 1.16em、Figtree 0.95em：
    一行里只要有中文，基线就下移，与旁边纯数字的文本框对不齐。按比例重算，重复执行结果不变。
    """
    ref, face = _figtree_bold(fonts)["m_FaceInfo"], cjk["m_FaceInfo"]
    scale = face["m_PointSize"] / ref["m_PointSize"]
    for key in LINE_METRICS:
        face[key] = ref[key] * scale
    cjk_obj.save_typetree(cjk)


def _patch_cjk(fonts: list, cjk_obj, cjk: dict) -> None:
    """两套字体共用的注入步骤：追加后备、开启多图集、对齐行度量。"""
    _append_fallback(fonts, cjk_obj.path_id)
    _enable_multi_atlas(cjk_obj, cjk)
    _align_line_metrics(fonts, cjk_obj, cjk)


def status_labels(container) -> list:
    """资源包或序列化文件中的状态标签文本组件：[(对象, typetree)]。"""
    return [
        (obj, tree)
        for obj, tree in mono_behaviours(container)
        if "m_text" in tree and obj.assets_file.objects[tree["m_GameObject"]["m_PathID"]].read_typetree()["m_Name"] == STATUS_LABEL
    ]


def _retarget_labels(labels: list, status_font: StatusFont, font_file: str | None) -> None:
    """让标签改用专用字体并清除样式绑定，否则运行时字体又被样式改回去。font_file 是字体所在的外部文件，None 表示同一文件。

    组件上的字号、对齐、字形样式与颜色都不动：样式只提供字体和与组件相同的字号。
    """
    for obj, tree in labels:
        if tree["m_Maskable"] != 0:
            raise ValueError(f"状态标签打开了 maskable，与预期不符（对象 {obj.path_id}）；游戏可能改了界面")
        if not tree.get(STYLE_FIELD):
            raise ValueError(f"状态标签没有样式绑定，与预期不符（对象 {obj.path_id}）；游戏可能改了界面")
        file_id = tree["m_fontAsset"]["m_FileID"]
        found = PurePath(obj.assets_file.externals[file_id - 1].path).name if file_id else None
        if found != font_file:
            raise ValueError(f"状态标签的字体不在 {font_file or '所在文件'} 里（对象 {obj.path_id}）；游戏可能改了界面")
        tree[STYLE_FIELD] = ""
        tree["m_fontAsset"] = {"m_FileID": file_id, "m_PathID": status_font.font}
        tree["m_sharedMaterial"] = {"m_FileID": file_id, "m_PathID": status_font.material}
        obj.save_typetree(tree)


def _add_clone(source, path_id: int, tree: dict) -> None:
    """以 source 的类型信息在同一文件内新增对象；path_id 紧接文件现有最大值，保持对象表有序。"""
    obj = copy.copy(source)
    obj.path_id = path_id
    obj.save_typetree(tree)
    source.assets_file.objects[path_id] = obj


def _add_status_font(fonts: list, cjk_obj, cjk: dict) -> StatusFont:
    """从已注入的中文字体克隆出状态标签的专用字体（字体、材质、图集各一个新对象）。

    源字体文件共用，所以字形覆盖与中文字体相同。TMP 按名字计算字体和材质的哈希，新对象都要改名。
    保留 Figtree 的后备链：其他文字系统的标签仍走后备，显示与原版相同。
    """
    objects = cjk_obj.assets_file.objects
    atlas_source, material_source = objects[cjk["m_AtlasTextures"][0]["m_PathID"]], objects[cjk["m_Material"]["m_PathID"]]
    atlas_id, material_id, font_id = (max(objects) + i for i in (1, 2, 3))
    atlas_ref = {"m_FileID": 0, "m_PathID": atlas_id}

    _add_clone(atlas_source, atlas_id, atlas_source.read_typetree() | {"m_Name": f"{STATUS_FONT_ASSET} Atlas"})
    material = material_source.read_typetree() | {"m_Name": f"{STATUS_FONT_ASSET} Material"}
    material["m_SavedProperties"]["m_TexEnvs"] = [
        (name, env | {"m_Texture": atlas_ref}) if name == "_MainTex" else (name, env) for name, env in material["m_SavedProperties"]["m_TexEnvs"]
    ]
    _add_clone(material_source, material_id, material)
    _add_clone(
        cjk_obj,
        font_id,
        copy.deepcopy(cjk)
        | {
            "m_Name": STATUS_FONT_ASSET,
            "m_Material": {"m_FileID": 0, "m_PathID": material_id},
            "m_AtlasTextures": [atlas_ref],
            "m_IsMultiAtlasTexturesEnabled": 0,
            "m_FallbackFontAssetTable": copy.deepcopy(_figtree_bold(fonts)["m_FallbackFontAssetTable"]),
        },
    )
    return StatusFont(font_id, material_id)


def missing_glyphs(bundle: bytes, chars: set[str]) -> set[str]:
    """chars 中 ui 包内中文字体源文件未覆盖的字符。"""
    return _missing(*_cjk_font(font_assets(UnityPy.load(bundle))), chars)


def inject_cjk_fallback(env) -> None:
    """在已加载的 ui 包中，把中文字体追加到其余 TMP 字体的后备链末尾（已含则跳过），开启它的多图集并对齐行度量，
    再让预制体里的状态标签改用包内的专用字体（包不能引用 resources.assets 的对象）。
    """
    fonts = font_assets(env)
    cjk_obj, cjk = _cjk_font(fonts)
    _patch_cjk(fonts, cjk_obj, cjk)
    labels = status_labels(env)
    if not labels:
        raise ValueError("ui 包里找不到状态标签，中文会被排行榜的遮罩裁掉；游戏可能改了界面")
    _retarget_labels(labels, _add_status_font(fonts, cjk_obj, cjk), None)


def add_cjk_fallback(bundle: bytes) -> bytes:
    """inject_cjk_fallback 的字节进出版本。"""
    env = UnityPy.load(bundle)
    inject_cjk_fallback(env)
    return env.file.save(packer=PACKER)


def load_serialized(data: bytes, deps: GameFiles):
    """加载 resources.assets、level2 这类没有内嵌类型信息的序列化文件。

    deps 提供只读依赖：程序集（生成 typetree）与 globalgamemanagers.assets（脚本引用）。
    """
    env = UnityPy.Environment()
    env.load_file(deps.globalgamemanagers.read_bytes(), name=deps.globalgamemanagers.name, is_dependency=True)
    serialized = env.load_file(data, name="serialized")
    generator = TypeTreeGenerator(serialized.unity_version)
    generator.load_local_dll_folder(str(deps.managed))
    env.typetree_generator = generator
    return serialized


def add_cjk_fallback_serialized(data: bytes, deps: GameFiles, chars: set[str]) -> tuple[bytes, StatusFont]:
    """resources.assets：检查中文字体覆盖 chars 后，把它追加到其余 TMP 字体的后备链末尾，开启它的多图集并对齐行度量，
    再克隆出状态标签的专用字体。返回新内容与专用字体的位置。
    """
    serialized = load_serialized(data, deps)
    fonts = font_assets(serialized)
    cjk_obj, cjk = _cjk_font(fonts)
    ensure_glyphs(_missing(cjk_obj, cjk, chars))
    _patch_cjk(fonts, cjk_obj, cjk)
    status_font = _add_status_font(fonts, cjk_obj, cjk)
    return serialized.save(), status_font




def use_status_font(scene: bytes, deps: GameFiles, status_font: StatusFont) -> bytes:
    """把比赛场景里的状态标签改用 resources.assets 里的专用字体。"""
    serialized = load_serialized(scene, deps)
    labels = status_labels(serialized)
    if not labels:
        raise ValueError("比赛场景里找不到状态标签，中文会被排行榜的遮罩裁掉；游戏可能改了界面")
    _retarget_labels(labels, status_font, deps.resources.name)
    return serialized.save()


def is_injected_serialized(data: bytes, deps: GameFiles) -> bool:
    """resources.assets 是否已被注入。

    判据：原版只有 Figtree-Black/Bold 等少数字体挂了中文后备，注入后其余字体全部都有。
    若将来原版本身就让所有字体都挂上中文后备，此判据会误报，需要改用别的标记。
    """
    fonts = font_assets(load_serialized(data, deps))
    cjk_id = _cjk_font(fonts)[0].path_id
    others = [tree for obj, tree in fonts if obj.path_id != cjk_id]
    return bool(others) and all(_has_fallback(tree, cjk_id) for tree in others)


def is_injected_race_scene(scene: bytes, deps: GameFiles) -> bool:
    """比赛场景是否已被注入。判据：原版的状态标签都绑定了样式，注入时清除。"""
    return any(not tree.get(STYLE_FIELD) for _, tree in status_labels(load_serialized(scene, deps)))
