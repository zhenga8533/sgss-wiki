from dotenv import load_dotenv
from util.ability import get_ability
from util.file import download_file, load, save
from util.format import find_pokemon_sprite, find_trainer_sprite, format_id
from util.item import get_item
from util.logger import Logger
from util.move import get_move
import json
import logging
import os
import re


def parse_pokemon_set(line: str) -> str:
    """
    Parse a Pokémon set from the specified line.

    :param line: The line to parse.
    :return: The parsed Pokémon set.
    """

    # Parse the line data
    strs = [s.strip() for s in line.rstrip("(!)").split("/")]
    name, level, item = re.match(r"(.+) \(Lv\. (\d+)\) @ (.+)", strs[0]).groups()
    ability = strs[1]
    moves = strs[2].split(", ")
    moves = [moves[i] if len(moves) > i else "—" for i in range(4)]

    # Generate the Pokemon set
    pokemon = f"<b><a href='/sgss-wiki/pokemon/{format_id(name)}/'>{name}</a></b> @ {item}\n"
    pokemon += f"<b>Ability:</b> {ability}\n"
    pokemon += f"<b>Level:</b> {level}\n"
    pokemon += "<b>Moves:</b>\n"
    pokemon += "\n".join([f"{i}. {move}" for i, move in enumerate(moves, 1)])

    return pokemon + "<br><br>"


def parse_pokemon_table(line: str, logger: Logger) -> str:
    """
    Parse a Pokémon table from the specified line.

    :param line: The line to parse.
    :param logger: The logger to use.
    :return: The parsed Pokémon table.
    """

    # Parse the line data
    strs = [s.strip() for s in line.rstrip("(!)").split("/")]
    name, level, item = re.match(r"(.+) \(Lv\. (\d+)\) @ (.+)", strs[0]).groups()
    ability = strs[1]
    moves = strs[2].split(", ")
    moves = [moves[i] if len(moves) > i else "—" for i in range(4)]

    # Load pokemon data
    POKEMON_INPUT_PATH = os.getenv("POKEMON_INPUT_PATH")
    pokemon_id = format_id(name)
    pokemon_data = json.loads(load(POKEMON_INPUT_PATH + pokemon_id + ".json", logger))
    pokemon_types = pokemon_data["types"]

    # Load item data
    if item != "None":
        item_data = get_item(item)
        item_effect = (
            item_data["flavor_text_entries"].get("heartgold-soulsilver", item_data["effect"]).replace("\n", " ")
        )
        item_path = f"../docs/assets/items/{format_id(item, symbol='_')}.png"
        if not os.path.exists(item_path):
            download_file(item_path, item_data["sprite"], logger)

    # Load ability data
    ability_data = get_ability(ability)
    ability_effect = (
        ability_data["flavor_text_entries"].get("heartgold-soulsilver", ability_data["effect"]).replace("\n", " ")
    )

    # Generate the Pokemon table
    sprite = find_pokemon_sprite(name, "front", logger).replace("../", "../../")
    table = f"| " + sprite
    # table += f"| **Lv. {level}** [{name}](../../pokemon/{pokemon_id}.md/)<br>"
    table += f" | **Lv. {level}** {name}<br>"
    table += f'**Ability:** <span class="tooltip" title="{ability_effect}">{ability}</span><br>'
    table += " ".join(f'![{t}](../../assets/types/{t}.png "{t.title()}")' for t in pokemon_types)
    table += (
        f' | ![{item}]({item_path.replace("docs", "..")} "{item}")<br><span class="tooltip" title="{item_effect}">{item}</span> | '
        if item != "None"
        else " | None | "
    )

    # Load move data
    for i, move in enumerate(moves, 1):
        if move == "—":
            table += f"{i}. {move}<br>"
            continue

        move_data = get_move(move)
        move_effect = move_data["effect"]
        move_text = move_data["flavor_text_entries"].get("heartgold-soulsilver", move_effect).replace("\n", " ")
        table += f'{i}. <span class="tooltip" title="{move_text}">{move}</span><br>'
    table = table[:-4] + " |\n"

    return table


