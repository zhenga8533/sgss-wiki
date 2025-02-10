from dotenv import load_dotenv
from util.file import load, save
from util.format import find_pokemon_sprite, format_id
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
    NAV_OUTPUT_PATH = os.getenv("NAV_OUTPUT_PATH")
    WILD_ENCOUNTER_PATH = os.getenv("WILD_ENCOUNTER_PATH")

    LOG = os.getenv("LOG") == "True"
    LOG_PATH = os.getenv("LOG_PATH")
    logger = Logger("Pokemon Locations Parser", LOG_PATH + "pokemon_locations.log", LOG)

    # Read input data
    data = load(INPUT_PATH + "Pokemon Locations.txt", logger)
    lines = data.split("\n")
    n = len(lines)
    md = "# Pokémon Locations\n\n"
    md += "!!! tip\n\n\t"
    md += "For a more comprehensive list of wild Pokémon encounters, please refer to the [Wild Encounters](../wild_encounters/new_bark_town/wild_pokemon.md) page."
    md += "\n\n"

    # Wild Encounter data
    curr_location = None
    encounter = None
    level = None
    wild_encounters = {}

    rod_levels = {
        "Old Rod": "10",
        "Good Rod": "25",
        "Super Rod": "50",
    }

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
            if line.startswith("["):
                md += "### "
                wild_encounters[curr_location] += f"---\n\n## {encounter}\n\n"
            else:
                md += "---\n\n## "
                curr_location = line
                wild_encounters[curr_location] = f"# {curr_location} — Wild Pokémon\n\n"
            md += line + "\n\n"
        # Wild Pokemon Levels
        elif line.startswith("Wild Levels:"):
            md += line + "\n\n"
            level = line.split(": ")[1]
        # List changes
        elif line.startswith("- "):
            md += f"1. {line[2:]}\n"
            if not next_line.startswith("- "):
                md += "\n"
        # Encounter type header
        elif line.endswith(":"):
            md += f"**{line}**\n\n"
            if curr_location in wild_encounters:
                encounter = line.rstrip(":")
                wild_encounters[curr_location] += f"### {encounter}\n\n"
                wild_encounters[curr_location] += "| Sprite | Pokémon | Encounter Type | Level | Chance |\n"
                wild_encounters[curr_location] += "|:------:|---------|:--------------:|-------|--------|\n"
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
            pokemon = line.split(", ")
            for j, p in enumerate(pokemon):
                # Format pokemon name
                if " (" in p:
                    name, chance = p.split(" (")
                    chance = chance[:-1]
                else:
                    name = p
                    chance = str(100 // len(pokemon)) + "%" if " [" not in name else "100%"
                if " [" in name:
                    name = name.split(" [")[0]
                sprite = find_pokemon_sprite(name, "front", logger).replace("../", "../../")
                pokemon_id = format_id(name)

                # Format encounters
                encounters = [sub_e for e in encounter.split(", ") for sub_e in e.split(" / ")]
                encounter_sprites = " ".join(
                    [
                        f'![{e}](../../assets/encounter_types/{format_id(e, symbol="_")}.png "{e}"){{: style="max-width: 24px;"" }}'
                        for e in encounters
                    ]
                )

                # Add pokemon to markdown
                md += f"{j + 1}. <a href='/sgss-wiki/pokemon/{pokemon_id}.md/'>{name}</a> ({chance})\n"
                wild_encounters[curr_location] += f"| {sprite} "
                wild_encounters[curr_location] += f"| [{name}](../../pokemon/{pokemon_id}.md) "
                wild_encounters[curr_location] += f"| {encounter_sprites}"
                wild_encounters[curr_location] += f"| {rod_levels[encounter] if encounter in rod_levels else level} "
                wild_encounters[curr_location] += f"| {chance} |\n"
            md += "</code></pre>\n\n"
            wild_encounters[curr_location] += "\n"
        # Miscellaneous lines
        else:
            md += line + "\n\n"

        i += 1
    logger.log(logging.INFO, "Data parsed successfully!")

    save(OUTPUT_PATH + "pokemon_locations.md", md, logger)

    # Save wild encounters navigation
    nav = "  - Wild Encounters:\n"
    for location, encounters in wild_encounters.items():
        location_id = format_id(location, symbol="_")
        save(WILD_ENCOUNTER_PATH + location_id + "/wild_pokemon.md", encounters, logger)
        nav += f"      - {location}:\n"
        nav += f"          - Wild Pokémon: {WILD_ENCOUNTER_PATH + location_id}/wild_pokemon.md\n"
    save(NAV_OUTPUT_PATH + "wild_nav.yml", nav, logger)


if __name__ == "__main__":
    main()
