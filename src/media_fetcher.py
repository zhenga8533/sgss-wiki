from bs4 import BeautifulSoup
from dotenv import load_dotenv
from util.file import load
from util.format import verify_pokemon_form
from util.logger import Logger
import json
import logging
import os
import re
import requests
import threading
import time


def request_data(url: str, timeout: int, logger: Logger) -> dict:
    """
    Request data from the PokeAPI (or any API).

    :param url: The URL of the data.
    :param timeout: Request timeout in seconds.
    :param logger: The logger to log messages.
    :return: The JSON data from the URL, or None if unsuccessful.
    """

    attempt = 0

    while True:
        attempt += 1
        logger.log(logging.INFO, f'Requesting data from "{url}" (attempt {attempt}).')

        try:
            response = requests.get(url, timeout=timeout)
        except KeyboardInterrupt:
            # Re-raise KeyboardInterrupt to allow the program to stop immediately.
            raise
        except requests.exceptions.Timeout:
            # Log the timeout and retry the request.
            logger.log(logging.ERROR, f'Request to "{url}" timed out.')
            time.sleep(1)
            continue
        except requests.exceptions.RequestException:
            # Log the exception and retry.
            logger.log(logging.ERROR, f'Request to "{url}" failed.')
            time.sleep(1)
            continue

        # Check the status code of the response.
        status = response.status_code
        if status != 200:
            logger.log(logging.ERROR, f'Failed to request data from "{url}": {status}.')
            return None
        return response


def save_media(media_path: str, media: str, logger: Logger) -> None:
    """
    Save the media content to the specified path.

    :param media_path: The path to save the media content.
    :param media: The media content to save.
    :param logger: The logger to use.
    :return: None
    """

    # Create the directory if it does not exist
    dirs = media_path.rsplit("/", 1)[0]
    if not os.path.exists(dirs):
        os.makedirs(dirs)
        logger.log(logging.INFO, f"Created directory '{dirs}'.")

    # Save the media content to the specified path
    try:
        with open(media_path, "wb") as file:
            file.write(media)
            logger.log(logging.INFO, f"The content was saved to '{media_path}'.")
    except Exception as e:
        logger.log(logging.ERROR, f"An error occurred while saving to {media_path}:\n{e}")
        exit(1)


def fetch_media(pokemon: dict, pokemon_path: str, timeout: int, logger: Logger) -> None:
    """
    Fetch and save media for the specified Pokémon.

    :param pokemon: The Pokémon to fetch media for.
    :param pokemon_path: The path to the Pokémon data files.
    :param timeout: Request timeout in seconds.
    :param logger: The logger to use.
    :return: None
    """

    # Load the Pokémon data
    name = pokemon["name"]
    data = json.loads(load(pokemon_path + name + ".json", logger))
    forms = data.get("forms")

    # Fetch media for each form
    for form in forms:
        if form != name and not verify_pokemon_form(form, logger):
            continue

        form_data = load(pokemon_path + form + ".json", logger)
        form_data = json.loads(form_data) if form_data != "" else data

        # Official artwork
        sprites = form_data["sprites"]
        official_artwork = sprites["other"]["official-artwork"]
        official = official_artwork["front_default"]
        official_shiny = official_artwork["front_shiny"]
        sprite_data = {"official": official, "official_shiny": official_shiny}

        # Generation 4, heartgold-soulsilver sprites
        gen_4 = sprites["versions"]["generation-iv"]["heartgold-soulsilver"]
        for key in gen_4:
            sprite_name = key.replace("_default", "")
            sprite = gen_4[key]
            if sprite:
                sprite_data[sprite_name] = sprite

        # Save all sprites
        for key in sprite_data:
            sprite = sprite_data[key]
            logger.log(logging.INFO, f"Fetching sprite for {form} from {sprite}.")
            response = request_data(sprite, timeout, logger).content
            save_media(f"../docs/assets/sprites/{form}/{key}.png", response, logger)

        # Save cries
        cries = {
            "latest": form_data["cry_latest"] or form_data["cry_legacy"],
            "legacy": form_data["cry_legacy"] or form_data["cry_latest"],
        }
        for key in cries:
            cry = cries[key]
            if cry is None:
                continue

            logger.log(logging.INFO, f"Fetching cry for {form} from {cry}.")
            response = request_data(cry, timeout, logger).content
            save_media(f"../docs/assets/cries/{form}/{key}.ogg", response, logger)


