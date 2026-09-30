from contextlib import contextmanager
from contextvars import ContextVar

PRICING = {
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


_costs: ContextVar = ContextVar("costs", default=None)


@contextmanager
def track_cost():
    """Collect the estimated cost (USD) of every print_usage call inside the block."""
    costs = []
    token = _costs.set(costs)
    try:
        yield lambda: sum(costs)
    finally:
        _costs.reset(token)


def print_usage(response, label: str = "API call"):
    u = response.usage
    inp, out = u.input_tokens, u.output_tokens
    cache_write = getattr(u, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(u, "cache_read_input_tokens", 0) or 0

    print(f"  [{label}] tokens  in={inp:,}  out={out:,}", end="")
    if cache_write or cache_read:
        print(f"  cache_write={cache_write:,}  cache_read={cache_read:,}", end="")
    print()

    in_rate, out_rate = PRICING.get(response.model, (0, 0))
    if in_rate:
        cost = (inp * in_rate + out * out_rate) / 1_000_000
        print(f"  [{label}] est. cost ${cost:.4f}")
        if _costs.get() is not None:
            _costs.get().append(cost)
