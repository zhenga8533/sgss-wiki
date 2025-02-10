from dotenv import load_dotenv
from util.file import load, save
from util.format import find_pokemon_sprite, format_id
from util.logger import Logger
from util.move import get_move
import json
import logging
import os
import re


def update_move(line: str, move_path: str, logger: Logger) -> None:
    """
    Update move data if the line is a move change

    :param line: The line to parse
    :param move_path: The path to the move data
    :param logger: The logger object
    :return: None
    """

    pattern = r"([A-Z a-z]+) is a ([0-9]+)-power ([A-Za-z]+) move(.*)?."
    if match := re.match(pattern, line):
        logger.log(logging.DEBUG, f"Matched move change: {line}")
        move, power, type_, effect = match.groups()
        move_id = format_id(move)
        move_data = get_move(move_id)
        move_data["power"] = int(power)
        move_data["type"] = type_.lower()
        move_data["effect"] = "Inflicts regular damage." if effect is None else f"Inflicts regular damage,{effect}"
        save(move_path + move_id + ".json", json.dumps(move_data, indent=4), logger)


def parse_change(attribute: str, changes: str, pokemon: str, pokemon_path: str, logger: Logger) -> str:
    # Load Pokemon data
    file_path = pokemon_path + pokemon + ".json"
    data = json.loads(load(file_path, logger))

    md = attribute + ":\n\n```"
    for change in changes.split(", "):
        if attribute == "Ability":
            pass
        elif attribute == "Level Up Moves":
            move, level = change.rsplit(" ", 1)
            level = int(re.sub(r"[\[\]{}()]", "", level))

            move_id = format_id(move)
            moves = data["moves"]["heartgold-soulsilver"]

            # Remove previous move learned at the same level
            level_index = next(
                (i for i, m in enumerate(moves) if m["level_learned_at"] == level),
                None,
            )
            if level_index is not None and level > 1:
                moves.pop(level_index)

            # Remove previous move with the same name
            move_index = next(
                (i for i, m in enumerate(moves) if m["name"] == move_id and m["learn_method"] == "level-up"), None
            )
            if move_index is not None:
                moves.pop(move_index)

            # Add new move
            moves.append({"name": move_id, "learn_method": "level-up", "level_learned_at": level})
        elif attribute == "TM":
            machines = re.findall(r"(TM\d+|HM\d+)", changes)
            moves = re.findall(r"\((.*?)\)", changes)

            for machine, move in zip(machines, moves):
                md += f"\n+ {machine} ({move})"

                move_id = format_id(move)
                moves = data["moves"]["heartgold-soulsilver"]
                move_index = next(
                    (i for i, m in enumerate(moves) if m["name"] == move_id and m["learn_method"] == "machine"), None
                )
                if move_index is None:
                    moves.append({"name": move_id, "learn_method": "machine", "level_learned_at": 0})
            break
        elif attribute == "Stat Change":
            for stat_change in change.split(", "):
                stat, value = stat_change.split(" (")
                stat = format_id(stat)
                value = int(value[:-1])

                stats = data["stats"]
                if stat in stats or stat == "total":
                    stats[stat] = value
                else:
                    logger.log(logging.WARNING, f"Unknown stat: {stat}")
        elif attribute == "Base Experience":
            data["base_experience"] = int(change.split(" >> ")[1])
        elif attribute == "Type Change":
            if " >> " not in change:
                continue
            data["types"] = [t.lower() for t in change.split(" >> ")[1].split(" / ")]
        elif attribute == "Item Rate":
            item, chance = change.split(" (", 1)
            item = format_id(item)
            chance = int(chance.split(" >> ")[1][:-2])

            held_items = data["held_items"]
            held_items[item]["heartgold"] = chance
            held_items[item]["soulsilver"] = chance
        else:
            logger.log(logging.WARNING, f"Unknown attribute: {attribute}")

        md += "\n+ " + change
    md += "\n```\n\n"

    save(file_path, json.dumps(data, indent=4), logger)
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
    MOVE_INPUT_PATH = os.getenv("MOVE_INPUT_PATH")
    POKEMON_INPUT_PATH = os.getenv("POKEMON_INPUT_PATH")

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
    curr_pokemon = None

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
            pokemon_id = format_id(line.split(" ", 1)[1])
            md += f"---\n\n## [{line}](../pokemon/{pokemon_id}.md)\n\n"
        # List changes
        elif line.startswith("- "):
            md += f"1. {line[2:]}\n"
            if not next_line.startswith("- "):
                md += "\n"
            update_move(line[2:], MOVE_INPUT_PATH, logger)
        # Pokemon changes
        elif line.startswith("#"):
            num, pokemon = line.split(" ", 1)
            num = int(num[1:])
            curr_pokemon = format_id(pokemon)

            # Set region if Pokemon is from a new region
            if num >= pokedex_index[region_index]:
                md += f"---\n\n## {regions[region_index]} Pokémon\n\n"
                region_index += 1

            md += f"**[{line}](../pokemon/{curr_pokemon}.md)**\n\n"
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

            md += parse_change(attribute, changes, curr_pokemon, POKEMON_INPUT_PATH, logger)
        # Miscellaneous lines
        else:
            md += line + "\n\n"

        i += 1
    logger.log(logging.INFO, "Data parsed successfully!")

    save(OUTPUT_PATH + "pokemon_changes.md", md, logger)


if __name__ == "__main__":
    main()
