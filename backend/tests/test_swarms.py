"""Tests for swarm topologies (Session 3)."""

import pytest
from app.swarms.base import BaseSwarm, SwarmResult
from app.swarms.manager import get_swarm, list_topologies, SWARM_REGISTRY
from app.swarms.sequential import SequentialSwarm
from app.swarms.parallel import ParallelSwarm


class TestSwarmManager:
    """Tests for swarm manager functions."""

    def test_list_topologies_returns_6(self):
        topologies = list_topologies()
        assert len(topologies) == 6

    def test_list_topologies_contains_expected(self):
        topologies = list_topologies()
        expected = {"sequential", "parallel", "hierarchical", "debate", "consensus", "adaptive"}
        assert set(topologies) == expected

    def test_all_topology_names_are_strings(self):
        for name in list_topologies():
            assert isinstance(name, str)

    def test_get_swarm_sequential(self):
        swarm = get_swarm("sequential")
        assert isinstance(swarm, SequentialSwarm)
        assert isinstance(swarm, BaseSwarm)

    def test_get_swarm_parallel(self):
        swarm = get_swarm("parallel")
        assert isinstance(swarm, ParallelSwarm)
        assert isinstance(swarm, BaseSwarm)

    def test_get_swarm_hierarchical(self):
        swarm = get_swarm("hierarchical")
        assert isinstance(swarm, BaseSwarm)
        assert swarm.topology == "hierarchical"

    def test_get_swarm_debate(self):
        swarm = get_swarm("debate")
        assert isinstance(swarm, BaseSwarm)
        assert swarm.topology == "debate"

    def test_get_swarm_consensus(self):
        swarm = get_swarm("consensus")
        assert isinstance(swarm, BaseSwarm)
        assert swarm.topology == "consensus"

    def test_get_swarm_adaptive(self):
        swarm = get_swarm("adaptive")
        assert isinstance(swarm, BaseSwarm)
        assert swarm.topology == "adaptive"

    def test_get_swarm_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown swarm topology"):
            get_swarm("nonexistent_topology")

    def test_all_registry_values_are_subclasses_of_base(self):
        for name, cls in SWARM_REGISTRY.items():
            assert issubclass(cls, BaseSwarm), f"{name} is not a BaseSwarm subclass"


class TestSwarmResult:
    """Tests for SwarmResult dataclass."""

    def test_swarm_result_required_fields(self):
        sr = SwarmResult(output={"key": "val"}, topology="sequential")
        assert sr.output == {"key": "val"}
        assert sr.topology == "sequential"

    def test_swarm_result_defaults(self):
        sr = SwarmResult(output={}, topology="test")
        assert sr.agents_used == []
        assert sr.total_tokens == 0
        assert sr.total_cost == 0.0
        assert sr.steps_executed == 0
        assert sr.duration_ms == 0

    def test_swarm_result_custom_values(self):
        sr = SwarmResult(
            output={"result": "ok"},
            topology="parallel",
            agents_used=["classifier", "extractor"],
            total_tokens=500,
            total_cost=0.01,
            steps_executed=2,
            duration_ms=123,
        )
        assert sr.agents_used == ["classifier", "extractor"]
        assert sr.total_tokens == 500
        assert sr.total_cost == 0.01
        assert sr.steps_executed == 2
        assert sr.duration_ms == 123


class TestBaseSwarmAbstract:
    """BaseSwarm should not be directly instantiable."""

    def test_cannot_instantiate_base_swarm(self):
        with pytest.raises(TypeError):
            BaseSwarm()


class TestSequentialSwarmExecution:
    """Integration test for SequentialSwarm with demo agents."""

    @pytest.mark.asyncio
    async def test_sequential_returns_swarm_result(self):
        swarm = SequentialSwarm()
        result = await swarm.execute(
            input_data={"text": "Test document content"},
            agent_types=["classifier"],
            config={"demo": True},
        )
        assert isinstance(result, SwarmResult)
        assert result.topology == "sequential"
        assert "classifier" in result.agents_used
        assert result.steps_executed >= 1

    @pytest.mark.asyncio
    async def test_sequential_chain_two_agents(self):
        swarm = SequentialSwarm()
        result = await swarm.execute(
            input_data={"text": "Some document to process"},
            agent_types=["classifier", "summarizer"],
            config={"demo": True},
        )
        assert isinstance(result, SwarmResult)
        assert result.steps_executed == 2
        assert result.agents_used == ["classifier", "summarizer"]


class TestParallelSwarmExecution:
    """Integration test for ParallelSwarm with demo agents."""

    @pytest.mark.asyncio
    async def test_parallel_returns_swarm_result(self):
        swarm = ParallelSwarm()
        result = await swarm.execute(
            input_data={"text": "Test content for parallel"},
            agent_types=["classifier", "summarizer"],
            config={"demo": True},
        )
        assert isinstance(result, SwarmResult)
        assert result.topology == "parallel"
        assert result.steps_executed == 2
        # Output should contain keys for each agent
        assert "classifier" in result.output
        assert "summarizer" in result.output
