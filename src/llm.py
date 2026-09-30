"""The LLM client (OpenRouter through ChatOpenAI), structured output, and cost."""

import json
import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

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

    def summary(self) -> str:
        return (
            f"LLM: {self.llm_calls} calls, {self.input_tokens} in / {self.output_tokens} out "
            f"tokens. This run: ${self.llm_cost:.6f}."
        )


USAGE = Usage()


def record_spend() -> str:
    """Add this run's cost to the running total in SPEND_FILE. Returns a line to print."""
    path = Path(config.SPEND_FILE)
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, ValueError):
        data = {}
    total = float(data.get("total_usd", 0.0)) + USAGE.llm_cost
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


@lru_cache(maxsize=2)
def get_llm(model: str | None = None) -> ChatOpenAI:
    """The chat client for `model` (default: LLM_MODEL). The eval's grader may use another model."""
    if not config.LLM_API_KEY:
        raise RuntimeError("No OpenRouter key. Set LLM_API_OR in .env (see .env.example).")
    provider = {"require_parameters": config.LLM_REQUIRE_PARAMETERS}
    kwargs = {}
    if config.LLM_TEMPERATURE:
        kwargs["temperature"] = float(config.LLM_TEMPERATURE)
    return ChatOpenAI(
        model=model or config.LLM_MODEL,
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


# --- structured output ---------------------------------------------------------------------


class StructuredOutputError(RuntimeError):
    """The LLM did not return a valid object."""


def _is_error_in_reply(err: TypeError) -> bool:
    """OpenRouter sometimes answers HTTP 200 with {"error": ...} and no "choices" (for example
    "temporarily rate-limited upstream"). The OpenAI client then fails with this TypeError."""
    return "NoneType" in str(err) and "not iterable" in str(err)


def _invoke_with_retry(runnable, messages):
    """Call the model; if the reply holds an error instead of an answer, wait and try again."""
    waits = [2 ** (i + 1) for i in range(config.LLM_MAX_RETRIES)]  # 2, 4, 8 seconds
    for wait in waits + [None]:
        try:
            return runnable.invoke(messages)
        except TypeError as err:
            if not _is_error_in_reply(err):
                raise
            if wait is None:
                raise StructuredOutputError(
                    "OpenRouter returned an error instead of a reply (often a short upstream rate "
                    "limit), also after retrying. Try again in a minute.") from err
            log.warning("OpenRouter returned an error instead of a reply; retrying in %ss.", wait)
            time.sleep(wait)


def structured(schema: type[BaseModel], messages: list[BaseMessage], model: str | None = None):
    """Ask the LLM for an object of type `schema` (OpenAI `json_schema`, strict mode).

    `model` defaults to LLM_MODEL. Raises StructuredOutputError if the reply cannot be parsed.
    """
    runnable = get_llm(model).with_structured_output(schema, method="json_schema", strict=True,
                                                     include_raw=True)
    out = _invoke_with_retry(runnable, messages)
    USAGE.add_llm(out.get("raw"))
    if out.get("parsed") is None:
        raise StructuredOutputError(
            f"could not parse {schema.__name__}: {out.get('parsing_error')}")
    return out["parsed"]
