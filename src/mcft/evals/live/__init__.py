"""Live-eval plumbing: RCON client, placeholder substitution, checker eval.

Consumed by the battery runner (Phase 4) and the era ablation (Phase 3).
Everything here is testable without a bot: substitution and latching are
pure functions; checkers translate to RCON commands that can be exercised
against the eval server with blocks placed by hand.
"""

from mcft.evals.live.checkers import CheckerContext, evaluate_checker
from mcft.evals.live.rcon import Rcon
from mcft.evals.live.substitute import substitute

__all__ = ["CheckerContext", "Rcon", "evaluate_checker", "substitute"]