def fetch_media_range(
    start_index: int, end_index: int, pokedex: list, pokemon_path: str, timeout: int, logger: Logger
) -> None:
    """
    Fetch and save media for a range of Pokémon.

    :param start_index: The starting index for the Pokémon range.
    :param end_index: The ending index for the Pokémon range.
    :param pokedex: The list of Pokémon to process.
    :param pokemon_path: Path where Pokémon data is stored.
    :param timeout: Request timeout in seconds.
    :param logger: Logger instance for logging.
    :return: None
    """

    for i in range(start_index, end_index + 1):
        pokemon = pokedex[i]
        fetch_media(pokemon, pokemon_path, timeout, logger)


def fetch_bulbagarden(url: str, pokedex: list[dict], num_threads: int, timeout: int, logger: Logger) -> None:
    """
    Fetch and save Bulbagarden sprites from the specified URL using threading.

    :param url: The URL of the Bulbagarden sprites.
    :param pokedex: The list of Pokémon to process.
    :param num_threads: Number of threads to use for fetching sprites.
    :param timeout: Request timeout in seconds.
    :param logger: Logger instance for logging.
    :return: None
    """

    logger.log(logging.INFO, f"Fetching Bulbagarden sprites from {url}.")
    response = request_data(url, timeout, logger)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    sprites = [img["src"] for img in soup.find_all("img") if "src" in img.attrs and "Spr_" in img["src"]]
    id_regex = r".*?spr_4[hdp]_(\d+)?([a-z-]+)?(?:_([mf]))?$"

    def process_sprite(sprite: str):
        """
        Process the sprite URL to fetch and save the sprite.

        :param sprite: The URL of the sprite.
        :return: None
        """

        sprite_id = sprite.rsplit("/", 1)[1].split(".")[0].lower()

        # Match the sprite ID to extract the number, extension
        match = re.match(id_regex, sprite_id)
        if match:
            num, extension, gender = match.groups()
            extension = extension.replace("-", "") if extension else None
            logger.log(logging.INFO, f"Fetching sprite for {num} ({extension}, {gender}).")

            name = pokedex[int(num) - 1]["name"] + (f"-{extension}" if extension else "")
            view = "front" + ("_female" if gender == "f" else "")
            sprite_img = request_data(sprite, timeout, logger).content
            save_media(f"../docs/assets/sprites/{name}/{view}.png", sprite_img, logger)
        else:
            logger.log(logging.ERROR, f"Failed to match sprite ID: {sprite_id}")

    # Create threads to process each sprite
    threads = []
    for i in range(0, len(sprites), num_threads):
        for sprite in sprites[i : i + num_threads]:
            thread = threading.Thread(target=process_sprite, args=(sprite,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    # Fetch the next page if it exists
    next_page = soup.find("a", string="next page")
    if next_page:
        next_url = "https://archives.bulbagarden.net" + next_page["href"]
        fetch_bulbagarden(next_url, pokedex, num_threads, timeout, logger)


def main():
    """
    Main function for the media fetcher.

    :return: None
    """

    # Load environment variables and logger
    load_dotenv()
    TIMEOUT = int(os.getenv("TIMEOUT"))
    POKEMON_INPUT_PATH = os.getenv("POKEMON_INPUT_PATH")

    LOG = os.getenv("LOG") == "True"
    LOG_PATH = os.getenv("LOG_PATH")
    logger = Logger("Media Fetcher", LOG_PATH + "media_fetcher.log", LOG)

    # Fetch pokedex
    pokedex = request_data("https://pokeapi.co/api/v2/pokemon/?offset=0&limit=493", TIMEOUT, logger)
    pokedex = pokedex.json().get("results")
    logger.log(logging.INFO, pokedex)

    # Determine the range for each thread
    THREADS = int(os.getenv("THREADS"))
    total_pokemon = len(pokedex)
    chunk_size = total_pokemon // THREADS
    remainder = total_pokemon % THREADS

    threads = []
    start_index = 0

    for t in range(THREADS):
        # Calculate the end index for each thread's range
        end_index = start_index + chunk_size - 1
        if remainder > 0:
            end_index += 1
            remainder -= 1

        # Start each thread to handle a specific range of Pokémon
        thread = threading.Thread(
            target=fetch_media_range,
            args=(start_index, end_index, pokedex, POKEMON_INPUT_PATH, logger),
        )
        threads.append(thread)
        thread.start()

        # Update the start_index for the next thread
        start_index = end_index + 1

    # Ensure all threads are completed
    for t in threads:
        t.join()

    # Fetch Bulbagarden media
    url = "https://archives.bulbagarden.net/wiki/Category:HeartGold_and_SoulSilver_sprites"
    fetch_bulbagarden(url, pokedex, THREADS, TIMEOUT, logger)


if __name__ == "__main__":
    main()
