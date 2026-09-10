from pathlib import Path

from loguru import logger
from magika import Magika


DEFAULT_LANG = "txt"
PDF_SIG_BYTES = b'%PDF'
magika = Magika()

def code_content_clean(content):
    if not content:
        return ""
    lines = content.splitlines()
    start_idx = 0
    end_idx = len(lines)
    if lines and lines[0].startswith("```"):
        start_idx = 1
    if lines and end_idx > start_idx and lines[end_idx - 1].strip() == "```":
        end_idx -= 1
    if start_idx < end_idx:
        return "\n".join(lines[start_idx:end_idx]).strip()
    return ""

def guess_language_by_text(code):
    code = code_content_clean(code)
    if code.startswith("<_"):
        end = code.find("_>")
        if end != -1:
            lang = code[2:end].lower()
            code = code[end + 2:]
            return lang, code

    return (lang if lang != "unknown" else DEFAULT_LANG), code


def guess_suffix_by_bytes(file_bytes, file_path=None) -> str:
    suffix = magika.identify_bytes(file_bytes).prediction.output.label
    if file_path and suffix in ["ai", "html"] and Path(file_path).suffix.lower() in [".pdf"] and file_bytes[:4] == PDF_SIG_BYTES:
        suffix = "pdf"
    return suffix


def guess_suffix_by_path(file_path) -> str:
    if not isinstance(file_path, Path):
        file_path = Path(file_path)
    suffix = magika.identify_path(file_path).prediction.output.label
    if suffix in ["ai", "html"] and file_path.suffix.lower() in [".pdf"]:
        try:
            with open(file_path, 'rb') as f:
                if f.read(4) == PDF_SIG_BYTES:
                    suffix = "pdf"
        except Exception as e:
            logger.warning(f"Failed to read file {file_path} for PDF signature check: {e}")
    return suffix
