from dotenv import load_dotenv
from util.file import load, save
from util.logger import Logger
import logging
import os


def main():
    """
    Main function for the pokemon locations parser.

    :return: None
    """

    # Load environment variables and logger
    load_dotenv()
    INPUT_PATH = os.getenv("INPUT_PATH")
    OUTPUT_PATH = os.getenv("OUTPUT_PATH")

    LOG = os.getenv("LOG") == "True"
    LOG_PATH = os.getenv("LOG_PATH")
    logger = Logger("Pokemon Locations Parser", LOG_PATH + "pokemon_locations.log", LOG)

    # Read input data
    data = load(INPUT_PATH + "Pokemon Locations.txt", logger)
    lines = data.split("\n")
    n = len(lines)
    md = "# Pokémon Locations\n\n"

    # Parse all lines in the input data file
    logger.log(logging.INFO, "Parsing data...")
    i = 0
    while i < n:
        last_line = lines[i - 1] if i > 0 else ""
        line = lines[i]
        next_line = lines[i + 1] if i + 1 < n else ""
        logger.log(logging.DEBUG, f"Parsing line {i + 1}: {line}")

        # Skip empty lines
        if line == "---" or line == "":
            pass
        # Section headers
        elif next_line.startswith("Wild Levels:") or next_line == "---":
            md += "### " if line.startswith("[") else "---\n\n## "
            md += line + "\n\n"
        # List changes
        elif line.startswith("- "):
            md += f"1. {line[2:]}\n"
            if not next_line.startswith("- "):
                md += "\n"
        # Encounter type header
        elif line.endswith(":"):
            md += f"**{line}**\n\n"
        # Pokemon encounter list
        elif "%)" in line or last_line.endswith(":"):
            while not (next_line.endswith(":") or next_line == "" or next_line.startswith("[")):
                line += next_line

                i += 1
                if i + 1 < n:
                    next_line = lines[i + 1]
                else:
                    break

            md += "<pre><code>"
            for j, pokemon in enumerate(line.split(", ")):
                md += f"{j + 1}. {pokemon}\n"
            md += "</code></pre>\n\n"
        # Miscellaneous lines
        else:
            md += line + "\n\n"

        i += 1
    logger.log(logging.INFO, "Data parsed successfully!")

    save(OUTPUT_PATH + "pokemon_locations.md", md, logger)


if __name__ == "__main__":
    main()
