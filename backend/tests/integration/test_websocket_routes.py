def test_device_usage_websocket_ping(api_client, mock_usage_ws_service):
    with api_client.websocket_connect("/devices/usage/ws") as ws:
        snapshot = ws.receive_text()
        assert "history" in snapshot
        ws.send_text("ping")
        assert ws.receive_text() == "pong"
