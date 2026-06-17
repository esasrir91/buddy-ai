# Agent Evolution

The evolution module (`buddy.agent.evolution`) is an **experimental optimization
layer** that treats an agent's configuration as a *genome* and applies
genetic-algorithm operators — mutation, crossover, and fitness selection — to
search for better-performing variants.

!!! warning "Experimental"
    Evolution is an optimization scaffold, not a turnkey self-improvement system.
    It mutates configuration (instructions, temperature, personality traits) and
    scores variants from interaction data **you** supply. It does not retrain the
    underlying model. Treat results as candidate configurations to validate.

Availability is gated; check before using:

```python
from buddy import check_feature
assert check_feature("evolution")

from buddy import AgentGenome, EvolutionStrategy, FitnessEvaluator
from buddy.agent.evolution import EvolutionaryMixin
```

## The genome

`AgentGenome` is a Pydantic model encoding the tunable surface of an agent:

| Field group | Fields |
|-------------|--------|
| Core | `instructions`, `temperature`, `max_tokens`, `max_loops`, `reasoning_depth` |
| Personality (0.0–1.0) | `creativity`, `analytical_thinking`, `empathy`, `assertiveness`, `curiosity`, `patience` |
| Tools | `preferred_tools`, `tool_usage_strategy` (`conservative`/`balanced`/`aggressive`) |
| Style | `response_style`, `error_handling_strategy`, `interaction_style` |
| Lineage | `genome_id`, `generation`, `parent_genomes`, `fitness_score`, `mutation_history` |

```python
from buddy import AgentGenome

genome = AgentGenome(instructions="Be concise.", temperature=0.7)

# Produce a mutated child genome
child = genome.mutate(mutation_rate=0.2, mutation_strength=0.3)
print(child.generation, child.parent_genomes)

# Recombine two genomes
other = AgentGenome(instructions="Be thorough.", temperature=1.0)
offspring = genome.crossover(other, crossover_rate=0.5)
```

`mutate()` perturbs numeric and personality genes (and occasionally rewrites
instructions), while `crossover()` blends parents and combines their preferred
tools.

## Fitness evaluation

`FitnessEvaluator` scores a genome from a list of interaction dictionaries. Each
interaction is a plain dict with optional keys such as `response_time`,
`task_completed`, `error_occurred`, `task_type`, and a `feedback` sub-dict with
`accuracy` and `satisfaction`.

```python
from buddy import FitnessEvaluator

interactions = [
    {"response_time": 1.2, "task_completed": True,
     "feedback": {"accuracy": 0.9, "satisfaction": 0.8}},
    {"response_time": 3.0, "task_completed": False, "error_occurred": True,
     "feedback": {"accuracy": 0.4, "satisfaction": 0.3}},
]

metrics = FitnessEvaluator().evaluate(interactions)
print(metrics.overall_fitness)   # weighted score in [0.0, 1.0]
```

`FitnessMetrics.overall_fitness` combines accuracy, response time, satisfaction,
completion rate, error rate, efficiency, adaptability, and consistency into a
single normalized score.

## Evolution strategies

`EvolutionStrategy` enumerates the search families the layer is designed around:

| Member | Value |
|--------|-------|
| `EvolutionStrategy.GENETIC` | `"genetic"` |
| `EvolutionStrategy.DIFFERENTIAL` | `"differential"` |
| `EvolutionStrategy.PARTICLE_SWARM` | `"particle_swarm"` |
| `EvolutionStrategy.BAYESIAN` | `"bayesian"` |

## Adding evolution to an agent

`EvolutionaryMixin` adds `evolve()`, `crossover_with()`, `evaluate_fitness()`,
`should_evolve()`, and `auto_evolve()` to an agent class. Compose it with
`Agent` so the mixin can consume its extra keyword arguments
(`evolution_enabled`, `auto_evolution`, `evolution_threshold`):

```python
from buddy import Agent
from buddy.agent.evolution import EvolutionaryMixin

class EvolvingAgent(EvolutionaryMixin, Agent):
    pass

agent = EvolvingAgent(evolution_enabled=True, auto_evolution=True)
fitness = agent.evaluate_fitness(interactions)
if agent.should_evolve():
    evolved = agent.evolve()   # returns a new agent built from a mutated genome
```

!!! note
    `evolve()` raises `ValueError` unless `evolution_enabled=True`. Fitness
    history needs at least five evaluations before `should_evolve()` will report
    a decline. Always benchmark an evolved agent before promoting it.
