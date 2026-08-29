"""
Runtime competency routing for Buddy agents and teams.

While :mod:`buddy.eval.competency` scores competency offline and drives a
training loop, this module applies the same competency signal *at task-execution
time*. Given an incoming task it:

1. infers the task's competency domain (via an LLM classifier),
2. selects the most competent member to handle it (lowest deficit in that domain),
3. chooses an execution policy (proceed / review / escalate) and a model tier
   (standard / strong) based on the competency, and
4. records the task outcome back into a live competency tracker, closing the loop
   with real runtime data.

The :class:`CompetencyTracker` produced here exposes ``signal()`` callables that
can be fed directly into :class:`buddy.eval.competency.DomainSpec`, so runtime
outcomes flow into the same scores used by the autonomous learning loop.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from buddy.utils.log import logger

if TYPE_CHECKING:
    from buddy.agent import Agent
    from buddy.models.base import Model


# ----------------------------------------------------------------------------
# Live competency tracker
# ----------------------------------------------------------------------------


class CompetencyTracker:
    """Tracks live per-domain competency, updated from task outcomes.

    Competency is held on a ``0..base`` scale and updated with an exponential
    moving average (EMA): each success nudges the score toward ``base``, each
    failure toward 0. This makes the score reflect *actual* task performance over
    time rather than a fixed, hand-set number.
    """

    def __init__(
        self,
        *,
        base: float = 10.0,
        alpha: float = 0.3,
        seed: Optional[Dict[str, float]] = None,
        default: Optional[float] = None,
    ) -> None:
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1].")
        self.base = base
        self.alpha = alpha
        self.default = default if default is not None else base * 0.5
        self._scores: Dict[str, float] = dict(seed or {})
        self._counts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def get(self, domain: str) -> float:
        with self._lock:
            return self._scores.get(domain, self.default)

    def set(self, domain: str, value: float) -> None:
        with self._lock:
            self._scores[domain] = max(0.0, min(self.base, float(value)))

    def record_outcome(self, domain: str, success: bool, weight: float = 1.0) -> float:
        """Update a domain's competency from a task outcome; returns the new score."""
        target = self.base if success else 0.0
        effective_alpha = min(1.0, self.alpha * max(0.0, weight))
        with self._lock:
            old = self._scores.get(domain, self.default)
            new = (1.0 - effective_alpha) * old + effective_alpha * target
            new = max(0.0, min(self.base, new))
            self._scores[domain] = new
            self._counts[domain] = self._counts.get(domain, 0) + 1
            return new

    def observations(self, domain: str) -> int:
        with self._lock:
            return self._counts.get(domain, 0)

    def signal(self, domain: str) -> Callable[[], float]:
        """Return a callable usable as a DomainSpec signal for the autonomous loop."""
        return lambda: self.get(domain)

    def as_dict(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._scores)


# ----------------------------------------------------------------------------
# Domain classification
# ----------------------------------------------------------------------------


class DomainClassifier:
    """Protocol-ish base: map a task to one of the known domain names."""

    def classify(self, task: str, domains: List[str]) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class KeywordDomainClassifier(DomainClassifier):
    """Cheap fallback: choose the domain whose name appears in the task text."""

    def classify(self, task: str, domains: List[str]) -> str:
        text = (task or "").lower()
        for d in domains:
            if d.lower() in text:
                return d
        return domains[0] if domains else "unknown"


class LLMDomainClassifier(DomainClassifier):
    """Use an LLM to classify the task into one of the known domains."""

    def __init__(self, model: Optional["Model"] = None) -> None:
        self.model = model
        self._agent: Optional["Agent"] = None
        self._fallback = KeywordDomainClassifier()

    def _get_agent(self) -> Optional["Agent"]:
        if self._agent is not None:
            return self._agent
        try:
            from pydantic import BaseModel, Field

            from buddy.agent import Agent

            class DomainChoice(BaseModel):
                domain: str = Field(..., description="The single best-matching domain name.")
                confidence: float = Field(..., description="Confidence between 0 and 1.")

            model = self.model
            if model is None:
                from buddy.models.openai import OpenAIChat

                model = OpenAIChat(id="o4-mini")

            self._agent = Agent(
                model=model,
                description=(
                    "You are a task router. Given a task and a list of competency "
                    "domains, return the single domain that best matches the task. "
                    "You must choose exactly one name from the provided list."
                ),
                response_model=DomainChoice,
                structured_outputs=True,
            )
            return self._agent
        except Exception as e:
            logger.debug(f"LLM domain classifier unavailable, using keyword fallback: {e}")
            return None

    def classify(self, task: str, domains: List[str]) -> str:
        if not domains:
            return "unknown"
        agent = self._get_agent()
        if agent is None:
            return self._fallback.classify(task, domains)
        try:
            prompt = (
                f"Domains: {', '.join(domains)}\n\n"
                f"Task: {task}\n\n"
                "Return the single best-matching domain name from the list."
            )
            choice = agent.run(prompt).content
            domain = getattr(choice, "domain", None)
            if isinstance(domain, str):
                # Match case-insensitively back to a known domain.
                for d in domains:
                    if d.lower() == domain.strip().lower():
                        return d
            logger.debug(f"Classifier returned unrecognized domain '{domain}'; using fallback.")
        except Exception as e:
            logger.debug(f"LLM classification failed: {e}; using keyword fallback.")
        return self._fallback.classify(task, domains)


