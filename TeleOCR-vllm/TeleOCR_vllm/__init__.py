"""vLLM plugin registration for TeleOCR."""

from __future__ import annotations


def register() -> None:
    from vllm import ModelRegistry

    model_ref = "TeleOCR_vllm.qwen2_5_vl:Qwen2_5_VLForConditionalGeneration"

    # Keep the original architecture name so existing TeleOCR config.json files
    # can run without changing their architectures field.
    ModelRegistry.register_model("Qwen2_5_VLForConditionalGeneration", model_ref)

    # Also expose an explicit TeleOCR name for future model configs.
    ModelRegistry.register_model("TeleOCRForConditionalGeneration", model_ref)
