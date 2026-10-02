import os
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")


async def main():
    async with aiohttp.ClientSession() as session:

        # Obtener token de Twitch
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
                print("❌ Error obteniendo el token:")
                print(data)
                return

            access_token = data["access_token"]
            print("✅ Conexión con Twitch correcta.")

        # Buscar un juego de prueba
        headers = {
            "Client-ID": CLIENT_ID,
            "Authorization": f"Bearer {access_token}"
        }

        query = """
        fields name, platforms.name, first_release_date, genres.name;
        search "Resident Evil 4";
        limit 1;
        """

        async with session.post(
            "https://api.igdb.com/v4/games",
            headers=headers,
            data=query
        ) as response:

            data = await response.json()

            if response.status != 200:
                print("❌ Error consultando IGDB:")
                print(data)
                return

            print("✅ Conexión con IGDB correcta.")
            print()
            print("🎮 Juego encontrado:")

            game = data[0]

            print("Nombre:", game.get("name"))

            platforms = game.get("platforms", [])
            print("Plataformas:", ", ".join(p["name"] for p in platforms))

            genres = game.get("genres", [])
            print("Géneros:", ", ".join(g["name"] for g in genres))


asyncio.run(main())