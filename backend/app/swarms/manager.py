"""SwarmManager — registry for swarm topologies."""

from app.swarms.base import BaseSwarm
from app.swarms.sequential import SequentialSwarm
from app.swarms.parallel import ParallelSwarm
from app.swarms.hierarchical import HierarchicalSwarm
from app.swarms.debate import DebateSwarm
from app.swarms.consensus import ConsensusSwarm
from app.swarms.adaptive import AdaptiveSwarm

SWARM_REGISTRY: dict[str, type[BaseSwarm]] = {
    "sequential": SequentialSwarm,
    "parallel": ParallelSwarm,
    "hierarchical": HierarchicalSwarm,
    "debate": DebateSwarm,
    "consensus": ConsensusSwarm,
    "adaptive": AdaptiveSwarm,
}


def get_swarm(topology: str) -> BaseSwarm:
    """Instantiate and return a swarm by topology name."""
    if topology not in SWARM_REGISTRY:
        raise ValueError(
            f"Unknown swarm topology: '{topology}'. "
            f"Available: {list(SWARM_REGISTRY.keys())}"
        )
    return SWARM_REGISTRY[topology]()


def list_topologies() -> list[str]:
    """Return all registered topology names."""
    return list(SWARM_REGISTRY.keys())
