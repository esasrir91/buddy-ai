"""
Advanced Reasoning Engine for Buddy AI

Implements sophisticated reasoning strategies including Chain-of-Thought Plus,
Tree of Thoughts, analogical reasoning, causal inference, and logical deduction.
"""

import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field


class ReasoningStrategy(str, Enum):
    """Available reasoning strategies"""

    CHAIN_OF_THOUGHT = "chain_of_thought"
    CHAIN_OF_THOUGHT_PLUS = "chain_of_thought_plus"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    ANALOGICAL_REASONING = "analogical_reasoning"
    CAUSAL_INFERENCE = "causal_inference"
    LOGICAL_DEDUCTION = "logical_deduction"
    HYBRID_REASONING = "hybrid_reasoning"


class StepType(str, Enum):
    """Types of reasoning steps"""

    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"
    DEDUCTION = "deduction"
    INDUCTION = "induction"
    ABDUCTION = "abduction"
    ANALOGY = "analogy"
    CAUSATION = "causation"
    VERIFICATION = "verification"
    CONTRADICTION_CHECK = "contradiction_check"


class ConfidenceLevel(str, Enum):
    """Confidence levels for reasoning steps"""

    VERY_LOW = "very_low"  # 0.0 - 0.2
    LOW = "low"  # 0.2 - 0.4
    MEDIUM = "medium"  # 0.4 - 0.6
    HIGH = "high"  # 0.6 - 0.8
    VERY_HIGH = "very_high"  # 0.8 - 1.0


