from enum import Enum

from pydantic import BaseModel


class AttackCategory(str, Enum):
    PROMPT_INJECTION_DIRECT = "prompt_injection_direct"
    PROMPT_INJECTION_INDIRECT = "prompt_injection_indirect"
    INSECURE_OUTPUT_HANDLING = "insecure_output_handling"
    MODEL_THEFT = "model_theft"
    SENSITIVE_INFORMATION_DISCLOSURE = "sensitive_information_disclosure"
    INSECURE_PLUGIN_DESIGN = "insecure_plugin_design"
    EXCESSIVE_AGENCY = "excessive_agency"


class Variant(str, Enum):
    A = "a"  # Claude Sonnet via Anthropic API
    B = "b"  # Llama 3.1 8B via Groq
    C = "c"  # Multi-model pipeline (Llama Guard + Llama + Presidio)


class Attack(BaseModel):
    category: AttackCategory
    technique: str
    payload: str
    variant: Variant
