"""
Sutra-Decomposed Competency scoring for Buddy agents and teams.

This module implements a balance-aware competency score for an AI agent (or
team) operating across multiple competency domains, together with a
deficit-driven controller that turns the score into concrete, prioritized
learning/retraining recommendations.

The score decomposes an agent's integrated competency into three components:

* Vertical  (V) : per-domain depth        ``V = sum_i a_i^2``
* Crosswise (C) : cross-domain interaction ``C = 2 * sum_{i<j} w_ij a_i a_j``
* Deficit   (D) : gap from a target base   ``delta_i = B - a_i``

where ``a_i`` is the competency of domain ``i`` in ``[0, B]``, ``B`` is the
target/base competency, and ``w_ij in [0, 1]`` are optional domain-dependency
weights. With ``w_ij = 1`` for all pairs, ``V + C = (sum_i a_i)^2``; supplying a
non-trivial dependency graph makes the crosswise term a genuine, non-separable
interaction signal that rewards balanced, connected competence.

The per-domain ``priority`` combines the deficit with a crosswise-centrality
factor so the highest-leverage gaps are addressed first. A
:class:`DeficitDrivenController` consumes those priorities to recommend (or
trigger) knowledge-acquisition / retraining actions, forming a closed loop.
"""

from __future__ import annotations

import threading
from dataclasses import asdict, dataclass, field
from os import getenv
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from buddy.utils.log import logger

if TYPE_CHECKING:
    from rich.console import Console

    from buddy.eval.accuracy import AccuracyEval
    from buddy.eval.reliability import ReliabilityEval
    from buddy.train.jobs import TrainingJob, TrainingJobManager

# Dependency weights may be supplied as a {(domain_a, domain_b): weight} mapping.
DependencyGraph = Dict[Tuple[str, str], float]


@dataclass
class CompetencyDomain:
    """A single competency domain and the agent's mastery of it."""

    name: str
    # Mastery of this domain, expressed on the same scale as ``base`` (0..base).
    competency: float
    # Optional human-readable note on where the competency value came from.
    source: Optional[str] = None