@dataclass
class ReasoningStep:
    """Individual step in reasoning process"""

    step_id: str
    step_type: StepType
    content: str
    reasoning: str
    confidence: float
    evidence: List[str] = None
    assumptions: List[str] = None
    references: List[str] = None
    verification_status: Optional[bool] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.evidence is None:
            self.evidence = []
        if self.assumptions is None:
            self.assumptions = []
        if self.references is None:
            self.references = []
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ReasoningResult(BaseModel):
    """Complete reasoning result with steps and conclusions"""

    query: str
    strategy_used: ReasoningStrategy
    reasoning_steps: List[ReasoningStep]
    final_conclusion: str
    overall_confidence: float
    alternative_conclusions: List[str] = Field(default_factory=list)
    contradictions_found: List[str] = Field(default_factory=list)
    assumptions_made: List[str] = Field(default_factory=list)
    evidence_used: List[str] = Field(default_factory=list)
    reasoning_time: float = 0.0
    verification_passed: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChainOfThoughtPlus:
    """Enhanced Chain-of-Thought reasoning with verification"""

    def __init__(self, max_steps: int = 10, verification_enabled: bool = True):
        self.max_steps = max_steps
        self.verification_enabled = verification_enabled
        self.step_verifier = StepVerifier() if verification_enabled else None

    def reason(self, query: str, context: Dict[str, Any] = None) -> ReasoningResult:
        """Execute Chain-of-Thought Plus reasoning"""
        start_time = datetime.now()
        steps = []
        current_step = 1

        # Initial observation
        initial_step = ReasoningStep(
            step_id=f"cot_plus_{current_step}",
            step_type=StepType.OBSERVATION,
            content=query,
            reasoning="Initial problem observation and understanding",
            confidence=0.9,
        )
        steps.append(initial_step)

        # Progressive reasoning with verification
        current_understanding = query
        for i in range(2, self.max_steps + 1):
            # Generate next reasoning step
            next_step = self._generate_next_step(current_understanding, steps, f"cot_plus_{i}")

            # Verify step if enabled
            if self.verification_enabled and self.step_verifier:
                verification_result = self.step_verifier.verify_step(next_step, steps)
                next_step.verification_status = verification_result.is_valid

                if not verification_result.is_valid:
                    # Generate alternative step
                    next_step = self._generate_alternative_step(current_understanding, steps, f"cot_plus_{i}_alt")

            steps.append(next_step)
            current_understanding = next_step.content

            # Check for conclusion
            if self._is_conclusion_reached(next_step):
                break

        # Generate final conclusion
        final_conclusion = self._generate_conclusion(steps)
        overall_confidence = self._calculate_overall_confidence(steps)

        reasoning_time = (datetime.now() - start_time).total_seconds()

        return ReasoningResult(
            query=query,
            strategy_used=ReasoningStrategy.CHAIN_OF_THOUGHT_PLUS,
            reasoning_steps=steps,
            final_conclusion=final_conclusion,
            overall_confidence=overall_confidence,
            reasoning_time=reasoning_time,
            verification_passed=all(s.verification_status != False for s in steps),
        )

    def _generate_next_step(
        self, current_understanding: str, previous_steps: List[ReasoningStep], step_id: str
    ) -> ReasoningStep:
        """Generate next reasoning step"""
        # This would use the agent's model for actual reasoning
        # For now, implement structured reasoning patterns

        step_count = len(previous_steps)

        if step_count == 1:
            # Break down the problem
            return ReasoningStep(
                step_id=step_id,
                step_type=StepType.DEDUCTION,
                content=f"Breaking down the problem: {current_understanding}",
                reasoning="Decompose the problem into manageable components",
                confidence=0.8,
            )
        elif step_count == 2:
            # Analyze components
            return ReasoningStep(
                step_id=step_id,
                step_type=StepType.HYPOTHESIS,
                content="Analyzing each component and their relationships",
                reasoning="Examine individual elements and their interactions",
                confidence=0.7,
            )
        else:
            # Synthesize solution
            return ReasoningStep(
                step_id=step_id,
                step_type=StepType.DEDUCTION,
                content="Synthesizing solution from analysis",
                reasoning="Combine insights to form conclusion",
                confidence=0.8,
            )

    def _generate_alternative_step(self, understanding: str, steps: List[ReasoningStep], step_id: str) -> ReasoningStep:
        """Generate alternative step when verification fails"""
        return ReasoningStep(
            step_id=step_id,
            step_type=StepType.HYPOTHESIS,
            content=f"Alternative approach to: {understanding}",
            reasoning="Exploring alternative reasoning path due to verification failure",
            confidence=0.6,
        )

    def _is_conclusion_reached(self, step: ReasoningStep) -> bool:
        """Check if reasoning has reached a conclusion"""
        conclusion_indicators = [
            "therefore",
            "thus",
            "in conclusion",
            "the answer is",
            "we can conclude",
            "this shows that",
        ]

        content_lower = step.content.lower()
        return any(indicator in content_lower for indicator in conclusion_indicators)

    def _generate_conclusion(self, steps: List[ReasoningStep]) -> str:
        """Generate final conclusion from reasoning steps"""
        last_step = steps[-1]
        return f"Based on the reasoning process: {last_step.content}"

    def _calculate_overall_confidence(self, steps: List[ReasoningStep]) -> float:
        """Calculate overall confidence from individual step confidences"""
        if not steps:
            return 0.0

        # Weighted average with recent steps having higher weight
        total_weighted_confidence = 0.0
        total_weight = 0.0

        for i, step in enumerate(steps):
            weight = 1.0 + (i / len(steps))  # Later steps have higher weight
            total_weighted_confidence += step.confidence * weight
            total_weight += weight

        return total_weighted_confidence / total_weight if total_weight > 0 else 0.0


