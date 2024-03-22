import asyncio


async def handle_echo(reader, writer):
    data = await reader.readline()
    message = data.decode()
    print(f"The TCP server received the message: {message}")
    writer.write(f"The TCP server received: {message}\n".encode())
    await writer.drain()

    print("Close the connection")
    writer.close()
    await writer.wait_closed()


async def main():
    server = await asyncio.start_server(handle_echo, "127.0.0.1", 8888)

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"Serving on {addrs}")

    async with server:
        await server.serve_forever()


asyncio.run(main())
