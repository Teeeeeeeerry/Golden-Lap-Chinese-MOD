"""用 UnityPy 读写资源包的公共部分。"""

# 写回时必须压缩，否则 UnityPy 默认输出未压缩的包，体积膨胀数十倍
PACKER = "lz4"


def mono_behaviours(container):
    """遍历资源包或序列化文件中可读出类型信息的 MonoBehaviour：(对象, typetree)。"""
    objects = container.objects.values() if isinstance(container.objects, dict) else container.objects
    for obj in objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:  # 部分 MonoBehaviour 缺类型信息，读不出来，跳过
            continue
        yield obj, tree