def parse_trainer_roster(trainers: list, logger: Logger) -> tuple:
    """
    Parse the trainer roster from the specified list of trainers.

    :param trainers: The list of trainers to parse.
    :param logger: The logger to use.
    :return: The parsed markdown and roster.
    """

    md = ""
    trainer_rosters = "| Trainer | P1 | P2 | P3 | P4 | P5 | P6 |\n"
    trainer_rosters += "|:-------:|:--:|:--:|:--:|:--:|:--:|:--:|\n"

    # Parse each trainer
    for trainer in trainers:
        trainer_name, pokemon = re.split(r"\s{2,}", trainer)
        trainer_sprite = find_trainer_sprite(trainer_name, "trainers", logger).replace("../", "../../")

        md += f"1. {trainer_name}"
        trainer_name = trainer_name.replace("(!)", "[(!)](#rematches)")
        trainer_rosters += f"| {trainer_sprite}<br>{trainer_name} "

        # Parse each Pokemon in team
        for i, p in enumerate(pokemon.split(", "), 1):
            pokemon_name, level = p.split(" Lv. ")
            pokemon_id = format_id(pokemon_name)
            pokemon_sprite = find_pokemon_sprite(pokemon_name, "front", logger).replace("../", "../../")

            pokemon_link = f"../pokemon/{pokemon_id}.md/"
            # md += f"\n\t{i}. Lv. {level} [{pokemon_name}]({pokemon_link})"
            md += f"\n\t{i}. Lv. {level} {pokemon_name}"
            # trainer_rosters += f"| {pokemon_sprite}<br>[{pokemon_name}](../{pokemon_link})<br>Lv. {level} "
            trainer_rosters += f"| {pokemon_sprite}<br>{pokemon_name}<br>Lv. {level} "
        md += "\n"
        trainer_rosters += "|\n"
    md += "\n"

    return md, trainer_rosters


def parse_trainers(trainers: list, rematches: list, important: dict, logger: Logger) -> tuple:
    """
    Parse the trainers from the specified data.

    :param trainers: The list of trainers to parse.
    :param rematches: The list of rematch trainers to parse.
    :param important: The list of important trainers to parse.
    :param logger: The logger to use.
    :return: The parsed markdown and roster.
    """

    trainers = [t for t in trainers if re.split(r"\s{2,}", t)[0] not in important]
    md = ""
    trainer_rosters = ""
    important_trainers = ""

    # Parse each trainer type
    if len(trainers) > 0:
        trainer_md, trainer_rosters = parse_trainer_roster(trainers, logger)
        md += "<h3>Generic Trainers</h3>\n\n" + trainer_md
        trainer_rosters = "\n### Generic Trainers\n\n" + trainer_rosters + "\n"

    if len(rematches) > 0:
        trainer_md, rematch_rosters = parse_trainer_roster(rematches, logger)
        md += "<h3>Rematches</h3>\n\n" + trainer_md
        trainer_rosters += "\n### Rematches\n\n" + rematch_rosters + "\n"

    if len(important) > 0:
        md += "<h3>Important Trainers</h3>\n\n"
        trainer_rosters += "\n### Important Trainers\n\n"
        table_head = f"| Pokémon | Attributes | Item | Moves |\n"
        table_head += "|:-------:|------------|:----:|-------|\n"
        curr_trainer = None

        # Seperate important trainers with different rosters
        for trainer in important:
            trainer_sprite = find_trainer_sprite(trainer, "trainers", logger)
            pokemon = important[trainer]

            # Generate trainer markdown
            md += f"**{trainer}**\n\n{trainer_sprite}\n\n"
            trainer_rosters += f"1. [{trainer}](important_trainers.md#{format_id(trainer)})\n"
            trainer_sprite = trainer_sprite.replace("../", "../../")
            important_trainers += f"### {trainer}\n\n{trainer_sprite}\n\n"

            # Initialize variables
            base = ""
            rivals = ["", "", ""]
            rival_index = 0

            wild = ""
            important_rivals = ["", "", ""]

            # Parse each roster into corresponding category
            for line in pokemon:
                if line.endswith("(!)"):
                    rivals[rival_index] += parse_pokemon_set(line)
                    important_rivals[rival_index] += parse_pokemon_table(line, logger)
                    rival_index = (rival_index + 1) % 3
                else:
                    base += parse_pokemon_set(line)
                    wild += parse_pokemon_table(line, logger)

            # Generate markdown for each roster
            important_head = ""
            if curr_trainer != trainer:
                important_head = table_head
                curr_trainer = trainer

            if rivals[0] != "":
                for i, starter in enumerate(["Totodile", "Chikorita", "Cyndaquil"]):
                    md += f'=== "{starter}"\n\n\t'
                    md += "\n\t".join(f"<pre><code>{(rivals[i] + base)[:-8]}</code></pre>".split("\n"))
                    md += "\n\n"

                    important_trainers += f'=== "{starter}"\n\n\t'
                    important_trainers += important_head.replace("\n", "\n\t")
                    important_trainers += "\n\t".join((wild + important_rivals[i]).split("\n"))
                    important_trainers += "\n"
            else:
                md += f"<pre><code>{base[:-8]}</code></pre>\n\n"
                important_trainers += important_head + wild + "\n\n"

    return md, trainer_rosters, important_trainers