@dataclass
class CompetencyResult:
    """Holds the computed Sutra-Decomposed Competency score and its breakdown."""

    domains: List[CompetencyDomain] = field(default_factory=list)
    base: float = 10.0
    lambda_centrality: float = 1.0
    # Dependency weights keyed by an order-independent ``(name_a, name_b)`` pair.
    dependency: DependencyGraph = field(default_factory=dict)

    # Computed aggregate components.
    vertical: float = field(init=False, default=0.0)
    crosswise: float = field(init=False, default=0.0)
    integrated: float = field(init=False, default=0.0)
    integrated_max: float = field(init=False, default=0.0)
    index: float = field(init=False, default=0.0)
    total_deficit: float = field(init=False, default=0.0)

    # Computed per-domain vectors (aligned with ``domains`` order).
    deficits: Dict[str, float] = field(init=False, default_factory=dict)
    centrality: Dict[str, float] = field(init=False, default_factory=dict)
    priority: Dict[str, float] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self.compute()

    def _weight(self, a: str, b: str) -> float:
        """Return the (symmetric) dependency weight for a pair, defaulting to 1.0."""
        if not self.dependency:
            return 1.0
        return self.dependency.get((a, b), self.dependency.get((b, a), 1.0))

    def compute(self) -> None:
        names = [d.name for d in self.domains]
        values = [max(0.0, min(self.base, float(d.competency))) for d in self.domains]
        n = len(values)

        if n == 0 or self.base <= 0:
            return

        # Vertical: per-domain depth.
        self.vertical = sum(v * v for v in values)

        # Crosswise: dependency-weighted pairwise interaction.
        crosswise = 0.0
        weight_sum = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                w = self._weight(names[i], names[j])
                crosswise += w * values[i] * values[j]
                weight_sum += w
        self.crosswise = 2.0 * crosswise

        self.integrated = self.vertical + self.crosswise
        # Max integrated value when every domain reaches ``base``.
        self.integrated_max = (self.base**2) * (n + 2.0 * weight_sum)
        self.index = self.integrated / self.integrated_max if self.integrated_max > 0 else 0.0

        # Per-domain deficit (Nikhilam: gap from base).
        self.deficits = {names[i]: self.base - values[i] for i in range(n)}
        self.total_deficit = sum(self.deficits.values())

        # Crosswise centrality: how connected (and competent) each domain is.
        centrality: Dict[str, float] = {}
        for i in range(n):
            acc = 0.0
            for j in range(n):
                if i == j:
                    continue
                acc += self._weight(names[i], names[j]) * values[j]
            centrality[names[i]] = values[i] * acc
        self.centrality = centrality

        max_centrality = max(centrality.values()) if centrality else 0.0

        # Priority: deficit amplified by normalized centrality.
        priority: Dict[str, float] = {}
        for i in range(n):
            norm_c = (centrality[names[i]] / max_centrality) if max_centrality > 0 else 0.0
            priority[names[i]] = self.deficits[names[i]] * (1.0 + self.lambda_centrality * norm_c)
        self.priority = priority

    def ranked_priorities(self) -> List[Tuple[str, float]]:
        """Return ``(domain, priority)`` pairs sorted by descending priority."""
        return sorted(self.priority.items(), key=lambda kv: kv[1], reverse=True)

    def weakest_domain(self) -> Optional[str]:
        ranked = self.ranked_priorities()
        return ranked[0][0] if ranked else None

    def print_summary(self, console: Optional["Console"] = None) -> None:
        from rich.box import ROUNDED
        from rich.console import Console
        from rich.table import Table

        if console is None:
            console = Console()

        summary_table = Table(
            box=ROUNDED,
            border_style="blue",
            show_header=False,
            title="[ Competency Summary ]",
            title_style="bold sky_blue1",
            title_justify="center",
        )
        summary_table.add_row("Domains", f"{len(self.domains)}")
        summary_table.add_row("Base (target)", f"{self.base:.2f}")
        summary_table.add_row("Vertical (V)", f"{self.vertical:.2f}")
        summary_table.add_row("Crosswise (C)", f"{self.crosswise:.2f}")
        summary_table.add_row("Integrated (U)", f"{self.integrated:.2f}")
        summary_table.add_row("Competency Index", f"{self.index:.2%}")
        summary_table.add_row("Total Deficit", f"{self.total_deficit:.2f}")
        weakest = self.weakest_domain()
        if weakest is not None:
            summary_table.add_row("Highest-priority gap", weakest)
        console.print(summary_table)

    def print_results(self, console: Optional["Console"] = None) -> None:
        from rich.box import ROUNDED
        from rich.console import Console
        from rich.table import Table

        if console is None:
            console = Console()

        results_table = Table(
            box=ROUNDED,
            border_style="blue",
            title="[ Competency by Domain ]",
            title_style="bold sky_blue1",
            title_justify="center",
        )
        results_table.add_column("Domain", style="bold")
        results_table.add_column("Competency", justify="right")
        results_table.add_column("Deficit", justify="right")
        results_table.add_column("Centrality", justify="right")
        results_table.add_column("Priority", justify="right")

        for name, _priority in self.ranked_priorities():
            comp = next((d.competency for d in self.domains if d.name == name), 0.0)
            results_table.add_row(
                name,
                f"{comp:.2f}/{self.base:.0f}",
                f"{self.deficits.get(name, 0.0):.2f}",
                f"{self.centrality.get(name, 0.0):.2f}",
                f"{self.priority.get(name, 0.0):.2f}",
            )
        console.print(results_table)


@dataclass
class CompetencyAction:
    """A recommended (or executed) learning action for one domain."""

    domain: str
    priority: float
    deficit: float
    action: str
    reason: str