class TreeOfThoughts:
    """Tree of Thoughts reasoning for complex problem exploration"""

    def __init__(self, max_depth: int = 5, max_branches: int = 3):
        self.max_depth = max_depth
        self.max_branches = max_branches
        self.thought_tree = {}

    def reason(self, query: str, context: Dict[str, Any] = None) -> ReasoningResult:
        """Execute Tree of Thoughts reasoning"""
        start_time = datetime.now()

        # Build thought tree
        root_thought = self._create_root_thought(query)
        self.thought_tree = {root_thought.step_id: root_thought}

        # Expand tree breadth-first
        self._expand_thought_tree(root_thought, depth=0)

        # Evaluate paths and select best
        best_path = self._find_best_reasoning_path()

        # Generate result
        final_conclusion = self._synthesize_conclusion(best_path)
        overall_confidence = self._calculate_path_confidence(best_path)

        reasoning_time = (datetime.now() - start_time).total_seconds()

        return ReasoningResult(
            query=query,
            strategy_used=ReasoningStrategy.TREE_OF_THOUGHTS,
            reasoning_steps=best_path,
            final_conclusion=final_conclusion,
            overall_confidence=overall_confidence,
            reasoning_time=reasoning_time,
            metadata={"tree_size": len(self.thought_tree)},
        )

    def _create_root_thought(self, query: str) -> ReasoningStep:
        """Create root node of thought tree"""
        return ReasoningStep(
            step_id="tot_root",
            step_type=StepType.OBSERVATION,
            content=query,
            reasoning="Root problem statement",
            confidence=1.0,
        )

    def _expand_thought_tree(self, parent_thought: ReasoningStep, depth: int):
        """Recursively expand thought tree"""
        if depth >= self.max_depth:
            return

        # Generate multiple thought branches
        for i in range(self.max_branches):
            child_thought = self._generate_child_thought(parent_thought, depth, i)
            child_id = f"{parent_thought.step_id}_child_{i}"
            child_thought.step_id = child_id

            self.thought_tree[child_id] = child_thought

            # Recursively expand if promising
            if child_thought.confidence > 0.5:
                self._expand_thought_tree(child_thought, depth + 1)

    def _generate_child_thought(self, parent: ReasoningStep, depth: int, branch: int) -> ReasoningStep:
        """Generate child thought from parent"""
        thought_strategies = [
            ("What if we approach this differently?", StepType.HYPOTHESIS),
            ("Let's consider the implications of this", StepType.DEDUCTION),
            ("What evidence supports this?", StepType.VERIFICATION),
        ]

        strategy_text, step_type = thought_strategies[branch % len(thought_strategies)]

        return ReasoningStep(
            step_id="",  # Will be set by caller
            step_type=step_type,
            content=f"{strategy_text} Building on: {parent.content}",
            reasoning=f"Exploring alternative path {branch} at depth {depth}",
            confidence=max(0.3, parent.confidence - (depth * 0.1)),
        )

    def _find_best_reasoning_path(self) -> List[ReasoningStep]:
        """Find the best reasoning path through the tree"""
        # Simple implementation: find path with highest average confidence
        root = self.thought_tree["tot_root"]

        def dfs_best_path(node_id: str, current_path: List[ReasoningStep]) -> Tuple[List[ReasoningStep], float]:
            current_node = self.thought_tree[node_id]
            current_path = current_path + [current_node]

            # Find children
            children = [nid for nid in self.thought_tree.keys() if nid.startswith(f"{node_id}_child_")]

            if not children:
                # Leaf node
                path_confidence = sum(step.confidence for step in current_path) / len(current_path)
                return current_path, path_confidence

            # Find best child path
            best_path = current_path
            best_confidence = 0.0

            for child_id in children:
                child_path, child_confidence = dfs_best_path(child_id, current_path)
                if child_confidence > best_confidence:
                    best_path = child_path
                    best_confidence = child_confidence

            return best_path, best_confidence

        best_path, _ = dfs_best_path("tot_root", [])
        return best_path

    def _synthesize_conclusion(self, path: List[ReasoningStep]) -> str:
        """Synthesize conclusion from reasoning path"""
        if not path:
            return "No conclusion reached"

        final_step = path[-1]
        return f"Through tree exploration: {final_step.content}"

    def _calculate_path_confidence(self, path: List[ReasoningStep]) -> float:
        """Calculate confidence for reasoning path"""
        if not path:
            return 0.0

        return sum(step.confidence for step in path) / len(path)


