from dotenv import load_dotenv
from util.file import load, save
from util.format import find_pokemon_sprite
from util.logger import Logger
import logging
import os


def main():
    """
    Main function for the special event guide parser.

    :return: None
    """

    # Load environment variables and logger
    load_dotenv()
    INPUT_PATH = os.getenv("INPUT_PATH")
    OUTPUT_PATH = os.getenv("OUTPUT_PATH")

    LOG = os.getenv("LOG") == "True"
    LOG_PATH = os.getenv("LOG_PATH")
    logger = Logger("Special Event Parser", LOG_PATH + "special_event_guide.log", LOG)

    # Read input data
    data = load(INPUT_PATH + "Special Event Guide.txt", logger)
    lines = data.split("\n")
    n = len(lines)
    md = "# Special Event Guide\n\n"

    # Parse all lines in the input data file
    logger.log(logging.INFO, "Parsing data...")
    i = 0
    while i < n:
        line = lines[i]
        next_line = lines[i + 1] if i + 1 < n else ""
        logger.log(logging.DEBUG, f"Parsing line {i + 1}: {line}")

        # Skip empty lines
        if line == "---" or line == "":
            pass
        # Section headers
        elif next_line.startswith("Wild Levels:") or next_line == "---":
            md += f"---\n\n## {line}\n\n"
        # List changes
        elif line.startswith("- "):
            md += f"1. {line[2:]}\n"
            if not next_line.startswith("- "):
                md += "\n"
        # Special Pokemon header
        elif line.startswith("#"):
            md += f"### {line}\n\n"
            pokemon = line.split(", ")
            md += " ".join([find_pokemon_sprite(p.split(" ", 1)[1], "front", logger) for p in pokemon])
            md += "\n\n"
        # Encounter Guide
        elif line == "Guide:":
            guide = ""
            while next_line != "":
                guide += " " + next_line

                i += 1
                if i + 1 < n:
                    next_line = lines[i + 1]
                else:
                    break

            md += "**Guide:**\n\n"
            md += "\n".join([f"{j}. {step.strip()}" for j, step in enumerate(guide.split(". "), 1)])
            md += "\n\n"
        # Subsection headers
        elif line.endswith(":"):
            md += f"**{line}**\n\n"
        # Miscellaneous lines
        else:
            md += line + "\n\n"

        i += 1
    logger.log(logging.INFO, "Data parsed successfully!")

    save(OUTPUT_PATH + "special_event_guide.md", md, logger)


if __name__ == "__main__":
    main()