class DeficitDrivenController:
    """Turn a :class:`CompetencyResult` into prioritized learning actions.

    This is the closed-loop controller: given a competency result, it selects the
    domains whose deficit exceeds a threshold and emits ranked recommendations.
    A caller (e.g. the training job manager) can execute these to drive the agent
    toward balanced mastery at minimum cost.
    """

    def __init__(
        self,
        *,
        deficit_threshold: float = 0.0,
        max_actions: Optional[int] = None,
        action: str = "schedule_learning",
    ) -> None:
        self.deficit_threshold = deficit_threshold
        self.max_actions = max_actions
        self.action = action

    def recommend(self, result: CompetencyResult) -> List[CompetencyAction]:
        actions: List[CompetencyAction] = []
        for name, priority in result.ranked_priorities():
            deficit = result.deficits.get(name, 0.0)
            if deficit <= self.deficit_threshold:
                continue
            actions.append(
                CompetencyAction(
                    domain=name,
                    priority=priority,
                    deficit=deficit,
                    action=self.action,
                    reason=(
                        f"Domain '{name}' is {deficit:.2f} below the target base "
                        f"(priority {priority:.2f}); prioritized for learning."
                    ),
                )
            )
            if self.max_actions is not None and len(actions) >= self.max_actions:
                break
        return actions


def _coerce_domains(
    domains: Union[List[CompetencyDomain], Dict[str, float]],
) -> List[CompetencyDomain]:
    if isinstance(domains, dict):
        return [CompetencyDomain(name=k, competency=float(v)) for k, v in domains.items()]
    coerced: List[CompetencyDomain] = []
    for d in domains:
        if isinstance(d, CompetencyDomain):
            coerced.append(d)
        else:
            raise TypeError(f"Unsupported domain entry: {d!r}")
    return coerced


@dataclass
class CompetencyEval:
    """Interface to score the multi-domain competency of an Agent or Team.

    Example:
        >>> from buddy.eval.competency import CompetencyEval
        >>> ev = CompetencyEval(
        ...     domains={"reasoning": 7, "memory": 6},
        ...     base=9,
        ...     dependency={("reasoning", "memory"): 1.0},
        ... )
        >>> result = ev.run()
        >>> result.index  # doctest: +SKIP
        0.5216...
    """

    # Domains may be a {name: competency} mapping or a list of CompetencyDomain.
    domains: Union[List[CompetencyDomain], Dict[str, float]]
    # Target/base competency that defines "mastery".
    base: float = 10.0
    # Optional dependency weights keyed by ``(domain_a, domain_b)``.
    dependency: DependencyGraph = field(default_factory=dict)
    # Trade-off between raw deficit and crosswise leverage in the priority.
    lambda_centrality: float = 1.0

    # Identity / metadata.
    name: Optional[str] = None
    eval_id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: Optional[str] = None
    team_id: Optional[str] = None
    model_id: Optional[str] = None
    model_provider: Optional[str] = None

    result: Optional[CompetencyResult] = None

    # Output controls.
    print_summary: bool = False
    print_results: bool = False
    file_path_to_save_results: Optional[str] = None
    monitoring: bool = getenv("BUDDY_MONITOR", "true").lower() == "true"

    def run(
        self,
        *,
        print_summary: bool = True,
        print_results: bool = True,
    ) -> CompetencyResult:
        domains = _coerce_domains(self.domains)
        self.result = CompetencyResult(
            domains=domains,
            base=self.base,
            lambda_centrality=self.lambda_centrality,
            dependency=dict(self.dependency),
        )

        if self.file_path_to_save_results is not None:
            from buddy.eval.utils import store_result_in_file

            store_result_in_file(
                file_path=self.file_path_to_save_results,
                name=self.name,
                eval_id=self.eval_id,
                result=self.result,  # type: ignore[arg-type]
            )

        if self.print_results or print_results:
            self.result.print_results()
        if self.print_summary or print_summary:
            self.result.print_summary()

        if self.monitoring:
            self._log_run()

        return self.result

    def recommend_actions(
        self,
        *,
        deficit_threshold: float = 0.0,
        max_actions: Optional[int] = None,
    ) -> List[CompetencyAction]:
        """Run (if needed) and return prioritized learning recommendations."""
        if self.result is None:
            self.run(print_summary=False, print_results=False)
        controller = DeficitDrivenController(
            deficit_threshold=deficit_threshold,
            max_actions=max_actions,
        )
        return controller.recommend(self.result)  # type: ignore[arg-type]

    def _log_run(self) -> None:
        if self.result is None:
            return
        try:
            from buddy.api.schemas.evals import EvalType
            from buddy.eval.utils import log_eval_run

            # COMPETENCY may not exist on older API schemas; fall back gracefully.
            eval_type = getattr(EvalType, "COMPETENCY", None)
            if eval_type is None:
                return
            log_eval_run(
                run_id=self.eval_id,
                run_data=asdict(self.result),
                eval_type=eval_type,
                agent_id=self.agent_id,
                team_id=self.team_id,
                model_id=self.model_id,
                model_provider=self.model_provider,
                name=self.name,
                evaluated_entity_name=self.name,
            )
        except Exception as e:  # pragma: no cover - logging must never break scoring
            logger.debug(f"Could not log competency eval run: {e}")


