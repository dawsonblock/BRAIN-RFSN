# rfsn_companion/proposer_variants.py
from __future__ import annotations

from typing import Callable, Dict
from rfsn_kernel.types import StateSnapshot, Proposal

from .proposers.baseline import propose_baseline
from .proposers.read_then_test import propose_read_then_test
from .proposers.read_patch_test import propose_read_patch_test
from .proposers.brain_wrap import propose_brain
from .proposers.trace_read_then_test import propose_trace_read_then_test
from .proposers.llm_patch import propose_llm_patch


PROPOSER_BY_VARIANT: Dict[str, Callable[[StateSnapshot], Proposal]] = {
    "v0_minimal": propose_baseline,
    "v2_read_then_plan": propose_read_then_test,
    "v1_patch_then_test": propose_read_patch_test,
    "v3_brain": propose_brain,
    "v4_trace_read": propose_trace_read_then_test,
    "v5_llm_patch": propose_llm_patch,
}


def select_proposer(variant_id: str) -> Callable[[StateSnapshot], Proposal]:
    return PROPOSER_BY_VARIANT.get(variant_id, propose_baseline)
