from dotenv import load_dotenv
from util.file import load, save
from util.format import find_pokemon_sprite, format_id
from util.logger import Logger
import logging
import os


def parse_change(attribute: str, changes: list[str]) -> str:
    md = attribute + ":\n\n```\n+ "
    md += "\n+ ".join(changes.split(", "))
    md += "\n```\n\n"

    return md


def main():
    """
    Main function for the pokemon changes parser.

    :return: None
    """

    # Load environment variables and logger
    load_dotenv()
    INPUT_PATH = os.getenv("INPUT_PATH")
    OUTPUT_PATH = os.getenv("OUTPUT_PATH")

    LOG = os.getenv("LOG") == "True"
    LOG_PATH = os.getenv("LOG_PATH")
    logger = Logger("Pokemon Changes Parser", LOG_PATH + "pokemon_changes.log", LOG)

    # Read input data
    data = load(INPUT_PATH + "Pokemon Changes.txt", logger)
    lines = data.split("\n")
    n = len(lines)
    md = "# Pokémon Changes\n\n"

    regions = ["Kanto", "Johto", "Hoenn", "Sinnoh", "Unova"]
    pokedex_index = [1, 152, 252, 387, 494]
    region_index = 0

    attribute = None

    # Parse all lines in the input data file
    logger.log(logging.INFO, "Parsing data...")
    i = 0
    while i < n:
        line = lines[i]
        next_line = lines[i + 1] if i + 1 < n else ""
        logger.log(logging.DEBUG, f"Parsing line {i + 1}: {line}")

        # Skip empty lines
        if line == "":
            pass
        # Section headers
        elif next_line.startswith("---"):
            md += f"---\n\n## {line}\n\n"
        # List changes
        elif line.startswith("- "):
            md += f"1. {line[2:]}\n"
            if not next_line.startswith("- "):
                md += "\n"
        # Pokemon changes
        elif line.startswith("#"):
            num, pokemon = line.split(" ", 1)
            num = int(num[1:])
            pokemon_id = format_id(pokemon)

            # Set region if Pokemon is from a new region
            if num >= pokedex_index[region_index]:
                md += f"---\n\n## {regions[region_index]}\n\n"
                region_index += 1

            # md += f"**[{line}](../pokemon/{pokemon_id}.md)**\n\n"
            md += f"**{line}**\n\n"
            md += find_pokemon_sprite(pokemon, "front", logger) + "\n\n"
        elif line.startswith("+ "):
            attribute, changes = line[2:].split(": ")

            while not (next_line.startswith("+ ") or next_line.startswith("#") or next_line == ""):
                changes += next_line

                i += 1
                if i + 1 < n:
                    next_line = lines[i + 1]
                else:
                    break

            md += parse_change(attribute, changes)
        # Miscellaneous lines
        else:
            md += line + "\n\n"

        i += 1
    logger.log(logging.INFO, "Data parsed successfully!")

    save(OUTPUT_PATH + "pokemon_changes.md", md, logger)


if __name__ == "__main__":
    main()
