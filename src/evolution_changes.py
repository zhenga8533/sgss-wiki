from dotenv import load_dotenv
from util.file import load, save
from util.format import format_id
from util.logger import Logger
import glob
import json
import logging
import os


def fix_evolutions(evolutions: list, pokemon: str, changes: list[str]) -> list:
    """
    Fix the evolutions list in place by adding the change to the specified pokemon.

    :param evolutions: The list of evolutions to fix.
    :param pokemon: The name of the pokemon to add the change to.
    :param changes: The change to add to the specified pokemon.
    :return: All evolutions in the list.
    """

    pokemon_evolutions = []

    for evolution in evolutions:
        name = evolution["name"]
        pokemon_evolutions.append(name)

        if name == pokemon:
            evolution["evolution_changes"] = changes

        pokemon_evolutions += fix_evolutions(evolution.get("evolutions", []), pokemon, changes)

    return pokemon_evolutions


def fix_pokemon(pokemon: list, evolutions: list, POKEMON_INPUT_PATH: str, logger: Logger) -> None:
    """
    Fix the pokemon list in place by adding the evolution changes to the specified pokemon.

    :param pokemon: The list of pokemon to fix.
    :param evolutions: The list of evolutions to fix.
    :param POKEMON_INPUT_PATH: The path to the pokemon data files.
    :param logger: The logger to use.
    """

    for p in pokemon:
        file_pattern = POKEMON_INPUT_PATH + p + "*.json"
        files = glob.glob(file_pattern)

        # Loop through each Pokémon file
        for file_path in files:
            pokemon_data = json.loads(load(file_path, logger))
            pokemon_data["evolutions"] = evolutions
            save(file_path, json.dumps(pokemon_data, indent=4), logger)


def main():
    """
    Main function for the evolution changes parser.

    :return: None
    """

    # Load environment variables and logger
    load_dotenv()
    INPUT_PATH = os.getenv("INPUT_PATH")
    OUTPUT_PATH = os.getenv("OUTPUT_PATH")
    POKEMON_INPUT_PATH = os.getenv("POKEMON_INPUT_PATH")

    LOG = os.getenv("LOG") == "True"
    LOG_PATH = os.getenv("LOG_PATH")
    logger = Logger("Evolution Changes Parser", LOG_PATH + "evolution_changes.log", LOG)

    # Read input data
    data = load(INPUT_PATH + "Evolution Changes.txt", logger)
    lines = data.split("\n")
    n = len(lines)
    md = "# Evolution Changes\n\n"

    skip_next = False
    curr_pokemon = None
    changes = []

    # Parse all lines in the input data file
    logger.log(logging.INFO, "Parsing data...")
    for i in range(n):
        if skip_next:
            skip_next = False
            continue

        line = lines[i]
        next_line = lines[i + 1] if i + 1 < n else ""
        logger.log(logging.DEBUG, f"Parsing line {i + 1}: {line}")

        # Skip empty lines
        if line == "---" or line == "":
            if len(changes) > 0:
                pokemon_id = format_id(curr_pokemon)
                pokemon_data = json.loads(load(POKEMON_INPUT_PATH + pokemon_id + ".json", logger))
                evolutions = fix_evolutions(pokemon_data["evolutions"], pokemon_id, changes)
                fix_pokemon(evolutions, pokemon_data["evolutions"], POKEMON_INPUT_PATH, logger)

                changes = []
                curr_pokemon = None
        # Section headers
        elif next_line.startswith("---"):
            md += f"---\n\n## {line}\n\n"
        # Pokemon headers
        elif line.startswith("#"):
            num, curr_pokemon = line.split(" ", 1)
            pokemon_id = format_id(curr_pokemon)
            md += f"### [{num} {curr_pokemon}](../pokemon/{pokemon_id}.md)\n\n"
        # List changes
        elif line.startswith("- "):
            line = line[2:]
            if len(changes) > 0:
                pokemon, change = line.split(" - ")
                md += f"1. [{pokemon}](../pokemon/{format_id(pokemon)}.md) - {change}\n"
                changes.append(line)
            else:
                md += f"1. {line}\n"

            if not next_line.startswith("- "):
                md += "\n"
        # Changed Pokémon names
        elif line.endswith("For the following Pokémon:"):
            md += line + "\n\n"
            change = line[: -len("For the following Pokémon:") - 1]

            for pokemon in next_line.split(", "):
                pokemon_id = format_id(pokemon)
                md += f"1. [{pokemon}](../pokemon/{pokemon_id}.md)\n"

                pokemon_data = json.loads(load(POKEMON_INPUT_PATH + pokemon_id + ".json", logger))
                evolutions = fix_evolutions(pokemon_data["evolutions"], pokemon_id, [change])
                fix_pokemon(evolutions, pokemon_data["evolutions"], POKEMON_INPUT_PATH, logger)
            md += "\n"
            skip_next = True
        # Change description
        elif line.startswith("Change"):
            md += line + "\n\n"
            changes.append(line)
        # Miscellaneous lines
        else:
            md += line + "\n\n"
    logger.log(logging.INFO, "Data parsed successfully!")

    save(OUTPUT_PATH + "evolution_changes.md", md, logger)


if __name__ == "__main__":
    main()
