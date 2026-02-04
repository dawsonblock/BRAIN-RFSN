# rfsn_replay.py
from __future__ import annotations

import argparse
from rfsn_kernel.replay import verify_ledger_chain, verify_gate_determinism


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    ok_chain, errs_chain = verify_ledger_chain(args.ledger)
    ok_gate, errs_gate = verify_gate_determinism(args.ledger)

    if not ok_chain:
        print("LEDGER_CHAIN_FAIL:", errs_chain)
        return 2
    if not ok_gate:
        print("GATE_DETERMINISM_FAIL:", errs_gate)
        return 3

    print("REPLAY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
