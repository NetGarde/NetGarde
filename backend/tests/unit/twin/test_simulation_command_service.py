from app.features.twin.schemas.simulation_command import SimulationCommandRequest
from app.features.twin.services.simulation_command_service import SimulationCommandService


def test_rules_block_port():
    result = SimulationCommandService().parse(
        SimulationCommandRequest(prompt="block port 443", active_ports=[443]),
    )
    assert result.action == "block_port"
    assert result.port == 443
    assert result.source == "rules"


def test_rules_block_https_alias():
    result = SimulationCommandService().parse(
        SimulationCommandRequest(prompt="stop https traffic", active_ports=[]),
    )
    assert result.action == "block_port"
    assert result.port == 443
    assert result.source == "rules"


def test_rules_clear_simulation():
    result = SimulationCommandService().parse(
        SimulationCommandRequest(prompt="clear simulation", active_ports=[443]),
    )
    assert result.action == "clear_simulation"
    assert result.source == "rules"


def test_rules_unblock_port():
    result = SimulationCommandService().parse(
        SimulationCommandRequest(prompt="unblock port 53", active_ports=[53]),
    )
    assert result.action == "unblock_port"
    assert result.port == 53
    assert result.source == "rules"


def test_rules_block_gateway():
    result = SimulationCommandService().parse(
        SimulationCommandRequest(prompt="block ec2 dns", active_ports=[]),
    )
    assert result.action == "block_gateway"
    assert result.source == "rules"