# ----------------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------------


@dataclass
class MemberProfile:
    """A routable agent and its own live competency tracker."""

    agent: "Agent"
    tracker: CompetencyTracker
    name: Optional[str] = None

    def __post_init__(self) -> None:
        if self.name is None:
            self.name = getattr(self.agent, "name", None) or f"member-{id(self.agent):x}"


@dataclass
class RoutingDecision:
    task: str
    domain: str
    member_name: str
    competency: float
    deficit: float
    policy: str  # "proceed" | "review" | "escalate"
    model_tier: str  # "standard" | "strong"
    reason: str
    candidates: Dict[str, float] = field(default_factory=dict)


class CompetencyRouter:
    """Route tasks to the most competent member and adapt execution to competency.

    Works for a single agent (one member) or a team (many members). Thresholds are
    expressed as fractions of ``base``.
    """

    def __init__(
        self,
        members: List[MemberProfile],
        *,
        base: float = 10.0,
        domains: Optional[List[str]] = None,
        review_threshold: float = 0.6,
        escalate_threshold: float = 0.3,
        strong_deficit_ratio: float = 0.4,
        classifier: Optional[DomainClassifier] = None,
        model: Optional["Model"] = None,
        strong_model: Optional["Model"] = None,
    ) -> None:
        if not members:
            raise ValueError("CompetencyRouter requires at least one MemberProfile.")
        self.members = members
        self.base = base
        self.review_threshold = review_threshold
        self.escalate_threshold = escalate_threshold
        self.strong_deficit_ratio = strong_deficit_ratio
        self.classifier = classifier or LLMDomainClassifier(model=model)
        self.strong_model = strong_model
        self._by_name = {m.name: m for m in members}

        if domains is not None:
            self.domains = list(domains)
        else:
            seen: List[str] = []
            for m in members:
                for d in m.tracker.as_dict():
                    if d not in seen:
                        seen.append(d)
            self.domains = seen

    def _select_member(self, domain: str) -> Tuple[MemberProfile, Dict[str, float]]:
        candidates = {m.name: m.tracker.get(domain) for m in self.members}  # type: ignore[misc]
        best = max(self.members, key=lambda m: m.tracker.get(domain))
        return best, candidates

    def decide(self, task: str, *, domain: Optional[str] = None) -> RoutingDecision:
        resolved_domain = domain or self.classifier.classify(task, self.domains)
        member, candidates = self._select_member(resolved_domain)
        competency = member.tracker.get(resolved_domain)
        deficit = self.base - competency
        ratio = competency / self.base if self.base > 0 else 0.0

        if ratio < self.escalate_threshold:
            policy = "escalate"
        elif ratio < self.review_threshold:
            policy = "review"
        else:
            policy = "proceed"

        model_tier = "strong" if (deficit / self.base if self.base > 0 else 0.0) >= self.strong_deficit_ratio else "standard"

        reason = (
            f"Task classified as '{resolved_domain}'. Best member '{member.name}' has "
            f"competency {competency:.2f}/{self.base:.0f} (deficit {deficit:.2f}) -> "
            f"policy={policy}, model_tier={model_tier}."
        )
        return RoutingDecision(
            task=task,
            domain=resolved_domain,
            member_name=member.name,  # type: ignore[arg-type]
            competency=competency,
            deficit=deficit,
            policy=policy,
            model_tier=model_tier,
            reason=reason,
            candidates=candidates,
        )

    def run(
        self,
        task: str,
        *,
        domain: Optional[str] = None,
        success_evaluator: Optional[Callable[[str, Any], bool]] = None,
        record: bool = True,
        block_on_escalate: bool = False,
        **run_kwargs: Any,
    ) -> Tuple[Any, RoutingDecision]:
        """Route and execute the task, optionally recording the outcome.

        Returns ``(response, decision)``. If ``block_on_escalate`` is True and the
        policy is "escalate", the task is not executed and ``response`` is None.
        """
        decision = self.decide(task, domain=domain)
        member = self._by_name[decision.member_name]

        if block_on_escalate and decision.policy == "escalate":
            logger.info(f"[competency-router] escalating task in '{decision.domain}'; not auto-executing.")
            return None, decision

        agent = member.agent
        original_model = None
        if decision.model_tier == "strong" and self.strong_model is not None:
            original_model = getattr(agent, "model", None)
            agent.model = self.strong_model  # type: ignore[attr-defined]

        try:
            response = agent.run(task, **run_kwargs)
        finally:
            if original_model is not None:
                agent.model = original_model  # type: ignore[attr-defined]

        if record and success_evaluator is not None:
            try:
                success = bool(success_evaluator(task, response))
                self.record_outcome(decision, success)
            except Exception as e:
                logger.debug(f"success_evaluator failed: {e}; outcome not recorded.")

        return response, decision

    def record_outcome(self, decision: RoutingDecision, success: bool, weight: float = 1.0) -> None:
        """Feed a task outcome back into the chosen member's competency tracker."""
        member = self._by_name.get(decision.member_name)
        if member is None:
            return
        new_score = member.tracker.record_outcome(decision.domain, success, weight=weight)
        logger.debug(
            f"[competency-router] recorded {'success' if success else 'failure'} for "
            f"'{member.name}'/{decision.domain} -> {new_score:.2f}"
        )