# ----------------------------------------------------------------------------
# Autonomous competency loop
# ----------------------------------------------------------------------------

# A signal is any callable returning the agent's *current* competency in a
# domain, on the same scale as ``base``. It is re-invoked every cycle, so the
# loop always scores against fresh, live measurements rather than fixed numbers.
CompetencySignal = Callable[[], float]


@dataclass
class DomainSpec:
    """Declares a competency domain for the autonomous loop.

    Attributes:
        name: Domain identifier.
        signal: Callable returning the current competency (0..base). Re-evaluated
            every cycle so scores update automatically.
        data_path: Optional path to training data used to close the gap for this
            domain when the loop decides to (re)train it.
    """

    name: str
    signal: CompetencySignal
    data_path: Optional[str] = None


def accuracy_signal(accuracy_eval: "AccuracyEval", base: float = 10.0) -> CompetencySignal:
    """Build a signal that scores a domain from a live AccuracyEval (1-10 -> 0..base)."""

    def _signal() -> float:
        result = accuracy_eval.run(print_summary=False, print_results=False)
        if result is None or not result.results:
            return 0.0
        return (result.avg_score / 10.0) * base

    return _signal


def reliability_signal(reliability_eval: "ReliabilityEval", base: float = 10.0) -> CompetencySignal:
    """Build a signal that scores a domain from a live ReliabilityEval (PASSED -> base)."""

    def _signal() -> float:
        result = reliability_eval.run(print_results=False)
        return base if result is not None and result.eval_status == "PASSED" else 0.0

    return _signal


