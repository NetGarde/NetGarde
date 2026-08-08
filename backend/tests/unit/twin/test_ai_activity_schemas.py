"""Unit tests for AI activity schemas."""

from app.features.twin.schemas.ai_activity import (
    AiSessionChainResponse,
    AiSessionDetailResponse,
    AiSessionGraphResponse,
    AiSessionListResponse,
    AiSessionTimelineResponse,
)


def test_ai_session_list_schema():
    payload = {
        "device_id": "dev_1",
        "total": 1,
        "items": [
            {
                "session_id": "ais_abc",
                "device_id": "dev_1",
                "app_name": "cursor",
                "root_process_id": "p1",
                "root_pid": 10,
                "start_time": "2026-08-06T12:00:00Z",
                "status": "active",
                "counters": {
                    "tool_executions": 2,
                    "files_read": 0,
                    "files_modified": 0,
                    "network_connections": 1,
                    "process_count": 4,
                },
                "risk_score": 50,
            }
        ],
    }
    model = AiSessionListResponse.model_validate(payload)
    assert model.total == 1
    assert model.items[0].app_name == "cursor"
    assert model.items[0].counters.tool_executions == 2


def test_ai_session_detail_and_graph_timeline():
    detail = AiSessionDetailResponse.model_validate(
        {
            "session_id": "ais_abc",
            "device_id": "dev_1",
            "app_name": "cursor",
            "root_process_id": "p1",
            "root_pid": 10,
            "start_time": "2026-08-06T12:00:00Z",
            "processes": {"p1": {"pid": 10, "name": "Cursor"}},
            "spawn_tree": {"process_id": "p1", "children": []},
            "tools": [],
            "findings": [],
            "activity_chain": [
                {"kind": "app", "label": "Cursor", "detail": "session started"},
                {"kind": "secret", "label": "Opened ~/.ssh", "detail": "~/.ssh/id_rsa"},
            ],
        }
    )
    assert detail.spawn_tree["process_id"] == "p1"
    assert len(detail.activity_chain) == 2

    graph = AiSessionGraphResponse.model_validate(
        {
            "session_id": "ais_abc",
            "device_id": "dev_1",
            "app_name": "cursor",
            "graph": {"nodes": [{"id": "p1", "label": "Cursor", "kind": "process"}], "edges": []},
        }
    )
    assert len(graph.graph["nodes"]) == 1

    timeline = AiSessionTimelineResponse.model_validate(
        {
            "session_id": "ais_abc",
            "device_id": "dev_1",
            "total": 1,
            "items": [
                {
                    "kind": "process_start",
                    "timestamp": "2026-08-06T12:00:00Z",
                    "process_id": "p1",
                    "summary": "root",
                }
            ],
        }
    )
    assert timeline.total == 1

    chain = AiSessionChainResponse.model_validate(
        {
            "session_id": "ais_abc",
            "device_id": "dev_1",
            "app_name": "cursor",
            "total": 2,
            "items": [
                {"kind": "app", "label": "Cursor"},
                {"kind": "network", "label": "Connected to api.openai.com"},
            ],
        }
    )
    assert chain.total == 2
    assert chain.items[1]["label"].startswith("Connected")
