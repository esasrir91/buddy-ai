"""
Evolutionary enhancements for the Buddy Agent class.

Extends agents with self-improvement capabilities through genetic algorithms,
performance-based adaptation, and autonomous optimization.
"""

import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional
from uuid import uuid4

import numpy as np
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from buddy.agent import Agent


class EvolutionStrategy(str, Enum):
    """Evolution strategies for agent optimization"""

    GENETIC = "genetic"
    DIFFERENTIAL = "differential"
    PARTICLE_SWARM = "particle_swarm"
    BAYESIAN = "bayesian"


class MutationType(str, Enum):
    """Types of mutations for agent evolution"""

    INSTRUCTION_MUTATION = "instruction"
    PARAMETER_MUTATION = "parameter"
    TOOL_MUTATION = "tool"
    REASONING_MUTATION = "reasoning"
    PERSONALITY_MUTATION = "personality"


@dataclass
class FitnessMetrics:
    """Metrics for evaluating agent fitness"""

    accuracy_score: float = 0.0
    response_time: float = 0.0
    user_satisfaction: float = 0.0
    task_completion_rate: float = 0.0
    error_rate: float = 0.0
    efficiency_score: float = 0.0
    adaptability_score: float = 0.0
    consistency_score: float = 0.0

    @property
    def overall_fitness(self) -> float:
        """Calculate overall fitness score"""
        weights = {
            "accuracy": 0.25,
            "response_time": 0.15,
            "satisfaction": 0.20,
            "completion": 0.20,
            "error": -0.10,  # Negative weight for errors
            "efficiency": 0.15,
            "adaptability": 0.10,
            "consistency": 0.15,
        }

        # Normalize response time (lower is better)
        normalized_response_time = max(0, 1.0 - (self.response_time / 10.0))

        score = (
            weights["accuracy"] * self.accuracy_score
            + weights["response_time"] * normalized_response_time
            + weights["satisfaction"] * self.user_satisfaction
            + weights["completion"] * self.task_completion_rate
            + weights["error"] * (1.0 - self.error_rate)
            + weights["efficiency"] * self.efficiency_score
            + weights["adaptability"] * self.adaptability_score
            + weights["consistency"] * self.consistency_score
        )

        return max(0.0, min(1.0, score))


