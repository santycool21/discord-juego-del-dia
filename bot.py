import discord
import aiohttp
import os
import json
import random
import asyncio
import datetime

from dotenv import load_dotenv


# =========================================================
# CONFIGURACIÓN
# =========================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

CHANNEL_ID = 1073046970979074110

PUNTUACION_MINIMA = 65
VOTOS_MINIMOS = 5

HISTORIAL_PLATAFORMAS = 5

ARCHIVO_HISTORIAL = "juegos.json"


# =========================================================
# PLATAFORMAS PERMITIDAS
# =========================================================

PLATAFORMAS_PERMITIDAS = {
    "PC",

    "PlayStation",
    "PlayStation 2",
    "PlayStation 3",
    "PlayStation 4",
    "PlayStation 5",
    "PSP",
    "PlayStation Vita",

    "Xbox",
    "Xbox 360",
    "Xbox One",
    "Xbox Series X|S",

    "NES",
    "SNES",
    "Nintendo 64",
    "Game Boy",
    "Game Boy Color",
    "Game Boy Advance",
    "Nintendo DS",
    "Nintendo 3DS",
    "Nintendo Switch",

    "Dreamcast",
    "Sega Saturn",
    "Genesis / Mega Drive",

    "Android",
    "iOS"
}


# =========================================================
# CLIENTE DE DISCORD
# =========================================================

intents = discord.Intents.default()

client = discord.Client(
    intents=intents
)


# =========================================================
# HISTORIAL
# =========================================================

def cargar_historial():

    try:

        with open(
            ARCHIVO_HISTORIAL,
            "r",
            encoding="utf-8"
        ) as archivo:

            datos = json.load(archivo)

            # Compatibilidad con el formato anterior.
            # Antes juegos.json era simplemente una lista
            # de IDs.

            if isinstance(datos, list):

                return {
                    "juegos": datos,
                    "plataformas": []
                }

            return datos

    except (
        FileNotFoundError,
        json.JSONDecodeError
    ):

        return {
            "juegos": [],
            "plataformas": []
        }


def guardar_historial(datos):

    with open(
        ARCHIVO_HISTORIAL,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            datos,
            archivo,
            indent=4,
            ensure_ascii=False
        )


# =========================================================
# TOKEN DE IGDB / TWITCH
# =========================================================

async def obtener_token_twitch():

    url = "https://id.twitch.tv/oauth2/token"

    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }

    async with aiohttp.ClientSession() as session:

        async with session.post(
            url,
            params=params
        ) as response:

            if response.status != 200:

                print(
                    "❌ Error obteniendo token de Twitch:",
                    response.status
                )

                print(
                    await response.text()
                )

                return None

            datos = await response.json()

            return datos["access_token"]


# =========================================================
# BUSCAR JUEGOS EN IGDB
# =========================================================

async def buscar_juegos():

    token = await obtener_token_twitch()

    if not token:
        return []

    url = "https://api.igdb.com/v4/games"

    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }

    todos_los_juegos = []

    # Diferentes bloques de juegos.
    # Cada uno busca una parte distinta del catálogo.

    consultas = [

        # Juegos muy populares
        """
        sort total_rating_count desc;
        limit 500;
        offset 0;
        """,

        # Juegos con bastantes valoraciones
        """
        sort total_rating_count desc;
        limit 500;
        offset 500;
        """,

        # Juegos con menos valoraciones
        """
        sort total_rating_count asc;
        limit 500;
        offset 0;
        """,

        # Juegos de puntuación alta
        """
        sort total_rating desc;
        limit 500;
        offset 0;
        """
    ]

    async with aiohttp.ClientSession() as session:

        for numero, orden in enumerate(
            consultas,
            start=1
        ):

            query = f"""
                fields
                    id,
                    name,
                    platforms.name,
                    genres.name,
                    first_release_date,
                    summary,
                    cover.url,
                    total_rating,
                    total_rating_count,
                    category;

                {orden}
            """

            async with session.post(
                url,
                headers=headers,
                data=query
            ) as response:

                if response.status != 200:

                    print(
                        f"❌ Error de IGDB "
                        f"en consulta {numero}:",
                        response.status
                    )

                    print(
                        await response.text()
                    )

                    continue

                juegos = await response.json()

                print(
                    f"📚 Consulta {numero}/4: "
                    f"{len(juegos)} juegos."
                )

                todos_los_juegos.extend(
                    juegos
                )

    # Eliminar posibles duplicados.
    # Algunos juegos pueden aparecer
    # en más de una consulta.

    juegos_unicos = {}

    for juego in todos_los_juegos:

        juego_id = juego.get("id")

        if juego_id is not None:

            juegos_unicos[juego_id] = juego

    juegos_finales = list(
        juegos_unicos.values()
    )

    print(
        f"📚 IGDB devolvió "
        f"{len(todos_los_juegos)} resultados."
    )

    print(
        f"🎮 Después de eliminar duplicados: "
        f"{len(juegos_finales)} juegos."
    )

    return juegos_finales


