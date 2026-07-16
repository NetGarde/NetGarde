def test_network_overview_route(
    api_client,
    dashboard_env,
    seed_policy,
):
    response = api_client.get("/dashboard/network-overview", params={"period_minutes": 60})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "template"
    assert "bullets" in body
    assert "stats" in body
