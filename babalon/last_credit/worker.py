"""Trusted child hosting one capability-free JavaScript guest for one proposal."""
from pathlib import Path
import sys

import quickjs


def guest_context():
    context = quickjs.Context()
    context.set_memory_limit(4 << 20)
    context.set_max_stack_size(128 << 10)
    context.set_time_limit(0.1)
    return context


def main():
    wire = sys.stdin.buffer.read(16385)
    if len(wire) > 16384:
        raise ValueError("oversized observation")
    context = guest_context()
    context.eval(Path(__file__).with_name("policy.js").read_text(encoding="utf-8"))
    output = context.get("propose")(wire.decode("utf-8"))
    if type(output) is not str or len(output.encode()) > 4096:
        raise ValueError("invalid proposal size")
    print(output)


if __name__ == "__main__":
    main()
