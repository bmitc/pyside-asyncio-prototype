import asyncio
from websockets.server import serve
import functools
import websockets


async def receive_websocket_message(
    websocket, send_queue: asyncio.Queue, receive_queue: asyncio.Queue
):
    # This also should handle application state. For example,
    # a message may transition a state machine to a different
    # state which would then potentially trigger new messages
    # to the TCP client(s).
    async for message in websocket:
        print(f"The WebSocket server received: {message}")
        send_queue.put_nowait(message)
        response = await receive_queue.get()
        await websocket.send(response)


async def websocket_server(send_queue: asyncio.Queue, receive_queue: asyncio.Queue):
    # I don't know if this queue passing as argument works
    bound_handler = functools.partial(
        receive_websocket_message, send_queue=send_queue, receive_queue=receive_queue
    )
    while True:
        try:
            async with serve(bound_handler, "localhost", 8765):
                await asyncio.Future()  # run forever
        except websockets.exceptions.ConnectionClosedError:
            pass


async def tcp_client(send_queue: asyncio.Queue, receive_queue: asyncio.Queue):
    reader, writer = await asyncio.open_connection("127.0.0.1", 8888)

    try:
        while True:
            try:
                message: str = await send_queue.get()
                print(f"The TCP client received: {message}")
                writer.write(f"message\n".encode())
                print("I WROTE SOMETHING")
                await writer.drain()

                data = await reader.readline()
                print(f"The TCP client received a response from the server: {data}")
                receive_queue.put_nowait(data)
            except ConnectionResetError:
                # Re-open the connection
                reader, writer = await asyncio.open_connection("127.0.0.1", 8888)
    except KeyboardInterrupt:
        writer.close()
        await writer.wait_closed()


async def main():
    # Create queues to pass messages back and forth
    send_queue = asyncio.Queue()
    receive_queue = asyncio.Queue()

    await asyncio.gather(
        websocket_server(send_queue, receive_queue),
        tcp_client(send_queue, receive_queue),
    )


asyncio.run(main())