# =========================================================
# FILTRAR JUEGOS
# =========================================================

def filtrar_juegos(juegos):

    datos_historial = cargar_historial()

    historial = datos_historial["juegos"]

    validos = []

    for juego in juegos:

        # Evitar juegos ya recomendados

        if juego.get("id") in historial:
            continue

        # Puntuación

        puntuacion = juego.get(
            "total_rating"
        )

        if puntuacion is None:
            continue

        if puntuacion < PUNTUACION_MINIMA:
            continue

        # Cantidad de valoraciones

        votos = juego.get(
            "total_rating_count",
            0
        )

        if votos < VOTOS_MINIMOS:
            continue

        # Plataformas

        plataformas = juego.get(
            "platforms",
            []
        )

        nombres_plataformas = {
            plataforma["name"]
            for plataforma in plataformas
        }

        if not nombres_plataformas.intersection(
            PLATAFORMAS_PERMITIDAS
        ):
            continue

        # Nombre

        if not juego.get("name"):
            continue

        # Descripción

        if not juego.get("summary"):
            continue

        # Géneros

        if not juego.get("genres"):
            continue

        validos.append(juego)

    return validos


# =========================================================
# OBTENER NOMBRES DE PLATAFORMAS
# =========================================================

def obtener_nombre_plataformas(juego):

    plataformas = juego.get(
        "platforms",
        []
    )

    nombres = []

    for plataforma in plataformas:

        nombre = plataforma.get("name")

        if nombre in PLATAFORMAS_PERMITIDAS:
            nombres.append(nombre)

    return nombres


# =========================================================
# OBTENER GÉNEROS
# =========================================================

def obtener_generos(juego):

    generos = juego.get(
        "genres",
        []
    )

    nombres = []

    for genero in generos:

        nombre = genero.get("name")

        if nombre:
            nombres.append(nombre)

    return nombres


# =========================================================
# RECOMENDAR JUEGO
# =========================================================

