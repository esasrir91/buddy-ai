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

__version__ = "2.1.3"
__author__ = "Sriram Sangeeth Mantha"
__email__ = "sriram.sangeet@gmail.com"
__license__ = "MIT"
__description__ = "A comprehensive Python framework for building and deploying AI agents"

# Core imports for easy access
from buddy.agent import Agent
from buddy.team import Team
from buddy.models.base import Model
from buddy.tools import Toolkit
from buddy.tools.function import Function

# Advanced features
try:
    from buddy.planning import PlanningAgent, ExecutionPlan, PlanStep, PlanStatus
    PLANNING_AVAILABLE = True
except ImportError:
    PLANNING_AVAILABLE = False

try:
    from buddy.multimodal import (
        MultiModalAgent, 
        ModalityType, 
        MultiModalResponse,
        ImageAnalysis,
        AudioAnalysis, 
        VideoAnalysis
    )
    MULTIMODAL_AVAILABLE = True
except ImportError:
    MULTIMODAL_AVAILABLE = False

try:
    from buddy.agent.evolution import (
        EvolutionaryMixin,
        AgentGenome,
        EvolutionStrategy,
        FitnessEvaluator
    )
    EVOLUTION_AVAILABLE = True
except ImportError:
    EVOLUTION_AVAILABLE = False

try:
    from buddy.reasoning import (
        AdvancedReasoning,
        AdvancedReasoningMixin,
        ReasoningStrategy,
        ReasoningResult
    )
    REASONING_AVAILABLE = True
except ImportError:
    REASONING_AVAILABLE = False

try:
    from buddy.agent.personality import (
        PersonalityEngine,
        PersonalityMixin,
        PersonalityProfile,
        EmotionalState,
        CommunicationStyle
    )
    PERSONALITY_AVAILABLE = True
except ImportError:
    PERSONALITY_AVAILABLE = False

try:
    from buddy.security import (
        AdversarialProtectionSystem,
        AdversarialProtectionMixin,
        SecurityConfig,
        ThreatLevel,
        SecurityAction
    )
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False

try:
    from buddy.pulse import (
        PulseEmployee,
        EmployeeProfile,
        KTSession,
        KTSourceType,
        KTSummary,
        MeetingNotes,
        WorkItem,
        ProfessionalMemory,
        OnboardingWorkflow,
    )
    PULSE_AVAILABLE = True
except ImportError:
    PULSE_AVAILABLE = False

# Legacy imports for compatibility
try:
    from buddy.memory.agent import AgentMemory
    from buddy.knowledge.agent import AgentKnowledge
    from buddy.workflow import Workflow
    from buddy.run import run
except ImportError:
    pass

# Feature availability flags
__features__ = {
    "planning": PLANNING_AVAILABLE,
    "multimodal": MULTIMODAL_AVAILABLE,
    "evolution": EVOLUTION_AVAILABLE,
    "reasoning": REASONING_AVAILABLE,
    "personality": PERSONALITY_AVAILABLE,
    "security": SECURITY_AVAILABLE,
    "pulse": PULSE_AVAILABLE,
    "core": True
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
        "author": __author__
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
    "__features__"
]