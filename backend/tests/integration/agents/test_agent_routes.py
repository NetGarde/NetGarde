def test_upsert_and_list_agents(api_client, ingest_env):
    upsert = api_client.post(
        "/internal/agents/upsert",
        json={
            "agent_id": "dev_api1",
            "hostname": "laptop-1",
            "os": "darwin",
            "arch": "arm64",
            "agent_version": "1.0.0",
        },
    )
    assert upsert.status_code == 200
    body = upsert.json()
    assert body["agent_id"] == "dev_api1"
    assert body["hostname"] == "laptop-1"

    listed = api_client.get("/agents")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert payload["items"][0]["agent_id"] == "dev_api1"

    detail = api_client.get("/agents/dev_api1")
    assert detail.status_code == 200
    assert detail.json()["hostname"] == "laptop-1"

    missing = api_client.get("/agents/dev_missing")
    assert missing.status_code == 404

    rename = api_client.post(
        "/internal/agents/upsert",
        json={"agent_id": "dev_api1", "hostname": "laptop-renamed"},
    )
    assert rename.status_code == 200
    assert rename.json()["hostname"] == "laptop-renamed"
    assert api_client.get("/agents").json()["items"][0]["hostname"] == "laptop-renamed"