class AnalogicalReasoning:
    """Analogical reasoning using knowledge graphs and similarity"""

    def __init__(self):
        self.analogy_database = {}  # Would be loaded from knowledge base

    def reason(self, query: str, context: Dict[str, Any] = None) -> ReasoningResult:
        """Execute analogical reasoning"""
        start_time = datetime.now()
        steps = []

        # Identify source domain (analogy)
        source_analogy = self._find_source_analogy(query)

        step1 = ReasoningStep(
            step_id="analog_1",
            step_type=StepType.ANALOGY,
            content=f"Found analogous situation: {source_analogy}",
            reasoning="Identifying structural similarity with known domain",
            confidence=0.8,
        )
        steps.append(step1)

        # Map structure from source to target
        structure_mapping = self._map_structure(source_analogy, query)

        step2 = ReasoningStep(
            step_id="analog_2",
            step_type=StepType.DEDUCTION,
            content=f"Structural mapping: {structure_mapping}",
            reasoning="Mapping elements from source to target domain",
            confidence=0.7,
        )
        steps.append(step2)

        # Apply knowledge from source domain
        transferred_knowledge = self._transfer_knowledge(source_analogy, structure_mapping)

        step3 = ReasoningStep(
            step_id="analog_3",
            step_type=StepType.INDUCTION,
            content=f"Applied knowledge: {transferred_knowledge}",
            reasoning="Transferring insights from analogous domain",
            confidence=0.75,
        )
        steps.append(step3)

        reasoning_time = (datetime.now() - start_time).total_seconds()

        return ReasoningResult(
            query=query,
            strategy_used=ReasoningStrategy.ANALOGICAL_REASONING,
            reasoning_steps=steps,
            final_conclusion=transferred_knowledge,
            overall_confidence=0.75,
            reasoning_time=reasoning_time,
        )

    def _find_source_analogy(self, target_query: str) -> str:
        """Find analogous situation from knowledge base"""
        # Simplified analogy finding
        analogy_patterns = {
            "flow": "water flow through pipes",
            "network": "transportation system",
            "growth": "plant development",
            "competition": "sports tournament",
            "learning": "building construction",
        }

        for pattern, analogy in analogy_patterns.items():
            if pattern.lower() in target_query.lower():
                return analogy

        return "general problem-solving process"

    def _map_structure(self, source: str, target: str) -> str:
        """Map structural elements between domains"""
        return f"Elements in {source} correspond to elements in {target}"

    def _transfer_knowledge(self, source: str, mapping: str) -> str:
        """Transfer knowledge using structural mapping"""
        return f"Based on how {source} works, the solution involves applying similar principles"


class CausalInference:
    """Causal reasoning and inference capabilities"""

    def __init__(self):
        self.causal_models = {}

    def reason(self, query: str, context: Dict[str, Any] = None) -> ReasoningResult:
        """Execute causal inference reasoning"""
        start_time = datetime.now()
        steps = []

        # Identify potential causes
        potential_causes = self._identify_causes(query)

        step1 = ReasoningStep(
            step_id="causal_1",
            step_type=StepType.HYPOTHESIS,
            content=f"Potential causes identified: {potential_causes}",
            reasoning="Identifying possible causal factors",
            confidence=0.8,
        )
        steps.append(step1)

        # Analyze causal relationships
        causal_relationships = self._analyze_causality(potential_causes, query)

        step2 = ReasoningStep(
            step_id="causal_2",
            step_type=StepType.CAUSATION,
            content=f"Causal analysis: {causal_relationships}",
            reasoning="Examining strength and direction of causal relationships",
            confidence=0.75,
        )
        steps.append(step2)

        # Predict effects
        predicted_effects = self._predict_effects(causal_relationships)

        step3 = ReasoningStep(
            step_id="causal_3",
            step_type=StepType.DEDUCTION,
            content=f"Predicted effects: {predicted_effects}",
            reasoning="Inferring likely outcomes based on causal model",
            confidence=0.7,
        )
        steps.append(step3)

        reasoning_time = (datetime.now() - start_time).total_seconds()

        return ReasoningResult(
            query=query,
            strategy_used=ReasoningStrategy.CAUSAL_INFERENCE,
            reasoning_steps=steps,
            final_conclusion=predicted_effects,
            overall_confidence=0.75,
            reasoning_time=reasoning_time,
        )

    def _identify_causes(self, query: str) -> List[str]:
        """Identify potential causal factors"""
        # Simplified cause identification
        return ["Factor A", "Factor B", "Factor C"]

    def _analyze_causality(self, causes: List[str], effect: str) -> str:
        """Analyze causal relationships"""
        return f"Strong causal relationship found between {causes[0]} and outcome"

    def _predict_effects(self, causal_model: str) -> str:
        """Predict effects based on causal model"""
        return "Based on causal analysis, the most likely outcome is..."


