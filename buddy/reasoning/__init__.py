"""
Advanced Reasoning Module for Buddy AI

This module implements sophisticated reasoning capabilities including:
- Chain-of-Thought Plus with verification
- Tree of Thoughts exploration
- Analogical reasoning
- Causal inference
- Logical deduction
- Hybrid reasoning combining multiple strategies

## Usage

```python
from buddy.reasoning import AdvancedReasoning, ReasoningStrategy, AdvancedReasoningMixin

# Initialize reasoning engine
reasoner = AdvancedReasoning()

# Use specific strategy
result = reasoner.reason(
    "How can we solve climate change?",
    strategy=ReasoningStrategy.TREE_OF_THOUGHTS
)

# Use hybrid reasoning
result = reasoner.hybrid_reason("Complex problem requiring multiple approaches")

# Add to agent via mixin
class MyAgent(AdvancedReasoningMixin, Agent):
    def solve_problem(self, problem: str):
        return self.reason_advanced(problem, strategy=ReasoningStrategy.CHAIN_OF_THOUGHT_PLUS)
```

## Features

### Chain-of-Thought Plus
Enhanced chain-of-thought reasoning with step verification, contradiction detection,
and alternative path exploration when verification fails.

### Tree of Thoughts
Explores multiple reasoning paths simultaneously, building a tree of potential
thought processes and selecting the most promising path.

### Analogical Reasoning
Uses structural similarity to transfer knowledge from familiar domains to
novel problems, enabling creative problem-solving.

### Causal Inference
Identifies causal relationships, analyzes cause-and-effect chains, and
predicts outcomes based on causal models.

### Logical Deduction
Formal logical reasoning with proof validation, supporting modus ponens,
modus tollens, and other logical rules.

### Hybrid Reasoning
Combines multiple reasoning strategies to tackle complex problems requiring
different cognitive approaches.

## Verification System
- Step-by-step verification of reasoning chains
- Contradiction detection across reasoning steps
- Evidence validation and consistency checking
- Automatic alternative path generation when verification fails

## Strategy Selection
Intelligent strategy selection based on problem characteristics:
- Causal problems → Causal Inference
- Similarity problems → Analogical Reasoning
- Logical problems → Logical Deduction
- Complex problems → Tree of Thoughts
- General problems → Chain-of-Thought Plus
"""

from .advanced_reasoning import (
    AdvancedReasoning,
    AdvancedReasoningMixin,
    AnalogicalReasoning,
    CausalInference,
    ChainOfThoughtPlus,
    ConfidenceLevel,
    LogicalDeduction,
    ReasoningResult,
    ReasoningStep,
    ReasoningStrategy,
    StepType,
    StepVerifier,
    StrategySelector,
    TreeOfThoughts,
    VerificationResult,
)

__all__ = [
    "AdvancedReasoning",
    "AdvancedReasoningMixin",
    "ReasoningStrategy",
    "ReasoningResult",
    "ReasoningStep",
    "StepType",
    "ConfidenceLevel",
    "ChainOfThoughtPlus",
    "TreeOfThoughts",
    "AnalogicalReasoning",
    "CausalInference",
    "LogicalDeduction",
    "StrategySelector",
    "StepVerifier",
    "VerificationResult",
]
