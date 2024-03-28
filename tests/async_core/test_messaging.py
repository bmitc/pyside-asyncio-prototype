# Core dependencies
import asyncio

# Package dependencies
from hypothesis import given, settings, HealthCheck
from hypothesis.strategies import one_of, text, integers, floats, tuples, none, lists, uuids
import pytest

# Project dependencies
from prototype.async_core.messaging import AsyncInbox


@pytest.mark.asyncio
@given(one_of(text(), integers(), floats(allow_nan=False), tuples(text(), integers()), none()))
async def test_send_and_read_message(input):
    """Verify that reading a message matches what was sent"""
    inbox = AsyncInbox[str | int | float | tuple[str, int] | None]()
    inbox.send(input)
    message = await inbox.read()
    assert message == input


@pytest.mark.asyncio
@given(lists(integers()))
async def test_first_in_first_out(input_list):
    """Verify that the inbox implements a FIFO"""
    inbox = AsyncInbox[list[int]]()
    for integer in input_list:
        inbox.send(integer)
    messages = [await inbox.read() for _ in input_list]
    assert messages == input_list


@pytest.mark.asyncio
@given(lists(uuids(), min_size=1000))
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
async def test_a_lot_of_messages(input_list):
    """Verify that the inbox can handle a lot of queued up messages. Since this
    test tests large lists, the too slow healthcheck is disabled and examples are
    limited to 10 instead of the default of 100.
    """
    inbox = AsyncInbox[str]()
    for uuid in input_list:
        inbox.send(uuid)
    messages = [await inbox.read() for _ in input_list]
    assert messages == input_list


@pytest.mark.asyncio
async def test_that_sending_synchronously_blocks():
    """Verify that sending a synchronous message to an inbox that is not
    being concurrently read and replying to messages blocks and doesn't
    return, thus raises a timeout.
    """
    with pytest.raises(TimeoutError):
        inbox = AsyncInbox[str]()
        async with asyncio.timeout(1):
            await inbox.send_synchronous("test")


@pytest.mark.asyncio
async def test_sending_a_synchronous_message():
    """Verify that sending a synchronous message works when there's a task reading
    the inbox and replying to messages.
    """

    async def read_inbox(inbox: AsyncInbox[int]) -> None:
        match await inbox.read():
            case (x, reply_channel):
                reply_channel.reply(2 * x)

    async def send_sync_message(inbox: AsyncInbox[int], message: int) -> int:
        return await inbox.send_synchronous(message)

    inbox = AsyncInbox[int]()
    [_, response] = await asyncio.gather(read_inbox(inbox), send_sync_message(inbox, 3))
    assert response == 6