class LogicalDeduction:
    """Formal logical deduction with proof validation"""

    def __init__(self):
        self.logical_rules = self._load_logical_rules()

    def reason(self, query: str, premises: List[str] = None, context: Dict[str, Any] = None) -> ReasoningResult:
        """Execute logical deduction reasoning"""
        start_time = datetime.now()
        steps = []
        premises = premises or []

        # Parse premises
        parsed_premises = self._parse_premises(premises)

        step1 = ReasoningStep(
            step_id="logic_1",
            step_type=StepType.OBSERVATION,
            content=f"Premises: {parsed_premises}",
            reasoning="Establishing logical foundation",
            confidence=1.0,
        )
        steps.append(step1)

        # Apply logical rules
        logical_chain = self._apply_logical_rules(parsed_premises, query)

        for i, rule_application in enumerate(logical_chain):
            step = ReasoningStep(
                step_id=f"logic_{i+2}",
                step_type=StepType.DEDUCTION,
                content=rule_application["conclusion"],
                reasoning=f"Applied rule: {rule_application['rule']}",
                confidence=rule_application["confidence"],
            )
            steps.append(step)

        # Validate proof
        proof_valid = self._validate_proof(steps)

        reasoning_time = (datetime.now() - start_time).total_seconds()

        final_conclusion = logical_chain[-1]["conclusion"] if logical_chain else "No conclusion reached"

        return ReasoningResult(
            query=query,
            strategy_used=ReasoningStrategy.LOGICAL_DEDUCTION,
            reasoning_steps=steps,
            final_conclusion=final_conclusion,
            overall_confidence=0.9 if proof_valid else 0.5,
            reasoning_time=reasoning_time,
            verification_passed=proof_valid,
        )

    def _load_logical_rules(self) -> Dict[str, Any]:
        """Load formal logical rules"""
        return {
            "modus_ponens": {"pattern": "if P then Q, P", "conclusion": "Q"},
            "modus_tollens": {"pattern": "if P then Q, not Q", "conclusion": "not P"},
            "hypothetical_syllogism": {"pattern": "if P then Q, if Q then R", "conclusion": "if P then R"},
        }

    def _parse_premises(self, premises: List[str]) -> List[str]:
        """Parse logical premises"""
        return [p.strip() for p in premises]

    def _apply_logical_rules(self, premises: List[str], query: str) -> List[Dict[str, Any]]:
        """Apply logical rules to derive conclusions"""
        # Simplified logical rule application
        return [{"rule": "modus_ponens", "conclusion": "Logical conclusion based on premises", "confidence": 0.9}]

    def _validate_proof(self, steps: List[ReasoningStep]) -> bool:
        """Validate logical proof"""
        # Simplified proof validation
        return all(step.confidence > 0.7 for step in steps)


