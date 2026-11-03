"""Single routing entry point for customer messages.

The router owns no classification rules: it delegates to the injected
``DecisionModel`` and returns its structured, auditable decision.  Execution of
tools and critical operations belongs to a future orchestrator, never here.
"""

from dataclasses import dataclass

from src.application.decisions import ConversationContext, Decision, DecisionModel, Intent


@dataclass(frozen=True, slots=True)
class Router:
    """Adapt the decision port to the application routing boundary."""

    decision_model: DecisionModel

    def route(self, message: str, context: ConversationContext) -> Decision:
        """Return a decision without performing I/O or invoking tools."""
        decision = self.decision_model.decide(message, context)
        if decision is not None:
            return decision
        return Decision(
            intent=Intent.CLARIFICATION,
            confidence=0.0,
            reason="Decision model did not produce a safe classification.",
            action="ask_clarifying_question",
            needs_clarification=True,
        )