async def recomendar_juego():

    print("\n🎮 Buscando juego del día...")

    juegos = await buscar_juegos()

    if not juegos:

        print(
            "❌ IGDB no devolvió juegos."
        )

        return

    validos = filtrar_juegos(juegos)

    print(
        f"🎮 Juegos que cumplen los filtros: "
        f"{len(validos)}"
    )

    if not validos:

        print(
            "❌ No hay juegos que cumplan "
            "los filtros."
        )

        return

    # =====================================================
    # VARIEDAD DE PUNTUACIONES
    # =====================================================

    juegos_65_69 = []
    juegos_70_79 = []
    juegos_80_89 = []
    juegos_90_plus = []

    for juego in validos:

        puntuacion = juego.get(
            "total_rating",
            0
        )

        if puntuacion < 70:

            juegos_65_69.append(juego)

        elif puntuacion < 80:

            juegos_70_79.append(juego)

        elif puntuacion < 90:

            juegos_80_89.append(juego)

        else:

            juegos_90_plus.append(juego)

    grupos = []

    # Mayor posibilidad de juegos
    # de puntuación media.

    if juegos_65_69:
        grupos.extend(
            [juegos_65_69] * 4
        )

    if juegos_70_79:
        grupos.extend(
            [juegos_70_79] * 4
        )

    if juegos_80_89:
        grupos.extend(
            [juegos_80_89] * 2
        )

    if juegos_90_plus:
        grupos.append(
            juegos_90_plus
        )

    grupo_elegido = random.choice(
        grupos
    )

    candidatos = grupo_elegido.copy()


    # =====================================================
    # VARIEDAD DE PLATAFORMAS
    # =====================================================

    datos_historial = cargar_historial()

    historial_plataformas = datos_historial[
        "plataformas"
    ]

    candidatos_variedad = []

    for juego in candidatos:

        plataformas = {
            plataforma["name"]
            for plataforma in juego.get(
                "platforms",
                []
            )
        }

        plataformas_validas = (
            plataformas.intersection(
                PLATAFORMAS_PERMITIDAS
            )
        )

        # Si ninguna plataforma del juego
        # apareció recientemente,
        # le damos prioridad.

        if not plataformas_validas.intersection(
            set(historial_plataformas)
        ):

            candidatos_variedad.append(
                juego
            )

    if candidatos_variedad:

        candidatos = candidatos_variedad


    # =====================================================
    # ELEGIR JUEGO
    # =====================================================

    juego = random.choice(
        candidatos
    )


    # =====================================================
    # GUARDAR HISTORIAL DEL JUEGO
    # =====================================================

    historial_juegos = datos_historial[
        "juegos"
    ]

    historial_juegos.append(
        juego["id"]
    )


    # =====================================================
    # GUARDAR PLATAFORMA UTILIZADA
    # =====================================================

    plataformas_juego = [
        plataforma["name"]
        for plataforma in juego.get(
            "platforms",
            []
        )
        if plataforma["name"]
        in PLATAFORMAS_PERMITIDAS
    ]

    if plataformas_juego:

        plataforma_principal = random.choice(
            plataformas_juego
        )

        historial_plataformas.append(
            plataforma_principal
        )

        historial_plataformas = (
            historial_plataformas[
                -HISTORIAL_PLATAFORMAS:
            ]
        )


    # =====================================================
    # GUARDAR TODO
    # =====================================================

    datos_historial["juegos"] = (
        historial_juegos
    )

    datos_historial["plataformas"] = (
        historial_plataformas
    )

    guardar_historial(
        datos_historial
    )


    # =====================================================
    # MOSTRAR EN CONSOLA
    # =====================================================

    print(
        f"✅ Recomendado: "
        f"{juego['name']}"
    )

    print(
        f"⭐ Puntuación: "
        f"{juego.get('total_rating', 0):.1f}/100"
    )

    print(
        f"👥 Valoraciones: "
        f"{juego.get('total_rating_count', 0)}"
    )


    # =====================================================
    # OBTENER CANAL DE DISCORD
    # =====================================================

    canal = client.get_channel(
        CHANNEL_ID
    )

    if canal is None:

        print(
            "❌ No se encontró el canal."
        )

        return


    # =====================================================
    # INFORMACIÓN DEL JUEGO
    # =====================================================

    plataformas = obtener_nombre_plataformas(
        juego
    )

    generos = obtener_generos(
        juego
    )

    año = "Desconocido"

    if juego.get(
        "first_release_date"
    ):

        fecha = datetime.datetime.fromtimestamp(
            juego["first_release_date"]
        )

        año = fecha.year


    puntuacion = juego.get(
        "total_rating",
        0
    )


    # =====================================================
    # CREAR EMBED
    # =====================================================

    embed = discord.Embed(
        title="🎮 Juego recomendado del día",
        description=juego["summary"]
    )


    embed.add_field(
        name="🕹️ Plataformas",
        value=(
            ", ".join(plataformas)
            if plataformas
            else "Desconocidas"
        ),
        inline=False
    )


    embed.add_field(
        name="🎭 Género",
        value=(
            ", ".join(generos)
            if generos
            else "Desconocido"
        ),
        inline=True
    )


    embed.add_field(
        name="📅 Año",
        value=str(año),
        inline=True
    )


    embed.add_field(
        name="⭐ Puntuación IGDB",
        value=f"{puntuacion:.1f}/100",
        inline=True
    )


    # =====================================================
    # PORTADA
    # =====================================================

    if juego.get("cover"):

        imagen = juego["cover"]["url"]

        if imagen.startswith("//"):

            imagen = (
                "https:"
                + imagen
            )

        imagen = imagen.replace(
            "t_thumb",
            "t_cover_big"
        )

        embed.set_thumbnail(
            url=imagen
        )


    # =====================================================
    # ENVIAR A DISCORD
    # =====================================================

    await canal.send(
        embed=embed
    )


# =========================================================
# EVENTO AL CONECTARSE
# =========================================================

@client.event
async def on_ready():

    print(
        f"\n🤖 Bot conectado como "
        f"{client.user}"
    )

    try:

        await recomendar_juego()

    except Exception as error:

        print(
            "❌ Ocurrió un error:",
            error
        )

    finally:

        print(
            "✅ Recomendación enviada. "
            "Cerrando bot..."
        )

        await client.close()


# =========================================================
# INICIAR BOT
# =========================================================

client.run(
    DISCORD_TOKEN
)