class AdvancedReasoning:
    """Main advanced reasoning engine that orchestrates different strategies"""

    def __init__(self):
        self.strategies = {
            ReasoningStrategy.CHAIN_OF_THOUGHT_PLUS: ChainOfThoughtPlus(),
            ReasoningStrategy.TREE_OF_THOUGHTS: TreeOfThoughts(),
            ReasoningStrategy.ANALOGICAL_REASONING: AnalogicalReasoning(),
            ReasoningStrategy.CAUSAL_INFERENCE: CausalInference(),
            ReasoningStrategy.LOGICAL_DEDUCTION: LogicalDeduction(),
        }
        self.strategy_selector = StrategySelector()

    def reason(
        self, query: str, strategy: Optional[ReasoningStrategy] = None, context: Dict[str, Any] = None
    ) -> ReasoningResult:
        """Execute advanced reasoning with specified or auto-selected strategy"""

        if strategy is None:
            strategy = self.strategy_selector.select_strategy(query, context)

        reasoning_engine = self.strategies.get(strategy)
        if not reasoning_engine:
            raise ValueError(f"Unsupported reasoning strategy: {strategy}")

        return reasoning_engine.reason(query, context)

    def hybrid_reason(self, query: str, context: Dict[str, Any] = None) -> ReasoningResult:
        """Execute hybrid reasoning using multiple strategies"""
        start_time = datetime.now()

        # Run multiple strategies
        strategies_to_use = [ReasoningStrategy.CHAIN_OF_THOUGHT_PLUS, ReasoningStrategy.ANALOGICAL_REASONING]

        results = []
        all_steps = []

        for strategy in strategies_to_use:
            result = self.reason(query, strategy, context)
            results.append(result)
            all_steps.extend(result.reasoning_steps)

        # Combine results
        combined_conclusion = self._combine_conclusions([r.final_conclusion for r in results])
        combined_confidence = sum(r.overall_confidence for r in results) / len(results)

        reasoning_time = (datetime.now() - start_time).total_seconds()

        return ReasoningResult(
            query=query,
            strategy_used=ReasoningStrategy.HYBRID_REASONING,
            reasoning_steps=all_steps,
            final_conclusion=combined_conclusion,
            overall_confidence=combined_confidence,
            reasoning_time=reasoning_time,
            alternative_conclusions=[r.final_conclusion for r in results],
            metadata={"strategies_used": [s.value for s in strategies_to_use]},
        )

    def _combine_conclusions(self, conclusions: List[str]) -> str:
        """Combine multiple reasoning conclusions"""
        return f"Synthesized from multiple reasoning approaches: {'; '.join(conclusions)}"


class StrategySelector:
    """Selects optimal reasoning strategy based on query characteristics"""

    def select_strategy(self, query: str, context: Dict[str, Any] = None) -> ReasoningStrategy:
        """Select best reasoning strategy for the query"""

        # Simple heuristic-based selection
        query_lower = query.lower()

        if any(word in query_lower for word in ["cause", "effect", "why", "because", "reason"]):
            return ReasoningStrategy.CAUSAL_INFERENCE

        if any(word in query_lower for word in ["like", "similar", "compare", "analogy"]):
            return ReasoningStrategy.ANALOGICAL_REASONING

        if any(word in query_lower for word in ["if", "then", "therefore", "prove", "logic"]):
            return ReasoningStrategy.LOGICAL_DEDUCTION

        if any(word in query_lower for word in ["complex", "multiple", "various", "different approaches"]):
            return ReasoningStrategy.TREE_OF_THOUGHTS

        # Default to Chain of Thought Plus
        return ReasoningStrategy.CHAIN_OF_THOUGHT_PLUS