class AgentGenome(BaseModel):
    """Genetic representation of agent configuration"""

    genome_id: str = Field(default_factory=lambda: str(uuid4()))
    generation: int = 0
    parent_genomes: List[str] = Field(default_factory=list)

    # Core agent properties
    instructions: str = ""
    temperature: float = 0.7
    max_tokens: int = 1000
    max_loops: int = 1
    reasoning_depth: int = 3

    # Personality traits (0.0 - 1.0)
    creativity: float = 0.5
    analytical_thinking: float = 0.5
    empathy: float = 0.5
    assertiveness: float = 0.5
    curiosity: float = 0.5
    patience: float = 0.5

    # Tool preferences
    preferred_tools: List[str] = Field(default_factory=list)
    tool_usage_strategy: Literal["conservative", "balanced", "aggressive"] = "balanced"

    # Performance genes
    response_style: Literal["concise", "detailed", "adaptive"] = "adaptive"
    error_handling_strategy: Literal["strict", "tolerant", "learning"] = "learning"
    interaction_style: Literal["formal", "casual", "adaptive"] = "adaptive"

    # Evolution metadata
    fitness_score: float = 0.0
    mutation_history: List[Dict[str, Any]] = Field(default_factory=list)
    performance_history: List[FitnessMetrics] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_mutation: Optional[datetime] = None

    def mutate(self, mutation_rate: float = 0.1, mutation_strength: float = 0.2) -> "AgentGenome":
        """Create a mutated version of this genome"""
        new_genome = self.model_copy()
        new_genome.genome_id = str(uuid4())
        new_genome.generation += 1
        new_genome.parent_genomes = [self.genome_id]
        new_genome.last_mutation = datetime.now()

        mutations_applied = []

        # Mutate numerical parameters
        if random.random() < mutation_rate:
            new_genome.temperature = self._mutate_float(self.temperature, 0.0, 2.0, mutation_strength)
            mutations_applied.append({"type": "temperature", "value": new_genome.temperature})

        if random.random() < mutation_rate:
            new_genome.max_tokens = self._mutate_int(self.max_tokens, 100, 4000, mutation_strength)
            mutations_applied.append({"type": "max_tokens", "value": new_genome.max_tokens})

        if random.random() < mutation_rate:
            new_genome.reasoning_depth = self._mutate_int(self.reasoning_depth, 1, 10, mutation_strength)
            mutations_applied.append({"type": "reasoning_depth", "value": new_genome.reasoning_depth})

        # Mutate personality traits
        personality_traits = ["creativity", "analytical_thinking", "empathy", "assertiveness", "curiosity", "patience"]

        for trait in personality_traits:
            if random.random() < mutation_rate:
                current_value = getattr(new_genome, trait)
                new_value = self._mutate_float(current_value, 0.0, 1.0, mutation_strength)
                setattr(new_genome, trait, new_value)
                mutations_applied.append({"type": trait, "value": new_value})

        # Mutate instructions (sophisticated text mutation)
        if random.random() < mutation_rate * 0.5:  # Lower probability for instruction mutation
            new_genome.instructions = self._mutate_instructions(self.instructions)
            mutations_applied.append({"type": "instructions", "change": "text_mutation"})

        # Record mutations
        new_genome.mutation_history.append(
            {
                "generation": new_genome.generation,
                "mutations": mutations_applied,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return new_genome

    def crossover(self, other: "AgentGenome", crossover_rate: float = 0.5) -> "AgentGenome":
        """Create offspring through crossover with another genome"""
        child_genome = AgentGenome()
        child_genome.genome_id = str(uuid4())
        child_genome.generation = max(self.generation, other.generation) + 1
        child_genome.parent_genomes = [self.genome_id, other.genome_id]

        # Numerical parameter crossover
        child_genome.temperature = self.temperature if random.random() < crossover_rate else other.temperature
        child_genome.max_tokens = self.max_tokens if random.random() < crossover_rate else other.max_tokens
        child_genome.reasoning_depth = (
            self.reasoning_depth if random.random() < crossover_rate else other.reasoning_depth
        )

        # Personality trait crossover (blend)
        child_genome.creativity = self._blend_trait(self.creativity, other.creativity)
        child_genome.analytical_thinking = self._blend_trait(self.analytical_thinking, other.analytical_thinking)
        child_genome.empathy = self._blend_trait(self.empathy, other.empathy)
        child_genome.assertiveness = self._blend_trait(self.assertiveness, other.assertiveness)
        child_genome.curiosity = self._blend_trait(self.curiosity, other.curiosity)
        child_genome.patience = self._blend_trait(self.patience, other.patience)

        # Instruction crossover (combine best parts)
        child_genome.instructions = self._crossover_instructions(self.instructions, other.instructions)

        # Tool preference combination
        child_genome.preferred_tools = list(set(self.preferred_tools + other.preferred_tools))

        return child_genome

    def _mutate_float(self, value: float, min_val: float, max_val: float, strength: float) -> float:
        """Mutate a float value within bounds"""
        mutation = random.gauss(0, strength)
        new_value = value + mutation
        return max(min_val, min(max_val, new_value))

    def _mutate_int(self, value: int, min_val: int, max_val: int, strength: float) -> int:
        """Mutate an integer value within bounds"""
        mutation = int(random.gauss(0, strength * (max_val - min_val) / 4))
        new_value = value + mutation
        return max(min_val, min(max_val, new_value))

    def _mutate_instructions(self, instructions: str) -> str:
        """Sophisticated instruction mutation"""
        # This would use an AI model to create meaningful variations
        # For now, implement simple text variations

        if not instructions:
            return instructions

        mutation_strategies = [self._add_emphasis, self._modify_tone, self._add_specificity, self._adjust_formality]

        strategy = random.choice(mutation_strategies)
        return strategy(instructions)

    def _add_emphasis(self, text: str) -> str:
        """Add emphasis to instructions"""
        emphasis_words = ["definitely", "carefully", "thoroughly", "precisely"]
        word = random.choice(emphasis_words)
        return f"{text} Please {word} consider all aspects."

    def _modify_tone(self, text: str) -> str:
        """Modify the tone of instructions"""
        if "please" not in text.lower():
            return f"Please {text.lower()}"
        return text.replace("Please", "Kindly")

    def _add_specificity(self, text: str) -> str:
        """Add more specificity to instructions"""
        specificity_additions = [
            " Focus on accuracy and detail.",
            " Consider multiple perspectives.",
            " Provide clear reasoning.",
            " Be comprehensive in your analysis.",
        ]
        addition = random.choice(specificity_additions)
        return text + addition

    def _adjust_formality(self, text: str) -> str:
        """Adjust formality level"""
        formal_replacements = {" you ": " one ", "can't": "cannot", "won't": "will not", "don't": "do not"}

        result = text
        for informal, formal in formal_replacements.items():
            if informal in text:
                result = result.replace(informal, formal)
                break

        return result

    def _crossover_instructions(self, instr1: str, instr2: str) -> str:
        """Combine instructions from two parents"""
        if not instr1:
            return instr2
        if not instr2:
            return instr1

        # Simple combination strategy
        sentences1 = instr1.split(".")
        sentences2 = instr2.split(".")

        combined = []
        for i in range(max(len(sentences1), len(sentences2))):
            if i < len(sentences1) and i < len(sentences2):
                # Choose randomly between parents
                chosen = sentences1[i] if random.random() < 0.5 else sentences2[i]
                combined.append(chosen)
            elif i < len(sentences1):
                combined.append(sentences1[i])
            elif i < len(sentences2):
                combined.append(sentences2[i])

        return ".".join(combined)

    def _blend_trait(self, trait1: float, trait2: float, alpha: float = None) -> float:
        """Blend two trait values"""
        if alpha is None:
            alpha = random.random()

        blended = alpha * trait1 + (1 - alpha) * trait2
        return max(0.0, min(1.0, blended))


class EvolutionaryMixin:
    """Mixin class to add evolutionary capabilities to agents"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.genome: Optional[AgentGenome] = None
        self.evolution_enabled: bool = kwargs.get("evolution_enabled", False)
        self.fitness_evaluator: Optional[FitnessEvaluator] = None
        self.performance_tracker: Optional[PerformanceTracker] = None
        self.auto_evolution: bool = kwargs.get("auto_evolution", False)
        self.evolution_threshold: float = kwargs.get("evolution_threshold", 0.1)
        self.generation: int = 0

        if self.evolution_enabled:
            self._initialize_evolution()

    def _initialize_evolution(self):
        """Initialize evolutionary capabilities"""
        self.genome = AgentGenome(
            instructions=getattr(self, "instructions", ""),
            temperature=getattr(self.model, "temperature", 0.7) if hasattr(self, "model") else 0.7,
            max_tokens=getattr(self.model, "max_tokens", 1000) if hasattr(self, "model") else 1000,
        )
        self.performance_tracker = PerformanceTracker()
        self.fitness_evaluator = FitnessEvaluator()

    def evolve(self, mutation_rate: float = 0.1, mutation_strength: float = 0.2) -> "Agent":
        """Evolve this agent based on performance"""
        if not self.evolution_enabled or not self.genome:
            raise ValueError("Evolution not enabled for this agent")

        # Create mutated genome
        new_genome = self.genome.mutate(mutation_rate, mutation_strength)

        # Create new agent with evolved genome
        evolved_agent = self._create_evolved_agent(new_genome)

        return evolved_agent

    def crossover_with(self, other_agent: "Agent") -> "Agent":
        """Create offspring through crossover with another agent"""
        if not self.genome or not hasattr(other_agent, "genome") or not other_agent.genome:
            raise ValueError("Both agents must have genomes for crossover")

        # Create child genome
        child_genome = self.genome.crossover(other_agent.genome)

        # Create new agent with child genome
        child_agent = self._create_evolved_agent(child_genome)

        return child_agent

    def evaluate_fitness(self, interactions: List[Dict[str, Any]]) -> FitnessMetrics:
        """Evaluate agent fitness based on recent interactions"""
        if not self.fitness_evaluator:
            self.fitness_evaluator = FitnessEvaluator()

        fitness = self.fitness_evaluator.evaluate(interactions)

        if self.genome:
            self.genome.fitness_score = fitness.overall_fitness
            self.genome.performance_history.append(fitness)

        return fitness

    def should_evolve(self) -> bool:
        """Determine if agent should evolve based on performance"""
        if not self.auto_evolution or not self.genome:
            return False

        # Check if performance has plateaued or declined
        recent_fitness = self.genome.performance_history[-10:]  # Last 10 evaluations
        if len(recent_fitness) < 5:
            return False

        # Calculate performance trend
        fitness_scores = [f.overall_fitness for f in recent_fitness]
        if len(fitness_scores) >= 5:
            recent_avg = sum(fitness_scores[-3:]) / 3
            older_avg = sum(fitness_scores[-5:-2]) / 3

            # Evolve if performance has declined or plateaued
            if recent_avg < older_avg - self.evolution_threshold:
                return True

        return False

    def auto_evolve(self) -> Optional["Agent"]:
        """Automatically evolve if conditions are met"""
        if self.should_evolve():
            return self.evolve()
        return None

    def _create_evolved_agent(self, genome: AgentGenome) -> "Agent":
        """Create a new agent from evolved genome"""
        # This would need to be implemented by the specific Agent class
        # For now, return a conceptual evolved agent
        evolved_agent_config = {
            "name": f"{self.name}_gen_{genome.generation}",
            "instructions": genome.instructions,
            "evolution_enabled": True,
            "genome": genome,
        }

        if hasattr(self, "model"):
            # Update model parameters
            evolved_model = self.model.model_copy()
            evolved_model.temperature = genome.temperature
            evolved_model.max_tokens = genome.max_tokens
            evolved_agent_config["model"] = evolved_model

        # This would create a new instance of the same agent class
        # In practice, this would use the agent's class constructor
        return type(self)(**evolved_agent_config)


class FitnessEvaluator:
    """Evaluates agent fitness based on performance metrics"""

    def __init__(self):
        self.evaluation_window = timedelta(hours=24)
        self.weights = {
            "response_quality": 0.3,
            "task_completion": 0.25,
            "user_satisfaction": 0.2,
            "efficiency": 0.15,
            "consistency": 0.1,
        }

    def evaluate(self, interactions: List[Dict[str, Any]]) -> FitnessMetrics:
        """Evaluate fitness from interaction data"""
        if not interactions:
            return FitnessMetrics()

        # Calculate metrics from interactions
        accuracy_score = self._calculate_accuracy(interactions)
        response_time = self._calculate_avg_response_time(interactions)
        user_satisfaction = self._calculate_user_satisfaction(interactions)
        completion_rate = self._calculate_completion_rate(interactions)
        error_rate = self._calculate_error_rate(interactions)
        efficiency_score = self._calculate_efficiency(interactions)
        adaptability_score = self._calculate_adaptability(interactions)
        consistency_score = self._calculate_consistency(interactions)

        return FitnessMetrics(
            accuracy_score=accuracy_score,
            response_time=response_time,
            user_satisfaction=user_satisfaction,
            task_completion_rate=completion_rate,
            error_rate=error_rate,
            efficiency_score=efficiency_score,
            adaptability_score=adaptability_score,
            consistency_score=consistency_score,
        )

    def _calculate_accuracy(self, interactions: List[Dict[str, Any]]) -> float:
        """Calculate response accuracy score"""
        accurate_responses = sum(1 for i in interactions if i.get("feedback", {}).get("accuracy", 0) >= 0.7)
        return accurate_responses / len(interactions) if interactions else 0.0

    def _calculate_avg_response_time(self, interactions: List[Dict[str, Any]]) -> float:
        """Calculate average response time in seconds"""
        response_times = [i.get("response_time", 0) for i in interactions if "response_time" in i]
        return sum(response_times) / len(response_times) if response_times else 0.0

    def _calculate_user_satisfaction(self, interactions: List[Dict[str, Any]]) -> float:
        """Calculate user satisfaction score"""
        satisfaction_scores = [i.get("feedback", {}).get("satisfaction", 0.5) for i in interactions]
        return sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0.5

    def _calculate_completion_rate(self, interactions: List[Dict[str, Any]]) -> float:
        """Calculate task completion rate"""
        completed_tasks = sum(1 for i in interactions if i.get("task_completed", False))
        return completed_tasks / len(interactions) if interactions else 0.0

    def _calculate_error_rate(self, interactions: List[Dict[str, Any]]) -> float:
        """Calculate error rate"""
        error_count = sum(1 for i in interactions if i.get("error_occurred", False))
        return error_count / len(interactions) if interactions else 0.0

    def _calculate_efficiency(self, interactions: List[Dict[str, Any]]) -> float:
        """Calculate efficiency score (task completion / time)"""
        efficiency_scores = []
        for interaction in interactions:
            if interaction.get("task_completed") and interaction.get("response_time"):
                efficiency = 1.0 / interaction["response_time"]  # Simple efficiency metric
                efficiency_scores.append(min(1.0, efficiency))

        return sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0.5

    def _calculate_adaptability(self, interactions: List[Dict[str, Any]]) -> float:
        """Calculate adaptability score based on handling diverse tasks"""
        task_types = set(i.get("task_type", "unknown") for i in interactions)
        successful_adaptations = len(
            [i for i in interactions if i.get("task_completed") and i.get("task_type") != "routine"]
        )

        adaptability = (successful_adaptations / len(interactions)) if interactions else 0.0
        return min(1.0, adaptability + (len(task_types) / 10.0))  # Bonus for variety

    def _calculate_consistency(self, interactions: List[Dict[str, Any]]) -> float:
        """Calculate consistency score"""
        quality_scores = [i.get("feedback", {}).get("accuracy", 0.5) for i in interactions]

        if len(quality_scores) < 2:
            return 1.0

        # Calculate standard deviation (lower is more consistent)
        mean_quality = sum(quality_scores) / len(quality_scores)
        variance = sum((x - mean_quality) ** 2 for x in quality_scores) / len(quality_scores)
        std_dev = variance**0.5

        # Convert to consistency score (0-1, higher is better)
        consistency = max(0.0, 1.0 - (std_dev * 2))  # Scale standard deviation
        return consistency


class PerformanceTracker:
    """Tracks agent performance over time for evolution decisions"""

    def __init__(self):
        self.performance_history: List[FitnessMetrics] = []
        self.interaction_log: List[Dict[str, Any]] = []
        self.tracking_window = timedelta(days=7)

    def record_interaction(self, interaction_data: Dict[str, Any]):
        """Record an interaction for performance tracking"""
        interaction_data["timestamp"] = datetime.now()
        self.interaction_log.append(interaction_data)

        # Cleanup old interactions
        cutoff_time = datetime.now() - self.tracking_window
        self.interaction_log = [i for i in self.interaction_log if i["timestamp"] > cutoff_time]

    def record_fitness(self, fitness: FitnessMetrics):
        """Record fitness evaluation"""
        self.performance_history.append(fitness)

        # Keep only recent history
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]

    def get_recent_performance(self, days: int = 7) -> List[FitnessMetrics]:
        """Get recent performance metrics"""
        cutoff_time = datetime.now() - timedelta(days=days)
        # Note: This would need timestamp in FitnessMetrics for proper filtering
        return self.performance_history[-50:]  # Simplified for now

    def analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends for evolution decisions"""
        if len(self.performance_history) < 5:
            return {"trend": "insufficient_data"}

        recent_scores = [f.overall_fitness for f in self.performance_history[-10:]]
        older_scores = [f.overall_fitness for f in self.performance_history[-20:-10]]

        if not older_scores:
            return {"trend": "insufficient_data"}

        recent_avg = sum(recent_scores) / len(recent_scores)
        older_avg = sum(older_scores) / len(older_scores)

        trend_direction = "improving" if recent_avg > older_avg else "declining"
        trend_magnitude = abs(recent_avg - older_avg)

        return {
            "trend": trend_direction,
            "magnitude": trend_magnitude,
            "recent_avg": recent_avg,
            "older_avg": older_avg,
            "stability": self._calculate_stability(recent_scores),
        }

    def _calculate_stability(self, scores: List[float]) -> float:
        """Calculate performance stability"""
        if len(scores) < 2:
            return 1.0

        mean_score = sum(scores) / len(scores)
        variance = sum((x - mean_score) ** 2 for x in scores) / len(scores)
        stability = max(0.0, 1.0 - variance)

        return stability
