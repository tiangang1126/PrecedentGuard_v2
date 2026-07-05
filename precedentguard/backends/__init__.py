"""Guard-model backends (HuggingFace-hosted).

All three vendors (Meta / Google / IBM) are covered by lightweight subclasses
of `HFGuardBackend`, which handles lazy transformers loading and a shared
prompt-hash cache. Concrete backends override the chat template and output
parser to match each vendor's convention.
"""

from precedentguard.backends.base import HFGuardBackend, ScoreFn
from precedentguard.backends.granite import (
    GRANITE_DEFAULT,
    GRANITE_LARGE,
    GraniteGuardianBackend,
)
from precedentguard.backends.llamaguard import (
    LLAMAGUARD_DEFAULT,
    LLAMAGUARD_LARGE,
    LlamaGuardBackend,
)
from precedentguard.backends.shieldgemma import (
    SHIELDGEMMA_DEFAULT,
    ShieldGemmaBackend,
)

__all__ = [
    "GRANITE_DEFAULT",
    "GRANITE_LARGE",
    "GraniteGuardianBackend",
    "HFGuardBackend",
    "LLAMAGUARD_DEFAULT",
    "LLAMAGUARD_LARGE",
    "LlamaGuardBackend",
    "SHIELDGEMMA_DEFAULT",
    "ScoreFn",
    "ShieldGemmaBackend",
]
