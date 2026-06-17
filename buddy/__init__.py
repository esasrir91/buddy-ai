"""
Buddy AI - Advanced AI Agent Framework

A comprehensive Python framework for building, deploying, and managing intelligent AI agents.
Designed with enterprise-grade capabilities for sophisticated AI applications.

Key Features:
- Multi-model LLM support (OpenAI, Anthropic, Google, Cohere, AWS, Azure, etc.)
- Intelligent agent management with persistent memory
- Extensible tool system and knowledge management
- Multi-agent team collaboration
- Workflow automation and orchestration
- Multiple deployment options

Author: Sriram Sangeeth Mantha
License: MIT
"""

__version__ = "2.2.1"
__author__ = "Sriram Sangeeth Mantha"
__email__ = "sriram.sangeet@gmail.com"
__license__ = "MIT"
__description__ = "A comprehensive Python framework for building and deploying AI agents"

# ---------------------------------------------------------------------------
# Lazy feature detection — no heavy imports at package load time.
# Actual classes are imported on first attribute access via __getattr__.
# This keeps `buddy --help` and `import buddy` fast (<0.5 s).
# ---------------------------------------------------------------------------
import importlib.util as _importlib_util  # noqa: E402 (used below too)
import os as _os

# _pkg_dir = directory of this __init__.py (i.e. the buddy/ folder)
_pkg_dir = _os.path.dirname(__file__)


def _has_module(name: str) -> bool:
    """Check whether an *installed* (non-buddy) package is available without importing it."""
    return _importlib_util.find_spec(name) is not None


def _has_subpackage(rel_path: str) -> bool:
    """Check whether a buddy sub-package exists by filesystem path — zero import cost."""
    return _os.path.isdir(_os.path.join(_pkg_dir, rel_path))


# Feature flags via fast filesystem check (no import machinery involved).
def _has_file(*parts: str) -> bool:
    return _os.path.isfile(_os.path.join(_pkg_dir, *parts))

PLANNING_AVAILABLE    = _has_subpackage("planning")
MULTIMODAL_AVAILABLE  = _has_subpackage("multimodal")
EVOLUTION_AVAILABLE   = _has_file("agent", "evolution.py")
REASONING_AVAILABLE   = _has_subpackage("reasoning")
PERSONALITY_AVAILABLE = _has_file("agent", "personality.py")
SECURITY_AVAILABLE    = _has_subpackage("security")
PULSE_AVAILABLE       = _has_subpackage("pulse")


# ---------------------------------------------------------------------------
# Lazy __getattr__ — import heavy objects only when first accessed.
# This means `from buddy import Agent` still works, but doesn't slow down
# `buddy --help` or scripts that only need version info.
# ---------------------------------------------------------------------------
_LAZY_MAP = {
    # Core
    "Agent":        ("buddy.agent",                 "Agent"),
    "Model":        ("buddy.models.base",            "Model"),
    "Team":         ("buddy.team",                   "Team"),
    "Toolkit":      ("buddy.tools",                  "Toolkit"),
    "Function":     ("buddy.tools.function",         "Function"),
    # Memory / knowledge
    "AgentMemory":  ("buddy.memory.agent",           "AgentMemory"),
    "AgentKnowledge":("buddy.knowledge.agent",       "AgentKnowledge"),
    # Workflow / run helpers
    "Workflow":     ("buddy.workflow",               "Workflow"),
    "run":          ("buddy.run",                    "run"),
    # Planning
    "PlanningAgent":("buddy.planning",               "PlanningAgent"),
    "ExecutionPlan":("buddy.planning",               "ExecutionPlan"),
    "PlanStep":     ("buddy.planning",               "PlanStep"),
    "PlanStatus":   ("buddy.planning",               "PlanStatus"),
    # Multi-modal
    "MultiModalAgent":  ("buddy.multimodal",         "MultiModalAgent"),
    "ImageAnalysis":    ("buddy.multimodal",         "ImageAnalysis"),
    "AudioAnalysis":    ("buddy.multimodal",         "AudioAnalysis"),
    "VideoAnalysis":    ("buddy.multimodal",         "VideoAnalysis"),
    "MultiModalResponse":("buddy.multimodal",        "MultiModalResponse"),
    "ModalityType":     ("buddy.multimodal",         "ModalityType"),
    # Evolution
    "AgentGenome":      ("buddy.agent.evolution",    "AgentGenome"),
    "EvolutionaryMixin":("buddy.agent.evolution",    "EvolutionaryMixin"),
    "EvolutionStrategy":("buddy.agent.evolution",    "EvolutionStrategy"),
    "FitnessEvaluator": ("buddy.agent.evolution",    "FitnessEvaluator"),
    # Reasoning
    "AdvancedReasoning":    ("buddy.reasoning",      "AdvancedReasoning"),
    "AdvancedReasoningMixin":("buddy.reasoning",     "AdvancedReasoningMixin"),
    "ReasoningResult":      ("buddy.reasoning",      "ReasoningResult"),
    "ReasoningStrategy":    ("buddy.reasoning",      "ReasoningStrategy"),
    # Personality
    "PersonalityEngine":    ("buddy.agent.personality", "PersonalityEngine"),
    "PersonalityMixin":     ("buddy.agent.personality", "PersonalityMixin"),
    "PersonalityProfile":   ("buddy.agent.personality", "PersonalityProfile"),
    "CommunicationStyle":   ("buddy.agent.personality", "CommunicationStyle"),
    "EmotionalState":       ("buddy.agent.personality", "EmotionalState"),
    # Security
    "AdversarialProtectionSystem":("buddy.security", "AdversarialProtectionSystem"),
    "AdversarialProtectionMixin": ("buddy.security", "AdversarialProtectionMixin"),
    "SecurityConfig":             ("buddy.security", "SecurityConfig"),
    "SecurityAction":             ("buddy.security", "SecurityAction"),
    "ThreatLevel":                ("buddy.security", "ThreatLevel"),
    # PULSE
    "PulseEmployee":    ("buddy.pulse", "PulseEmployee"),
    "ProfessionalMemory":("buddy.pulse","ProfessionalMemory"),
    "EmployeeProfile":  ("buddy.pulse", "EmployeeProfile"),
    "KTSession":        ("buddy.pulse", "KTSession"),
    "KTSourceType":     ("buddy.pulse", "KTSourceType"),
    "KTSummary":        ("buddy.pulse", "KTSummary"),
    "MeetingNotes":     ("buddy.pulse", "MeetingNotes"),
    "OnboardingWorkflow":("buddy.pulse","OnboardingWorkflow"),
    "WorkItem":         ("buddy.pulse", "WorkItem"),
}


