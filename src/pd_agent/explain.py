"""Plain-English explanations of OpenLane flow metrics via LLM.

Wraps the vendor-agnostic :class:`pd_agent.llm.LLMProvider` with a
domain-specific system prompt and a structured serialization of
:class:`pd_agent.flow.models.FlowMetrics` so the LLM receives only the
information that matters for physical-design signoff.
"""

from __future__ import annotations

from pd_agent.flow.models import FlowMetrics
from pd_agent.llm import LLMProvider, LLMResponse, make_default_provider

__all__ = ["SYSTEM_PROMPT", "build_user_prompt", "explain_metrics"]


SYSTEM_PROMPT = """\
You are an expert physical design engineer helping someone understand the
results of an OpenLane 2 flow run. You receive a structured summary of
signoff metrics.

Your job is to explain, in plain English:

1. Whether the design passed signoff (clean) or has issues.
2. The key numbers: timing slacks (setup/hold), DRC/LVS/antenna violation
   counts, power, and area.
3. If there are failures, which specific checks failed and by how much.

Guidelines:
- Be concise (4-8 sentences).
- Use engineering units (ns, mW, um^2).
- Do NOT invent values that are not in the input. If a field is marked
  "not measured", do not claim it passed or failed.
- Prefer insight over restating every number verbatim.
"""


def _fmt_float(value: float | None, unit: str) -> str:
    if value is None:
        return "not measured"
    return f"{value:g} {unit}"


def _fmt_int(value: int | None) -> str:
    if value is None:
        return "not measured"
    return str(value)


def build_user_prompt(metrics: FlowMetrics) -> str:
    """Serialize :class:`FlowMetrics` into a compact, human-readable prompt."""
    lines = [
        "Here are the signoff metrics from an OpenLane 2 run:",
        "",
        f"Overall clean: {str(metrics.is_clean).lower()}",
        "",
        "Design:",
        f"  instance_count: {_fmt_int(metrics.instance_count)}",
        f"  die_area:       {_fmt_float(metrics.die_area, 'um^2')}",
        f"  core_area:      {_fmt_float(metrics.core_area, 'um^2')}",
        "",
        "Timing (positive = passing, negative = failing):",
        f"  setup WS:  {_fmt_float(metrics.timing_setup_ws, 'ns')}",
        f"  setup WNS: {_fmt_float(metrics.timing_setup_wns, 'ns')}",
        f"  setup TNS: {_fmt_float(metrics.timing_setup_tns, 'ns')}",
        f"  hold  WS:  {_fmt_float(metrics.timing_hold_ws, 'ns')}",
        f"  hold  WNS: {_fmt_float(metrics.timing_hold_wns, 'ns')}",
        f"  hold  TNS: {_fmt_float(metrics.timing_hold_tns, 'ns')}",
        "",
        "Violations:",
        f"  DRC (Magic):    {_fmt_int(metrics.drc_errors_magic)}",
        f"  DRC (KLayout):  {_fmt_int(metrics.drc_errors_klayout)}",
        f"  LVS:            {_fmt_int(metrics.lvs_errors)}",
        f"  Antenna nets:   {_fmt_int(metrics.antenna_violating_nets)}",
        f"  Max slew:       {_fmt_int(metrics.max_slew_violations)}",
        f"  Max cap:        {_fmt_int(metrics.max_cap_violations)}",
        "",
        "Power:",
        f"  total: {_fmt_float(metrics.power_total, 'W')}",
        "",
        "Explain these results in plain English.",
    ]
    return "\n".join(lines)


def explain_metrics(
    metrics: FlowMetrics,
    *,
    provider: LLMProvider | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> LLMResponse:
    """Generate a plain-English explanation of the flow metrics.

    Parameters
    ----------
    metrics
        Parsed flow metrics from an OpenLane 2 run.
    provider
        LLM provider to use. If ``None``, a default provider is built from
        :class:`~pd_agent.config.PDAgentSettings` (requires
        ``ANTHROPIC_API_KEY``).
    max_tokens, temperature
        Generation knobs passed to the provider.
    """
    llm = provider if provider is not None else make_default_provider()
    return llm.generate(
        build_user_prompt(metrics),
        system=SYSTEM_PROMPT,
        max_tokens=max_tokens,
        temperature=temperature,
    )
