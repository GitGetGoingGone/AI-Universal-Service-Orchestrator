"""Accumulate OpenAI-compatible usage across intent (remote), planner, and engagement for credit_usage / huddle."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set


def _triplet_from_openai_usage(usage: Any) -> Optional[tuple[int, int, int]]:
    if usage is None:
        return None
    pt = getattr(usage, "prompt_tokens", None)
    ct = getattr(usage, "completion_tokens", None)
    tt = getattr(usage, "total_tokens", None)
    if pt is None and ct is None and tt is None:
        if isinstance(usage, dict):
            pt = usage.get("prompt_tokens")
            ct = usage.get("completion_tokens")
            tt = usage.get("total_tokens")
        else:
            return None
    p = int(pt or 0)
    c = int(ct or 0)
    tot = int(tt) if tt is not None else p + c
    if p == 0 and c == 0 and tot == 0:
        return None
    return (p, c, tot)


def heuristic_credit_usage(message_count: int) -> Dict[str, Any]:
    approx_tokens_in = message_count * 180 + 400
    approx_tokens_out = 650
    return {
        "estimated_input_tokens": approx_tokens_in,
        "estimated_output_tokens": approx_tokens_out,
        "estimated_total_tokens": approx_tokens_in + approx_tokens_out,
        "note": "Heuristic estimate (no LLM usage captured for this turn).",
        "usage_source": "heuristic",
    }


class TurnUsageAccumulator:
    """Thread-safe enough for single-threaded asyncio turn (one request mutates)."""

    def __init__(self) -> None:
        self._prompt = 0
        self._completion = 0
        self._sources: List[str] = []
        self._engagement_chars_est = 0

    def add_openai_usage(self, source: str, usage: Any) -> None:
        t = _triplet_from_openai_usage(usage)
        if not t:
            return
        p, c, _ = t
        self._prompt += p
        self._completion += c
        self._sources.append(source)

    def add_usage_dict(self, source: str, d: Dict[str, Any]) -> None:
        if not isinstance(d, dict):
            return
        p = int(d.get("prompt_tokens") or 0)
        c = int(d.get("completion_tokens") or 0)
        if p == 0 and c == 0:
            return
        self._prompt += p
        self._completion += c
        self._sources.append(source)

    def add_engagement_text_fallback(self, text: str) -> None:
        """When streaming API omits usage, approximate completion tokens from output length."""
        if not text:
            return
        est = max(1, len(text) // 4)
        self._engagement_chars_est = max(self._engagement_chars_est, est)

    def has_measured_usage(self) -> bool:
        return bool(self._sources)

    def to_credit_usage_dict(
        self,
        *,
        message_count: int,
        partial_note_suffix: str = "",
    ) -> Dict[str, Any]:
        if not self.has_measured_usage() and self._engagement_chars_est == 0:
            return heuristic_credit_usage(message_count)

        p = self._prompt
        c = self._completion + self._engagement_chars_est
        srcs: Set[str] = set(self._sources)
        src_label = ", ".join(sorted(srcs)) if srcs else "unknown"
        note = f"Summed provider-reported usage where available: {src_label}."
        if self._engagement_chars_est and "engagement" not in srcs:
            note += " Engagement output estimated from streamed text length (÷4) when the API omitted usage."
        if partial_note_suffix:
            note += f" {partial_note_suffix}"
        return {
            "estimated_input_tokens": p,
            "estimated_output_tokens": c,
            "estimated_total_tokens": p + c,
            "note": note,
            "usage_source": "api_partial" if self._engagement_chars_est and "engagement" not in srcs else "api",
        }


def ingest_intent_api_usage(acc: Optional[TurnUsageAccumulator], api_json: Dict[str, Any]) -> None:
    """Read llm_usage from Intent service chat_first_response envelope."""
    if acc is None or not isinstance(api_json, dict):
        return
    u = api_json.get("llm_usage")
    if isinstance(u, dict):
        acc.add_usage_dict("intent", u)


def apply_final_credit_usage_to_result(
    result: Dict[str, Any],
    acc: Optional[TurnUsageAccumulator],
    message_count: int,
) -> None:
    """Mutate orchestrator result + nested data with final credit_usage for clients / huddle."""
    if acc is None or not isinstance(result, dict):
        return
    cu = acc.to_credit_usage_dict(message_count=message_count)
    result["credit_usage"] = cu
    d = dict(result.get("data") or {})
    d["credit_usage"] = cu
    result["data"] = d
