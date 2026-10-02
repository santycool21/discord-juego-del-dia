import os
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")


async def main():
    async with aiohttp.ClientSession() as session:

        print("🔑 Obteniendo token...")

        async with session.post(
            "https://id.twitch.tv/oauth2/token",
            params={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "client_credentials"
            }
        ) as response:

            data = await response.json()

            if response.status != 200:
                print("❌ Error de Twitch:")
                print(data)
                return

            token = data["access_token"]

        print("✅ Token obtenido.")
        print("🎮 Consultando IGDB...")

        headers = {
            "Client-ID": CLIENT_ID,
            "Authorization": f"Bearer {token}"
        }

        query = """
        fields name, platforms.name, genres.name, first_release_date;
        limit 10;
        """

        async with session.post(
            "https://api.igdb.com/v4/games",
            headers=headers,
            data=query
        ) as response:

            texto = await response.text()

            print("📡 Código de respuesta:", response.status)

            if response.status != 200:
                print("❌ Respuesta de IGDB:")
                print(texto)
                return

            juegos = await response.json()

            print(f"✅ IGDB devolvió {len(juegos)} juegos.")
            print()

            for juego in juegos:
                print("🎮", juego.get("name"))


asyncio.run(main())