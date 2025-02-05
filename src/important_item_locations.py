from dotenv import load_dotenv
from util.file import load, save
from util.logger import Logger
import logging
import os


def main():
    """
    Main function for the important item locations parser.

    :return: None
    """

    # Load environment variables and logger
    load_dotenv()
    INPUT_PATH = os.getenv("INPUT_PATH")
    OUTPUT_PATH = os.getenv("OUTPUT_PATH")

    LOG = os.getenv("LOG") == "True"
    LOG_PATH = os.getenv("LOG_PATH")
    logger = Logger("Important Item Parser", LOG_PATH + "important_item_locations.log", LOG)

    # Read input data
    data = load(INPUT_PATH + "Important Item Locations.txt", logger)
    lines = data.split("\n")
    n = len(lines)
    md = "# Important Item Locations Changes\n\n"

    parse_table = False

    # Parse all lines in the input data file
    logger.log(logging.INFO, "Parsing data...")
    for i in range(n):
        line = lines[i]
        next_line = lines[i + 1] if i + 1 < n else ""
        logger.log(logging.DEBUG, f"Parsing line {i + 1}: {line}")

        # Skip empty lines
        if line == "---" or line == "" or line.startswith("* "):
            if parse_table:
                md += "\n"
                parse_table = False
            if line.startswith("* "):
                md += f"<sub><i>{line}</i></sub>\n\n"
        # Section headers
        elif next_line.startswith("---"):
            md += f"---\n\n## {line}\n\n"
        # List changes
        elif line.startswith("- "):
            md += f"1. {line[2:]}\n"
            if not next_line.startswith("- "):
                md += "\n"
        # Item changes
        elif ": " in line:
            if not parse_table:
                md += "| Item | Location |\n"
                md += "|------|----------|\n"
                parse_table = True

            item, location = line.split(": ")
            md += f"| {item} | {location} |\n"
        # Miscellaneous lines
        else:
            md += line + "\n\n"
    logger.log(logging.INFO, "Data parsed successfully!")

    save(OUTPUT_PATH + "important_item_locations.md", md, logger)


if __name__ == "__main__":
    main()
