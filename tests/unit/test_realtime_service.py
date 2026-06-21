"""Unit tests for websocket realtime hub."""

import asyncio

from src.qlib_research.app.services.realtime_service import RealtimeHub


class MockWebSocket:
    """Simple async websocket mock."""

    def __init__(self):
        self.accepted = False
        self.messages = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload):
        self.messages.append(payload)


def test_connect_and_status():
    hub = RealtimeHub()
    socket = MockWebSocket()

    async def run():
        await hub.connect(socket, "client-1", {"AAPL"})
        status = hub.status()
        assert socket.accepted is True
        assert status["active_clients"] == 1
        assert status["subscriptions"]["client-1"] == ["AAPL"]

    asyncio.run(run())


def test_subscription_filtering_on_broadcast():
    hub = RealtimeHub()
    socket_a = MockWebSocket()
    socket_b = MockWebSocket()

    async def run():
        await hub.connect(socket_a, "client-a", {"AAPL"})
        await hub.connect(socket_b, "client-b", {"MSFT"})
        delivered = await hub.broadcast_price_update("AAPL", 100.0, 1000, 0.5)
        assert delivered == 1
        assert len(socket_a.messages) == 1
        assert len(socket_b.messages) == 0
        assert socket_a.messages[0]["event"] == "price_update"

    asyncio.run(run())


def test_unsubscribe_and_disconnect():
    hub = RealtimeHub()
    socket = MockWebSocket()

    async def run():
        await hub.connect(socket, "client-1", {"AAPL", "MSFT"})
        subscriptions = hub.unsubscribe("client-1", {"AAPL"})
        assert subscriptions == {"MSFT"}
        hub.disconnect("client-1")
        status = hub.status()
        assert status["active_clients"] == 0

    asyncio.run(run())


def test_user_scoped_broadcast():
    hub = RealtimeHub()
    socket_a = MockWebSocket()
    socket_b = MockWebSocket()

    async def run():
        await hub.connect(socket_a, "client-a", {"AAPL"}, user_id=1)
        await hub.connect(socket_b, "client-b", {"AAPL"}, user_id=2)
        delivered = await hub.broadcast(
            event_type="order_update",
            data={"order_id": "123"},
            ticker="AAPL",
            user_id=1,
        )
        assert delivered == 1
        assert len(socket_a.messages) == 1
        assert len(socket_b.messages) == 0

    asyncio.run(run())
