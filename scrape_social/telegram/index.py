from telethon import TelegramClient

api_id = "26958023"
api_hash = "ae2023d1fd68dc7a61f6c4465e864510"

client = TelegramClient('anon', api_id, api_hash)

async def main():
    await client.send_message('me', 'Hello from python')

with client:
    client.loop.run_until_complete(main())