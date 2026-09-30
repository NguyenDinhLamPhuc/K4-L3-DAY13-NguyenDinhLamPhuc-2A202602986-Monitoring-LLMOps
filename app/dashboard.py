"""Dashboard aggregates from structured logs; never return raw request payloads."""
from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from fastapi import APIRouter
from fastapi.responses import FileResponse

from . import logging_config
from .pii import scrub_text

ROOT = Path(__file__).resolve().parents[1]
router = APIRouter()


def percentile(values: list[float], percent: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    lo, hi = math.floor(position), math.ceil(position)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo), 4)


def numbers(rows: list[dict], key: str) -> list[float]:
    return [float(row[key]) for row in rows
            if isinstance(row.get(key), (int, float))
            and not isinstance(row[key], bool) and math.isfinite(row[key])]


def summarize(rows: list[dict]) -> dict:
    received = [r for r in rows if r.get("event") == "request_received"]
    sent = [r for r in rows if r.get("event") == "response_sent"]
    failed = [r for r in rows if r.get("event") == "request_failed"]
    retrieval = [r for r in sent + failed
                 if r.get("tool_name") == "retrieval" and isinstance(r.get("tool_success"), bool)]
    latency = numbers(sent, "latency_ms")
    quality = numbers(sent, "quality_score")
    return {
        "latency": {**{f"p{p}": percentile(latency, p) for p in (50, 95, 99)},
                    "ttft_p95": percentile(numbers(sent, "ttft_ms"), 95)},
        "traffic": {"count": len(received)},
        "errors": {
            "error_rate_pct": len(failed) / len(received) * 100 if received else None,
            "tool_success_rate_pct": sum(r["tool_success"] for r in retrieval) / len(retrieval) * 100 if retrieval else None,
            "breakdown": dict(Counter(scrub_text(str(r.get("error_type", "Unknown"))) for r in failed)),
        },
        "cost": {"total": round(sum(numbers(sent, "cost_usd")), 6)},
        "tokens": {"tokens_in": sum(numbers(sent, "tokens_in")), "tokens_out": sum(numbers(sent, "tokens_out"))},
        "quality": {"mean": sum(quality) / len(quality) if quality else None},
    }


def build_snapshot(path: Path, *, now: datetime | None = None) -> dict:
    config = yaml.safe_load((ROOT / "config/dashboard.yaml").read_text(encoding="utf-8"))["dashboard"]
    end = now or datetime.now(timezone.utc)
    start = end - timedelta(minutes=config["time_range_minutes"])
    buckets: dict[str, list[dict]] = {}
    cursor = start.replace(second=0, microsecond=0)
    while cursor <= end:
        buckets[cursor.isoformat()] = []
        cursor += timedelta(minutes=1)
    rows = []
    invalid_lines = 0
    if path.exists():
        with path.open(encoding="utf-8") as source:
            for line in source:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    timestamp = datetime.fromisoformat(row["ts"].replace("Z", "+00:00"))
                    if timestamp.tzinfo is None:
                        raise ValueError("Timestamp must include timezone")
                except (ValueError, TypeError, KeyError, AttributeError):
                    invalid_lines += 1
                    continue
                if start <= timestamp <= end:
                    rows.append(row)
                    key = timestamp.astimezone(timezone.utc).replace(second=0, microsecond=0).isoformat()
                    buckets[key].append(row)
    summary = summarize(rows)
    summary["traffic"]["rate_per_minute"] = summary["traffic"]["count"] / config["time_range_minutes"]
    return {
        "config": config, "start": start.isoformat(), "end": end.isoformat(),
        "invalid_lines": invalid_lines, "event_count": len(rows), "summary": summary,
        "series": [{"time": timestamp, **summarize(events)} for timestamp, events in buckets.items()],
    }


@router.get("/dashboard", include_in_schema=False)
def dashboard_page():
    return FileResponse(ROOT / "app/dashboard.html", headers={"Cache-Control": "no-store"})


@router.get("/dashboard/data")
def dashboard_data() -> dict:
    return build_snapshot(logging_config.LOG_PATH)