class AutonomousCompetencyLoop:
    """A self-running loop: measure -> score -> find weakest gap -> train.

    Once configured with :class:`DomainSpec` entries (each providing a live signal
    and, optionally, training data), the loop runs on a background thread. Every
    cycle it re-reads the signals, recomputes the competency score, and \u2014 when the
    overall index is below ``target_index`` \u2014 automatically enqueues training jobs
    for the highest-priority deficit domains via the training job manager.

    Scores are never hand-set: they come from the signals each cycle, which is what
    makes the loop autonomous.
    """

    def __init__(
        self,
        domains: List[DomainSpec],
        *,
        base: float = 10.0,
        dependency: Optional[DependencyGraph] = None,
        lambda_centrality: float = 1.0,
        deficit_threshold: float = 0.5,
        target_index: float = 1.0,
        interval_seconds: float = 3600.0,
        max_jobs_per_cycle: Optional[int] = 1,
        auto_train: bool = True,
        force_retrain: bool = True,
        base_model: str = "distilgpt2",
        name: str = "autonomous-competency",
        job_manager: Optional["TrainingJobManager"] = None,
        on_cycle: Optional[Callable[[CompetencyResult, List["TrainingJob"]], None]] = None,
        monitoring: bool = False,
    ) -> None:
        if not domains:
            raise ValueError("AutonomousCompetencyLoop requires at least one DomainSpec.")
        self.domains = domains
        self.base = base
        self.dependency = dict(dependency) if dependency else {}
        self.lambda_centrality = lambda_centrality
        self.deficit_threshold = deficit_threshold
        self.target_index = target_index
        self.interval_seconds = interval_seconds
        self.max_jobs_per_cycle = max_jobs_per_cycle
        self.auto_train = auto_train
        self.force_retrain = force_retrain
        self.base_model = base_model
        self.name = name
        self.job_manager = job_manager
        self.on_cycle = on_cycle
        self.monitoring = monitoring

        self.cycle_count = 0
        self.last_result: Optional[CompetencyResult] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def _gather_domains(self) -> List[CompetencyDomain]:
        gathered: List[CompetencyDomain] = []
        for spec in self.domains:
            try:
                value = float(spec.signal())
            except Exception as e:
                logger.warning(f"Competency signal for '{spec.name}' failed: {e}; skipping this cycle.")
                continue
            gathered.append(CompetencyDomain(name=spec.name, competency=value, source="autonomous-signal"))
        return gathered

    def _get_job_manager(self) -> "TrainingJobManager":
        if self.job_manager is not None:
            return self.job_manager
        from buddy.train.jobs import job_manager

        return job_manager

    def evaluate_once(self) -> CompetencyResult:
        """Read live signals and compute the current competency score."""
        ev = CompetencyEval(
            domains=self._gather_domains(),
            base=self.base,
            dependency=self.dependency,
            lambda_centrality=self.lambda_centrality,
            name=self.name,
            monitoring=self.monitoring,
        )
        result = ev.run(print_summary=False, print_results=False)
        self.last_result = result
        return result

    def run_cycle(self) -> Dict[str, Any]:
        """Run one full cycle: measure, score, and (optionally) trigger training."""
        result = self.evaluate_once()
        self.cycle_count += 1

        started: List["TrainingJob"] = []
        if self.auto_train and result.index < self.target_index:
            data_paths = {s.name: s.data_path for s in self.domains if s.data_path}
            if data_paths:
                started = self._get_job_manager().enqueue_from_competency(
                    result,
                    data_paths,
                    deficit_threshold=self.deficit_threshold,
                    max_jobs=self.max_jobs_per_cycle,
                    base_model=self.base_model,
                    name_prefix=self.name,
                    force=self.force_retrain,
                )

        if self.on_cycle is not None:
            try:
                self.on_cycle(result, started)
            except Exception as e:  # pragma: no cover - callback must not break the loop
                logger.debug(f"on_cycle callback failed: {e}")

        summary = {
            "cycle": self.cycle_count,
            "index": result.index,
            "weakest": result.weakest_domain(),
            "total_deficit": result.total_deficit,
            "jobs_started": [j.id for j in started],
        }
        logger.info(
            f"[{self.name}] cycle {self.cycle_count}: index={result.index:.2%}, "
            f"weakest={summary['weakest']}, jobs_started={len(started)}"
        )
        return summary

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"[{self.name}] cycle failed: {e}")
            # Interruptible sleep until the next cycle.
            self._stop.wait(self.interval_seconds)

    def start(self) -> "AutonomousCompetencyLoop":
        """Start the background loop (no-op if already running)."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return self
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True, name=self.name)
            self._thread.start()
        logger.info(f"[{self.name}] autonomous competency loop started (interval {self.interval_seconds}s).")
        return self

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the loop to stop and wait briefly for the thread to exit."""
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)
        logger.info(f"[{self.name}] autonomous competency loop stopped.")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
