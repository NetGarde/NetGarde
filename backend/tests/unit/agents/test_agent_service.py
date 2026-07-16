from app.features.agents.services.agent_service import AgentService
from app.features.agents.schemas.agent import AgentUpsertRequest


def test_upsert_creates_then_updates_hostname(db_session):
    service = AgentService(db_session)

    created = service.upsert(
        AgentUpsertRequest(
            agent_id="dev_abc123",
            hostname="old-host",
            os="darwin",
            os_version="14.0",
            arch="arm64",
            agent_version="0.1.0",
        )
    )
    assert created.agent_id == "dev_abc123"
    assert created.hostname == "old-host"
    assert created.status == "registered"
    first_seen = created.first_seen_at

    updated = service.upsert(
        AgentUpsertRequest(
            agent_id="dev_abc123",
            hostname="new-host",
            agent_version="0.1.1",
        )
    )
    assert updated.agent_id == "dev_abc123"
    assert updated.id == created.id
    assert updated.hostname == "new-host"
    assert updated.agent_version == "0.1.1"
    assert updated.os == "darwin"
    assert updated.first_seen_at == first_seen

    listed = service.list_agents()
    assert listed.total == 1
    assert listed.items[0].hostname == "new-host"
