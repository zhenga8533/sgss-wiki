from dotenv import load_dotenv
from util.file import load
from util.format import format_id
from util.logger import Logger
import glob
import json
import logging
import os


# Load the environment variables and logger.
load_dotenv()
POKEMON_INPUT_PATH = os.getenv("POKEMON_INPUT_PATH")

LOG = os.getenv("LOG") == "True"
LOG_PATH = os.getenv("LOG_PATH")
logger = Logger("Pokemon Loader", LOG_PATH + "pokemon.log", LOG)

# Load all the pokemon data.
pokemon = {}

files = glob.glob(f"{POKEMON_INPUT_PATH}*.json")
for file in files:
    data = json.loads(load(file, logger))
    name = format_id(file.split("\\")[-1].split(".")[0])
    pokemon[name] = data
    logger.log(logging.INFO, f"Loaded pokemon {name}")


def get_pokemon(name: str) -> dict:
    """
    Get the pokemon data for a pokemon.

    :param name: The name of the pokemon.
    :return: The pokemon data.
    """

    id = format_id(name)
    if id in pokemon:
        return pokemon[id]
    else:
        logger.log(logging.ERROR, f"Pokemon {id} not found")
        return None
