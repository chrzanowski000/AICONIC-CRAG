"""The LLM client (OpenRouter through ChatOpenAI), structured output with fallbacks, and cost."""

import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError

import config

log = logging.getLogger(__name__)


# --- tokens and cost -------------------------------------------------------------------------


@dataclass
class Usage:
    """Running totals for this process. Printed at the end of every CLI run."""

    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    llm_cost: float = 0.0
    jev_calls: int = 0
    jev_cost: float = 0.0
    methods: dict[str, int] = field(default_factory=dict)

    @property
    def total_cost(self) -> float:
        return self.llm_cost + self.jev_cost

    def add_llm(self, message: AIMessage | None) -> None:
        if message is None:
            return
        self.llm_calls += 1
        meta = message.usage_metadata or {}
        tokens_in = meta.get("input_tokens", 0)
        tokens_out = meta.get("output_tokens", 0)
        self.input_tokens += tokens_in
        self.output_tokens += tokens_out
        cost = (message.response_metadata.get("token_usage") or {}).get("cost")
        if cost is None:  # not reported: work it out from the list price
            cost = (tokens_in * config.LLM_PRICE_IN_PER_M
                    + tokens_out * config.LLM_PRICE_OUT_PER_M) / 1e6
        self.llm_cost += float(cost)

    def add_jev(self, cost: float) -> None:
        self.jev_calls += 1
        self.jev_cost += float(cost or 0.0)

    def summary(self) -> str:
        return (
            f"LLM: {self.llm_calls} calls, {self.input_tokens} in / {self.output_tokens} out "
            f"tokens, ${self.llm_cost:.6f}. Jev: {self.jev_calls} calls, ${self.jev_cost:.6f}. "
            f"This run: ${self.total_cost:.6f}."
        )


USAGE = Usage()


def record_spend() -> str:
    """Add this run's cost to the running total in SPEND_FILE. Returns a line to print."""
    path = Path(config.SPEND_FILE)
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, ValueError):
        data = {}
    total = float(data.get("total_usd", 0.0)) + USAGE.total_cost
    data = {"total_usd": round(total, 8), "runs": int(data.get("runs", 0)) + 1}
    try:
        path.write_text(json.dumps(data, indent=2) + "\n")
    except OSError as err:
        log.warning("Could not write %s: %s", path, err)
    line = f"Total spent by this app so far: ${total:.6f} of ${config.BUDGET_USD:.2f} budget."
    if total > config.BUDGET_USD:
        line += " WARNING: over budget!"
    return line


# --- the client ------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    if not config.LLM_API_KEY:
        raise RuntimeError("No OpenRouter key. Set LLM_API_OR in .env (see .env.example).")
    provider: dict = {"require_parameters": config.LLM_REQUIRE_PARAMETERS}
    if config.LLM_PROVIDER_ORDER:
        provider["order"] = config.LLM_PROVIDER_ORDER
    kwargs = {}
    if config.LLM_TEMPERATURE:
        kwargs["temperature"] = float(config.LLM_TEMPERATURE)
    return ChatOpenAI(
        model=config.LLM_MODEL,
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        use_responses_api=False,
        reasoning_effort=config.LLM_REASONING_EFFORT or None,
        max_tokens=config.LLM_MAX_TOKENS,
        timeout=config.LLM_TIMEOUT_S,
        max_retries=config.LLM_MAX_RETRIES,
        extra_body={"provider": provider},
        default_headers={"HTTP-Referer": config.LLM_HTTP_REFERER, "X-Title": config.LLM_APP_TITLE},
        **kwargs,
    )


# --- structured output with fallbacks --------------------------------------------------------


class StructuredOutputError(RuntimeError):
    """No structured-output method gave a valid object."""


# The first method that worked is tried first next time, so failed methods are not retried
# on every call.
_preferred_method: str | None = None


def _json_mode_instructions(schema: type[BaseModel]) -> str:
    return (
        "Reply with one JSON object only, no other text. It must match this JSON schema:\n"
        + json.dumps(schema.model_json_schema())
    )


def _try_native(llm, schema, messages, method: str):
    runnable = llm.with_structured_output(
        schema, method=method, include_raw=True, strict=True if method == "json_schema" else None
    )
    out = runnable.invoke(messages)
    USAGE.add_llm(out.get("raw"))
    if out.get("parsed") is None:
        raise StructuredOutputError(f"{method}: could not parse: {out.get('parsing_error')}")
    return out["parsed"]


def _try_json_mode(llm, schema, messages):
    bound = llm.bind(response_format={"type": "json_object"})
    msgs = list(messages) + [HumanMessage(_json_mode_instructions(schema))]
    last_error = None
    for _ in range(2):  # one retry, with the error fed back
        raw = bound.invoke(msgs)
        USAGE.add_llm(raw)
        try:
            return schema.model_validate_json(raw.content)
        except ValidationError as err:
            last_error = err
            msgs += [raw, HumanMessage(f"That JSON was not valid: {err}. Try again.")]
    raise StructuredOutputError(f"json_mode: {last_error}")


def structured(schema: type[BaseModel], messages: list[BaseMessage], llm=None):
    """Ask the LLM for an object of type `schema`. Tries the methods in LLM_STRUCTURED_METHODS.

    Returns (object, method used). Raises StructuredOutputError if every method fails.
    """
    global _preferred_method
    llm = llm or get_llm()
    methods = list(config.LLM_STRUCTURED_METHODS)
    if _preferred_method in methods:
        methods.remove(_preferred_method)
        methods.insert(0, _preferred_method)
    errors = []
    for method in methods:
        try:
            if method == "json_mode":
                result = _try_json_mode(llm, schema, messages)
            elif method in ("json_schema", "function_calling"):
                result = _try_native(llm, schema, messages, method)
            else:
                raise ValueError(f"Unknown structured output method '{method}'")
        except Exception as err:  # any failure: log it and try the next method
            log.warning("Structured output with %s failed for %s: %s",
                        method, schema.__name__, str(err)[:300])
            errors.append(f"{method}: {str(err)[:200]}")
            continue
        if method != _preferred_method:
            log.info("Structured output method used: %s", method)
        _preferred_method = method
        USAGE.methods[method] = USAGE.methods.get(method, 0) + 1
        return result, method
    raise StructuredOutputError("; ".join(errors) or "no methods configured")


def plain(messages: list[BaseMessage], llm=None) -> str:
    """Plain text reply. Used only when an Answer object cannot be parsed."""
    raw = (llm or get_llm()).invoke(messages)
    USAGE.add_llm(raw)
    return raw.content if isinstance(raw.content, str) else str(raw.content)
