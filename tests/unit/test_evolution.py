"""Regression tests for evolutionary agent behavior."""

from datetime import datetime, timedelta

from buddy.agent.agent import Agent
from buddy.agent.evolution import AgentGenome, EvolutionaryMixin, FitnessEvaluator, FitnessMetrics, PerformanceTracker


class EvolvedAgent(EvolutionaryMixin, Agent):
    pass


def test_mixin_initializes_with_agent_and_preserves_child_genome():
    agent = EvolvedAgent(name="demo", instructions="be useful", add_context=True, evolution_enabled=True)

    child_genome = agent.genome.mutate(mutation_rate=0, mutation_strength=0)
    child = agent._create_evolved_agent(child_genome)

    assert child.genome is child_genome
    assert child.genome.generation == 1
    assert child.add_context is True
    assert child.name == "demo_gen_1"


def test_mutation_does_not_share_history():
    parent = AgentGenome(mutation_history=[{"generation": 0}])

    child = parent.mutate(mutation_rate=0, mutation_strength=0)
    child.mutation_history.append({"generation": 1})

    assert len(parent.mutation_history) == 1
    assert len(child.mutation_history) == 3


def test_errors_reduce_fitness():
    no_errors = FitnessMetrics(accuracy_score=1, error_rate=0).overall_fitness
    all_errors = FitnessMetrics(accuracy_score=1, error_rate=1).overall_fitness

    assert no_errors > all_errors


def test_crossover_preserves_all_configuration_genes():
    first = AgentGenome(
        max_loops=4,
        tool_usage_strategy="aggressive",
        response_style="concise",
        error_handling_strategy="strict",
        interaction_style="formal",
    )
    second = AgentGenome(
        max_loops=2,
        tool_usage_strategy="conservative",
        response_style="detailed",
        error_handling_strategy="tolerant",
        interaction_style="casual",
    )

    child = first.crossover(second, crossover_rate=1)

    assert child.max_loops == first.max_loops
    assert child.tool_usage_strategy == first.tool_usage_strategy
    assert child.response_style == first.response_style
    assert child.error_handling_strategy == first.error_handling_strategy
    assert child.interaction_style == first.interaction_style


def test_fitness_evaluation_records_tracker_data_without_mutating_input():
    agent = EvolvedAgent(evolution_enabled=True)
    interaction = {"response_time": 1, "task_completed": True}

    agent.evaluate_fitness([interaction])

    assert "timestamp" not in interaction
    assert len(agent.performance_tracker.interaction_log) == 1
    assert len(agent.performance_tracker.performance_history) == 1


def test_performance_tracker_filters_by_age():
    tracker = PerformanceTracker()
    tracker.record_fitness(FitnessMetrics(recorded_at=datetime.now() - timedelta(days=8)))
    tracker.record_fitness(FitnessMetrics(recorded_at=datetime.now()))

    assert len(tracker.get_recent_performance(days=7)) == 1


def test_should_evolve_on_plateau():
    agent = EvolvedAgent(evolution_enabled=True, auto_evolution=True)
    agent.genome.performance_history.extend(FitnessMetrics() for _ in range(6))

    assert agent.should_evolve() is True


def test_empty_evaluator_returns_zero_fitness():
    assert FitnessEvaluator().evaluate([]).overall_fitness == 0.0
