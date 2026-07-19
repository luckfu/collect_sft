"""Validated dataset export operations shared by the Web UI and tests."""

import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from export_harness_dataset import (
    export_constrained_dataset,
    export_dataset,
    export_openai_dataset,
    export_openai_windowed_dataset,
    export_sharegpt_dataset,
    export_tool_sft_dataset,
    inspect_dataset,
    load_call_rows,
)


EXPORT_FORMATS = {"canonical", "sharegpt", "tool_sft", "openai", "openai_windowed"}
EXPORT_FILENAME_RE = re.compile(
    r"^dataset-\d{8}-\d{6}-(?:canonical|sharegpt|tool_sft|openai|openai_windowed)(?:-selected\d+)?(?:-limited)?-[a-f0-9]{8}\.(?:json|jsonl)$"
)
MAX_SELECTED_CALLS = 100_000


class ExportValidationError(ValueError):
    pass


def _optional_limit(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        limit = int(value)
    except (TypeError, ValueError) as exc:
        raise ExportValidationError("limit must be an integer") from exc
    if not 1 <= limit <= 1_000_000:
        raise ExportValidationError("limit must be between 1 and 1000000")
    return limit


def _number(value: Any, name: str, minimum: float, maximum: float, *, integer: bool = False):
    try:
        result = int(value) if integer else float(value)
    except (TypeError, ValueError) as exc:
        raise ExportValidationError(f"{name} must be a number") from exc
    if not minimum <= result <= maximum:
        raise ExportValidationError(f"{name} must be between {minimum:g} and {maximum:g}")
    return result


def _optional_call_ids(value: Any) -> Optional[list[str]]:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ExportValidationError("call_ids must be an array")
    if not value:
        raise ExportValidationError("select at least one call")
    if len(value) > MAX_SELECTED_CALLS:
        raise ExportValidationError(f"cannot select more than {MAX_SELECTED_CALLS} calls")

    call_ids = []
    seen = set()
    for value_item in value:
        if not isinstance(value_item, str):
            raise ExportValidationError("every call_id must be a string")
        call_id = value_item.strip()
        if not call_id or len(call_id) > 255:
            raise ExportValidationError("call_id must contain 1 to 255 characters")
        if call_id not in seen:
            seen.add(call_id)
            call_ids.append(call_id)
    return call_ids


def _ensure_calls_exist(db_path: str, call_ids: Optional[list[str]]) -> None:
    if call_ids is None:
        return
    existing = {row["call_id"] for row in load_call_rows(db_path, call_ids=call_ids)}
    missing = [call_id for call_id in call_ids if call_id not in existing]
    if missing:
        sample = ", ".join(missing[:3])
        suffix = "..." if len(missing) > 3 else ""
        raise ExportValidationError(
            f"{len(missing)} selected call(s) no longer exist: {sample}{suffix}"
        )


def normalize_export_options(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ExportValidationError("request body must be a JSON object")
    export_format = str(payload.get("format") or "canonical")
    if export_format not in EXPORT_FORMATS:
        raise ExportValidationError("unsupported export format")
    return {
        "format": export_format,
        "limit": _optional_limit(payload.get("limit")),
        "call_ids": _optional_call_ids(payload.get("call_ids")),
        "include_skipped": bool(payload.get("include_skipped", False)),
        "include_metadata": bool(payload.get("include_metadata", False)),
        "include_tools": bool(payload.get("include_tools", True)),
        "context_limit": bool(payload.get("context_limit", False)),
        "max_seq_len": _number(payload.get("max_seq_len", 4096), "max_seq_len", 128, 1_000_000, integer=True),
        "chars_per_token": _number(payload.get("chars_per_token", 4.0), "chars_per_token", 0.1, 100.0),
        "prefix_budget_ratio": _number(payload.get("prefix_budget_ratio", 0.45), "prefix_budget_ratio", 0.0, 1.0),
    }


def inspect_for_web(db_path: str, *, limit: Any = None, call_ids: Any = None,
                    include_window_budget: bool = False, chars_per_token: Any = 4.0) -> Dict[str, Any]:
    normalized_call_ids = _optional_call_ids(call_ids)
    _ensure_calls_exist(db_path, normalized_call_ids)
    return inspect_dataset(
        db_path,
        limit=_optional_limit(limit),
        call_ids=normalized_call_ids,
        preview=0,
        include_window_budget=bool(include_window_budget),
        chars_per_token=_number(chars_per_token, "chars_per_token", 0.1, 100.0),
    )


def export_directory(db_path: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(db_path)), "data", "exports")


def export_file_path(db_path: str, filename: str) -> Optional[str]:
    if not EXPORT_FILENAME_RE.fullmatch(filename or ""):
        return None
    root = os.path.abspath(export_directory(db_path))
    path = os.path.abspath(os.path.join(root, filename))
    if os.path.dirname(path) != root:
        return None
    return path


def run_export(db_path: str, payload: Any) -> Dict[str, Any]:
    options = normalize_export_options(payload)
    _ensure_calls_exist(db_path, options["call_ids"])
    export_format = options["format"]
    extension = "json" if export_format == "sharegpt" else "jsonl"
    limited_suffix = "-limited" if options["context_limit"] and export_format != "openai_windowed" else ""
    selection_suffix = f"-selected{len(options['call_ids'])}" if options["call_ids"] is not None else ""
    filename = (
        f"dataset-{datetime.now().strftime('%Y%m%d-%H%M%S')}-"
        f"{export_format}{selection_suffix}{limited_suffix}-{uuid.uuid4().hex[:8]}.{extension}"
    )
    out_path = export_file_path(db_path, filename)
    assert out_path is not None
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    common = {
        "limit": options["limit"],
        "include_skipped": options["include_skipped"],
        "call_ids": options["call_ids"],
    }
    try:
        if options["context_limit"] and export_format != "openai_windowed":
            result = export_constrained_dataset(
                db_path,
                out_path,
                export_format,
                **common,
                include_metadata=options["include_metadata"],
                include_tools=options["include_tools"],
                max_seq_len=options["max_seq_len"],
                chars_per_token=options["chars_per_token"],
                prefix_budget_ratio=options["prefix_budget_ratio"],
            )
        elif export_format == "sharegpt":
            result = export_sharegpt_dataset(
                db_path, out_path, **common,
                include_metadata=options["include_metadata"],
                include_tools=options["include_tools"],
            )
        elif export_format == "tool_sft":
            result = export_tool_sft_dataset(
                db_path, out_path, **common,
                include_metadata=options["include_metadata"],
            )
        elif export_format == "openai":
            result = export_openai_dataset(
                db_path, out_path, **common,
                include_metadata=options["include_metadata"],
            )
        elif export_format == "openai_windowed":
            result = export_openai_windowed_dataset(
                db_path, out_path, **common,
                include_metadata=options["include_metadata"],
                max_seq_len=options["max_seq_len"],
                chars_per_token=options["chars_per_token"],
                prefix_budget_ratio=options["prefix_budget_ratio"],
            )
        else:
            result = export_dataset(db_path, out_path, **common)
    except Exception:
        try:
            os.remove(out_path)
        except FileNotFoundError:
            pass
        raise

    stat = os.stat(out_path)
    return {
        **result,
        "filename": filename,
        "selected_count": len(options["call_ids"]) if options["call_ids"] is not None else None,
        "size_bytes": stat.st_size,
        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def list_exports(db_path: str) -> list[Dict[str, Any]]:
    root = export_directory(db_path)
    if not os.path.isdir(root):
        return []
    rows = []
    for filename in os.listdir(root):
        path = export_file_path(db_path, filename)
        if path is None or not os.path.isfile(path):
            continue
        stat = os.stat(path)
        rows.append({
            "filename": filename,
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    rows.sort(key=lambda row: row["created_at"], reverse=True)
    return rows