def __getattr__(name: str):
    if name in _LAZY_MAP:
        import importlib as _il
        module_path, attr = _LAZY_MAP[name]
        mod = _il.import_module(module_path)
        obj = getattr(mod, attr)
        # Cache in module globals so subsequent accesses are free
        globals()[name] = obj
        return obj
    raise AttributeError(f"module 'buddy' has no attribute {name!r}")

# Third-party integration availability (fast spec-check, no import)
LANGCHAIN_AVAILABLE = _has_module("langchain_core")
LANGGRAPH_AVAILABLE = _has_module("langgraph")

# Feature availability flags
__features__ = {
    "planning": PLANNING_AVAILABLE,
    "multimodal": MULTIMODAL_AVAILABLE,
    "evolution": EVOLUTION_AVAILABLE,
    "reasoning": REASONING_AVAILABLE,
    "personality": PERSONALITY_AVAILABLE,
    "security": SECURITY_AVAILABLE,
    "pulse": PULSE_AVAILABLE,
    "langchain": LANGCHAIN_AVAILABLE,
    "langgraph": LANGGRAPH_AVAILABLE,
    "core": True,
}


def get_available_features():
    """Get list of available features in current installation"""
    available = []
    for feature, available_flag in __features__.items():
        if available_flag:
            available.append(feature)
    return available


def check_feature(feature_name: str) -> bool:
    """Check if a specific feature is available"""
    return __features__.get(feature_name, False)


def get_version_info():
    """Get comprehensive version and feature information"""
    return {
        "version": __version__,
        "features": __features__,
        "available_features": get_available_features(),
        "description": __description__,
        "author": __author__,
    }


__all__ = [
    # Core
    "Agent",
    "Team",
    "Model",
    "Function",
    "Toolkit",
    "AgentMemory",
    "AgentKnowledge",
    # Advanced features (conditional)
    "PlanningAgent",
    "ExecutionPlan",
    "PlanStep",
    "PlanStatus",
    "MultiModalAgent",
    "ModalityType",
    "MultiModalResponse",
    "ImageAnalysis",
    "AudioAnalysis",
    "VideoAnalysis",
    "EvolutionaryMixin",
    "AgentGenome",
    "EvolutionStrategy",
    "FitnessEvaluator",
    "AdvancedReasoning",
    "AdvancedReasoningMixin",
    "ReasoningStrategy",
    "ReasoningResult",
    "PersonalityEngine",
    "PersonalityMixin",
    "PersonalityProfile",
    "EmotionalState",
    "CommunicationStyle",
    "AdversarialProtectionSystem",
    "AdversarialProtectionMixin",
    "SecurityConfig",
    "ThreatLevel",
    "SecurityAction",
    # PULSE — Virtual Employee
    "PulseEmployee",
    "EmployeeProfile",
    "KTSession",
    "KTSourceType",
    "KTSummary",
    "MeetingNotes",
    "WorkItem",
    "ProfessionalMemory",
    "OnboardingWorkflow",
    # Utility functions
    "get_available_features",
    "check_feature",
    "get_version_info",
    # Metadata
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__description__",
    "__features__",
]