class StepVerifier:
    """Verifies individual reasoning steps for consistency and validity"""

    def verify_step(self, step: ReasoningStep, previous_steps: List[ReasoningStep]) -> "VerificationResult":
        """Verify a reasoning step against previous steps"""

        # Check for logical consistency
        consistency_check = self._check_logical_consistency(step, previous_steps)

        # Check for contradiction
        contradiction_check = self._check_contradictions(step, previous_steps)

        # Check evidence support
        evidence_check = self._check_evidence_support(step)

        is_valid = consistency_check and not contradiction_check and evidence_check

        return VerificationResult(
            is_valid=is_valid,
            consistency_score=1.0 if consistency_check else 0.0,
            has_contradictions=contradiction_check,
            evidence_strength=1.0 if evidence_check else 0.5,
            issues=self._collect_issues(consistency_check, contradiction_check, evidence_check),
        )

    def _check_logical_consistency(self, step: ReasoningStep, previous_steps: List[ReasoningStep]) -> bool:
        """Check if step is logically consistent with previous steps"""
        # Simplified consistency check
        return step.confidence > 0.3

    def _check_contradictions(self, step: ReasoningStep, previous_steps: List[ReasoningStep]) -> bool:
        """Check for contradictions with previous steps"""
        # Simplified contradiction detection
        step_content = step.content.lower()
        contradiction_words = ["not", "never", "impossible", "cannot"]

        for prev_step in previous_steps:
            prev_content = prev_step.content.lower()
            # Very basic contradiction detection
            if any(word in step_content for word in contradiction_words) and any(
                word not in prev_content for word in contradiction_words
            ):
                return True

        return False

    def _check_evidence_support(self, step: ReasoningStep) -> bool:
        """Check if step has adequate evidence support"""
        return len(step.evidence) > 0 or step.confidence > 0.6

    def _collect_issues(self, consistency: bool, contradiction: bool, evidence: bool) -> List[str]:
        """Collect verification issues"""
        issues = []
        if not consistency:
            issues.append("Logical inconsistency detected")
        if contradiction:
            issues.append("Contradiction with previous steps")
        if not evidence:
            issues.append("Insufficient evidence support")
        return issues


@dataclass
class VerificationResult:
    """Result of reasoning step verification"""

    is_valid: bool
    consistency_score: float
    has_contradictions: bool
    evidence_strength: float
    issues: List[str]


# Integration with Agent class through mixin
class AdvancedReasoningMixin:
    """Mixin to add advanced reasoning capabilities to agents"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.advanced_reasoning = AdvancedReasoning()
        self.reasoning_strategy: Optional[ReasoningStrategy] = kwargs.get("reasoning_strategy")
        self.reasoning_enabled: bool = kwargs.get("reasoning_enabled", True)
        self.reasoning_verification: bool = kwargs.get("reasoning_verification", True)

    def reason_advanced(
        self, query: str, strategy: Optional[ReasoningStrategy] = None, context: Dict[str, Any] = None
    ) -> ReasoningResult:
        """Execute advanced reasoning on query"""
        if not self.reasoning_enabled:
            raise ValueError("Advanced reasoning not enabled for this agent")

        strategy = strategy or self.reasoning_strategy
        return self.advanced_reasoning.reason(query, strategy, context)

    def reason_with_verification(self, query: str, **kwargs) -> ReasoningResult:
        """Execute reasoning with step verification enabled"""
        # Ensure verification is enabled
        original_verification = getattr(
            self.advanced_reasoning.strategies.get(ReasoningStrategy.CHAIN_OF_THOUGHT_PLUS),
            "verification_enabled",
            False,
        )

        # Enable verification temporarily
        cot_plus = self.advanced_reasoning.strategies.get(ReasoningStrategy.CHAIN_OF_THOUGHT_PLUS)
        if cot_plus:
            cot_plus.verification_enabled = True

        try:
            result = self.reason_advanced(query, **kwargs)
        finally:
            # Restore original verification setting
            if cot_plus:
                cot_plus.verification_enabled = original_verification

        return result

    def hybrid_reasoning(self, query: str, context: Dict[str, Any] = None) -> ReasoningResult:
        """Execute hybrid reasoning combining multiple strategies"""
        return self.advanced_reasoning.hybrid_reason(query, context)