def update_markdown(
    location: str,
    section: str,
    trainers: list,
    rematches: list,
    important: dict,
    wild_rosters: dict,
    wild_trainers: dict,
    logger: Logger,
) -> str:
    """
    Update the markdown with the current data.

    :param location: The current location.
    :param section: The current section.
    :param trainers: The list of trainers.
    :param rematches: The list of rematch trainers.
    :param important: The list of important trainers.
    :param wild_rosters: The wild rosters dictionary.
    :param wild_trainers: The wild trainers dictionary.
    :param logger: The logger to use.
    :return: The updated markdown to add.
    """

    if len(trainers) == 0:
        trainers = rematches
        rematches = []
    roster_md, trainer_rosters, important_trainers = parse_trainers(trainers, rematches, important, logger)
    md = roster_md

    if trainer_rosters != "":
        wild_rosters[location] = wild_rosters.get(location, f"# {location} — Trainer Rosters\n")
        wild_rosters[location] += f"\n---\n\n## {section[:-1]}\n\n" if section else ""
        wild_rosters[location] += trainer_rosters
    if important_trainers != "":
        wild_trainers[location] = wild_trainers.get(location, f"# {location} — Important Trainers\n\n")
        wild_trainers[location] += f"\n---\n\n## {section[:-1]}\n\n" if section else ""
        wild_trainers[location] += important_trainers

    return md


def main():
    """
    Main function for parsing the trainer Pokémon data.

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
    logger = Logger("Trainer Pokemon Parser", LOG_PATH + "trainer_pokemon.log", LOG)

    # Read input data
    data = load(INPUT_PATH + "Trainer Pokemon.txt", logger)
    lines = data.split("\n")
    n = len(lines)
    md = "# Trainer Pokémon\n\n"
    md += "!!! tip\n\n\t"
    md += "For a more comprehensive list of trainers, please refer to the [Wild Encounters](../wild_encounters/route_46/trainer_rosters.md) page."
    md += "\n\n"

    trainer = None
    trainers = []
    rematches = []
    important = {}

    wild_rosters = {}
    wild_trainers = {}
    location = None
    section = None

    # Parse data
    logger.log(logging.INFO, "Parsing data...")
    for i in range(n):
        line = lines[i].strip()
        next_line = lines[i + 1].strip() if i + 1 < n else ""
        logger.log(logging.DEBUG, f"Parsing line {i + 1}: {line}")

        # Skip empty lines
        if line.startswith("=") or line == "":
            pass
        # Section headers
        elif next_line.startswith("="):
            if len(trainers) > 0 or len(rematches) > 0:
                md += update_markdown(
                    location, section, trainers, rematches, important, wild_rosters, wild_trainers, logger
                )
                trainers = []
                rematches = []
                important = {}
            location, section = line.split(" (", 1) if "(" in line else (line, None)
            md += f"\n---\n\n## {line}\n\n"
        # List trainers
        elif line.startswith("- "):
            md += f"1. {line[2:]}\n"
        # Trainer rematches
        elif line == "Rematches":
            trainers = rematches
            rematches = []
        # Important trainer pokemon
        elif "@" in line:
            important[trainer].append(line)
        # Important trainer header
        elif "@" in next_line:
            trainer = line
            important[trainer] = []
        # Generic trainer pokemon
        elif "Lv." in line:
            rematches.append(line)
        # Note
        elif line.startswith("Note:"):
            md += f"!!! note\n\n\t{line[6:]}\n\n"
    md += update_markdown(location, section, trainers, rematches, important, wild_rosters, wild_trainers, logger)
    logger.log(logging.INFO, "Data parsed successfully!")

    save(OUTPUT_PATH + "trainer_pokemon.md", md, logger)

    # Save wild encounter navigation
    roster_nav = "  - Wild Encounters:\n"
    trainer_nav = "  - Wild Encounters:\n"
    for location, trainers in wild_rosters.items():
        location_id = format_id(location, symbol="_")
        save(WILD_ENCOUNTER_PATH + location_id + "/trainer_rosters.md", trainers, logger)
        roster_nav += f"      - {location}:\n"
        roster_nav += f"          - Trainer Rosters: {WILD_ENCOUNTER_PATH + location_id}/trainer_rosters.md\n"
    for location, trainers in wild_trainers.items():
        location_id = format_id(location, symbol="_")
        save(WILD_ENCOUNTER_PATH + location_id + "/important_trainers.md", trainers, logger)
        trainer_nav += f"      - {location}:\n"
        trainer_nav += f"          - Important Trainers: {WILD_ENCOUNTER_PATH + location_id}/important_trainers.md\n"
    save(NAV_OUTPUT_PATH + "roster_nav.yml", roster_nav, logger)
    save(NAV_OUTPUT_PATH + "trainer_nav.yml", trainer_nav, logger)


if __name__ == "__main__":
    main()
