# upstream_learner/episode.py
from __future__ import annotations

from dataclasses import dataclass
import time

from rfsn_kernel.types import StateSnapshot, Proposal
from rfsn_kernel.gate import gate
from rfsn_kernel.controller import execute_decision
from rfsn_kernel.ledger import append_ledger


@dataclass(frozen=True)
class EpisodeOutcome:
    decision_status: str
    tests_passed: bool
    wall_ms: int
    reward: float


def reward_from_results(tests_passed: bool, denied: bool) -> float:
    if denied:
        return 0.0
    return 1.0 if tests_passed else 0.0


def run_episode(*, ledger_path: str, state: StateSnapshot, proposal: Proposal) -> EpisodeOutcome:
    t0 = time.perf_counter()

    decision = gate(state, proposal)
    denied = not decision.allowed

    results = ()
    tests_passed = False
    decision_status = "DENY" if denied else "ALLOW"

    if not denied:
        results = execute_decision(state, decision)
        # if any RUN_TESTS action exists, treat its ok as tests_passed
        for r in results:
            if r.action.type == "RUN_TESTS":
                tests_passed = bool(r.output.get("ok"))
                break

    wall_ms = int((time.perf_counter() - t0) * 1000)
    reward = reward_from_results(tests_passed=tests_passed, denied=denied)

    append_ledger(
        ledger_path,
        state=state,
        proposal=proposal,
        decision=decision,
        results=results,
        meta={"wall_ms": wall_ms, "reward": reward, "decision_status": decision_status},
    )

    return EpisodeOutcome(decision_status=decision_status, tests_passed=tests_passed, wall_ms=wall_ms, reward=reward)
