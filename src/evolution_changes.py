from dotenv import load_dotenv
from util.file import load, save
from util.format import format_id
from util.logger import Logger
import glob
import json
import logging
import os


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
            pass
        # Section headers
        elif next_line.startswith("---"):
            md += f"---\n\n## {line}\n\n"
        # List changes
        elif line.startswith("- "):
            md += f"1. {line[2:]}\n"
            if not next_line.startswith("- "):
                md += "\n"
        # Changed Pokémon names
        elif line.endswith("For the following Pokémon:"):
            md += line + "\n\n"
            md += "\n".join([f"1. {pokemon}" for pokemon in next_line.split(", ")])
            md += "\n\n"
            skip_next = True
        # Miscellaneous lines
        else:
            md += line + "\n\n"
    logger.log(logging.INFO, "Data parsed successfully!")

    save(OUTPUT_PATH + "evolution_changes.md", md, logger)


if __name__ == "__main__":
    main()
