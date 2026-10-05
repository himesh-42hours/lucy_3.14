import asyncio
import websockets

clients = set()

async def handler(websocket):

    clients.add(websocket)

    print("Client connected")

    try:

        async for message in websocket:

            print("RECEIVED:", message)

            dead = []

            for client in clients:

                if client == websocket:
                    continue

                try:
                    await client.send(message)

                except:
                    dead.append(client)

            for d in dead:
                clients.remove(d)

    finally:

        clients.remove(websocket)

        print("Client disconnected")

async def broadcast(message):

    dead = []

    for client in clients:

        try:
            await client.send(message)

        except:
            dead.append(client)

    for d in dead:
        clients.remove(d)


async def main():

    async with websockets.serve(
        handler,
        "0.0.0.0",
        8765
    ):
        print("UI websocket running")

        await asyncio.Future()


asyncio.run(main())