# =========================
# Model
# =========================

model_path = "StarDoc-AI/TeleOCR"

BACKEND = "vllm-async-engine"
# [vllm-engine, vllm-async-engine]


# =========================
# Layout
# =========================

LAYOUT_MODE = "Detection"
# [Detection / Segmentation]


# =========================
# VLLM
# =========================

MAX_MODEL_LEN = 16384
GPU_MEMORY_UTILIZATION = 0.95


# =========================
# PDF
# =========================

PDF_TOOLS = "pypdfium2"
# [PyMuPDF / pypdfium2]

PDF_TOOLS_WORKER_MAX_NUM = 4
PDF_TOOLS_WORKER_RATIO = 0.7

MAX_PIXELS = 8000 * 8000


# =========================
# Runtime Override
# =========================

def _convert(value, reference):
    """根据默认值自动转换命令行参数类型。"""

    if isinstance(reference, bool):
        return value.lower() in {"true", "1", "yes"}

    if isinstance(reference, int):
        return int(value)

    if isinstance(reference, float):
        return float(value)

    if value.lower() == "none":
        return None

    return value


def update(overrides):
    """运行时覆盖配置。"""

    for item in overrides:

        key, sep, value = item.partition("=")

        if not sep:
            raise ValueError(
                f"Invalid config override: {item}. "
                f"Expected KEY=VALUE."
            )

        if key not in globals():
            raise KeyError(
                f"Unknown config option: {key}"
            )

        old_value = globals()[key]
        new_value = _convert(value, old_value)

        globals()[key] = new_value

        print(
            f"[Config] {key}: "
            f"{old_value!r} -> {new_value!r}"
        )


def show():
    """打印最终配置。"""

    print("\n========== TeleOCR Config ==========")

    for key, value in globals().items():

        if key.startswith("_"):
            continue

        if key.isupper() or key == "model_path":
            print(f"{key} = {value}")

    print("====================================\n")