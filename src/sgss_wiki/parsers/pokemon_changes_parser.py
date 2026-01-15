"""
Parser for Pokemon Changes documentation file.

This parser:
1. Reads data/documentation/Pokemon Changes.txt
2. Updates pokemon data in data/pokedb/parsed/
3. Generates a markdown file to docs/pokemon_changes.md
"""

import re

import orjson

from rom_wiki_core.parsers.base_parser import BaseParser
from rom_wiki_core.utils.core.loader import PokeDBLoader
from rom_wiki_core.utils.data.models import PokemonAbility
from rom_wiki_core.utils.formatters.markdown_formatter import (
    format_ability,
    format_item,
    format_move,
    format_pokemon_card_grid,
)
from rom_wiki_core.utils.services.attribute_service import AttributeService
from rom_wiki_core.utils.services.evolution_service import EvolutionService
from rom_wiki_core.utils.services.move_service import MoveService
from rom_wiki_core.utils.services.pokemon_item_service import PokemonItemService
from rom_wiki_core.utils.services.pokemon_move_service import PokemonMoveService
from rom_wiki_core.utils.text.text_util import format_display_name, name_to_id


class PokemonChangesParser(BaseParser):
    """Parser for Pokemon Changes documentation.

    Args:
        BaseParser (_type_): Abstract base parser class
    """

    def __init__(self, input_file: str, output_dir: str = "docs"):
        """Initialize the Pokemon Changes parser.

        Args:
            input_file (str): Path to the input file.
            output_dir (str, optional): Path to the output directory. Defaults to "docs".
        """
        super().__init__(input_file=input_file, output_dir=output_dir)
        self.evolution_service = EvolutionService()
        self._sections = ["General Notes", "Changes"]

        # Changes states
        self._pokemon = []
        self._extra_info = []

        self._current_pokemon = ""
        self._generation = None
        self._change_markdown = ""

        # Data update states (for batched updates)
        self._pending_levelup_moves: list[tuple[int, str]] = []
        self._pending_machine_moves: list[tuple[str, str, str]] = []

    def parse_general_notes(self, line: str) -> None:
        """Parse a line from the General Notes section.

        Args:
            line (str): A line from the General Notes section.
        """
        # Pattern: "- MoveName is a X-power TypeName move..."
        if match := re.match(r"^- (.+?) is a (\d+)-power (.+?) move", line):
            move_name, power, move_type = match.groups()
            MoveService.update_move_attribute(move_name, "power", power)
            MoveService.update_move_attribute(move_name, "type", move_type)
            self.logger.info(f"Updated {move_name}: {power} power, {move_type} type")
        # Pattern: "All Black and White upgrades..."
        elif "black and white upgrades" in line.lower():
            self._apply_gen5_move_upgrades()

        self.parse_default(line)

    def _apply_gen5_move_upgrades(self) -> None:
        """Apply Gen 5 (Black/White) move upgrades to all applicable moves.

        Compares move data between gen4 and gen5 directories and applies
        power/accuracy/pp changes where gen5 values differ.
        """
        data_dir = PokeDBLoader.get_data_dir()
        gen4_move_dir = data_dir.parent / "gen4" / "move"
        gen5_move_dir = data_dir.parent / "gen5" / "move"

        if not gen4_move_dir.exists() or not gen5_move_dir.exists():
            self.logger.warning("Gen4 or Gen5 move directories not found")
            return

        # Version group keys for comparison
        gen4_key = "heartgold_soulsilver"
        gen5_key = "black_white"

        updated_count = 0

        # Iterate through all gen4 moves and compare with gen5
        for gen4_file in gen4_move_dir.glob("*.json"):
            move_id = gen4_file.stem
            gen5_file = gen5_move_dir / f"{move_id}.json"

            if not gen5_file.exists():
                continue

            try:
                with open(gen4_file, "rb") as f:
                    gen4_data = orjson.loads(f.read())
                with open(gen5_file, "rb") as f:
                    gen5_data = orjson.loads(f.read())
            except (OSError, IOError, ValueError) as e:
                self.logger.debug(f"Error loading move {move_id}: {e}")
                continue

            # Compare and update power, accuracy, pp
            move_updated = False
            for attr in ["power", "accuracy", "pp"]:
                gen4_value = gen4_data.get(attr, {}).get(gen4_key)
                gen5_value = gen5_data.get(attr, {}).get(gen5_key)

                # Skip if either value is None or they're the same
                if gen5_value is None or gen4_value == gen5_value:
                    continue

                # Apply the Gen 5 upgrade
                new_val = str(gen5_value) if gen5_value is not None else "Never"
                if MoveService.update_move_attribute(move_id, attr, new_val):
                    self.logger.debug(
                        f"Updated {move_id} {attr}: {gen4_value} -> {gen5_value}"
                    )
                    move_updated = True

            if move_updated:
                updated_count += 1

        self.logger.info(f"Applied Gen 5 upgrades to {updated_count} moves")

    def parse_changes(self, line: str) -> None:
        """Parse a line from the Changes section.

        Args:
            line (str): A line from the Changes section.
        """
        if match := re.match(r"^#\d+ (.+?)$", line):
            self._parse_change()
            self._current_pokemon = match.group(1)

            # Compare generation
            data = PokeDBLoader.load_pokemon(self._current_pokemon)
            if data is None:
                self.logger.warning(
                    f"Pokemon '{self._current_pokemon}' not found in PokeDB."
                )
                return
            generation = data.generation
            if generation != self._generation:
                self._parse_change(is_section_end=True)
                self._generation = generation
                self._markdown += f"\n### {format_display_name(generation)}\n\n"

            self._change_markdown = f'??? note "{self._current_pokemon} Changes"\n\n'
            self._pokemon.append(self._current_pokemon)
        elif line.startswith("+ "):
            attribute, change = line[2:].split(": ", 1)
            self._change_markdown += self._format_attribute(attribute, change)
        else:
            self._parse_change(is_section_end=True)
            self.parse_default(line)

    def _parse_change(self, is_section_end: bool = False) -> None:
        """Parse the current change and append to markdown.

        Args:
            is_section_end (bool, optional): Indicates if this is the end of a section. Defaults to False.
        """
        if not self._current_pokemon:
            return

        # Flush pending move updates for the current Pokemon
        self._flush_pending_updates()

        # Append change markdown
        if self._change_markdown:
            self._extra_info.append(self._change_markdown)
            self._change_markdown = ""

        # Append pokemon card grid at section end
        if is_section_end:
            self._markdown += format_pokemon_card_grid(
                self._pokemon,
                relative_path="../pokedex/pokemon",
                extra_info=self._extra_info,
            )
            self._markdown += "\n\n"

            self._pokemon = []
            self._extra_info = []

    def _flush_pending_updates(self) -> None:
        """Flush pending batched updates for the current Pokemon.

        This is called when moving to the next Pokemon to ensure all pending
        move updates are saved.
        """
        if not self._current_pokemon:
            return

        # Flush pending level-up moves
        if self._pending_levelup_moves:
            PokemonMoveService.update_levelup_moves(
                self._current_pokemon, self._pending_levelup_moves
            )
            self._pending_levelup_moves = []

        # Flush pending machine moves (TM/HM)
        if self._pending_machine_moves:
            PokemonMoveService.update_machine_moves(
                self._current_pokemon, self._pending_machine_moves
            )
            self._pending_machine_moves = []

    def _update_ability_slot(self, ability_name: str, slot: int | None) -> None:
        """Update a specific ability slot for the current Pokemon.

        Args:
            ability_name (str): The ability name to set.
            slot (int | None): The slot number (1, 2, or 3) to update, or None to add.
        """
        pokemon_id = name_to_id(self._current_pokemon)
        pokemon_data = PokeDBLoader.load_pokemon(pokemon_id)
        if pokemon_data is None:
            self.logger.warning(
                f"Could not load Pokemon '{self._current_pokemon}' for ability update"
            )
            return

        ability_id = name_to_id(ability_name)

        # Check if ability already exists (idempotency check)
        for ability in pokemon_data.abilities:
            if ability.name == ability_id:
                # Ability already exists
                if slot is None or ability.slot == slot:
                    # Same ability in same/any slot - no change needed
                    return
                # Different slot specified - will update below

        # Find and update the specific slot, or add new ability
        if slot is not None:
            # Update specific slot
            found = False
            for i, ability in enumerate(pokemon_data.abilities):
                if ability.slot == slot:
                    # Check if already the same ability (idempotency)
                    if ability.name == ability_id:
                        return
                    # Update this slot with new PokemonAbility
                    is_hidden = slot == 3  # Slot 3 is typically hidden ability
                    pokemon_data.abilities[i] = PokemonAbility(
                        name=ability_id, is_hidden=is_hidden, slot=slot
                    )
                    found = True
                    break

            if not found:
                # Slot doesn't exist, add it
                is_hidden = slot == 3
                pokemon_data.abilities.append(
                    PokemonAbility(name=ability_id, is_hidden=is_hidden, slot=slot)
                )
        else:
            # No slot specified - find the next available slot (1, 2, or 3)
            existing_slots = {ability.slot for ability in pokemon_data.abilities}
            next_slot = None
            for s in [1, 2, 3]:
                if s not in existing_slots:
                    next_slot = s
                    break

            if next_slot is None:
                # All slots occupied - default to updating slot 3 (hidden)
                next_slot = 3
                for i, ability in enumerate(pokemon_data.abilities):
                    if ability.slot == 3:
                        if ability.name == ability_id:
                            return  # Already same ability
                        pokemon_data.abilities[i] = PokemonAbility(
                            name=ability_id, is_hidden=True, slot=3
                        )
                        break
            else:
                # Add to next available slot
                is_hidden = next_slot == 3
                pokemon_data.abilities.append(
                    PokemonAbility(name=ability_id, is_hidden=is_hidden, slot=next_slot)
                )

        # Save updated Pokemon data
        PokeDBLoader.save_pokemon(pokemon_id, pokemon_data)
        slot_str = f" (slot {slot})" if slot else ""
        self.logger.info(f"Updated ability{slot_str} for '{self._current_pokemon}': {ability_name}")

    def _apply_stat_change(self, stat_name: str, new_value: int) -> None:
        """Apply an absolute stat change to the current Pokemon.

        Args:
            stat_name (str): The stat name (e.g., "HP", "Attack", "Defense", "Special Attack", etc.).
            new_value (int): The new absolute stat value.
        """
        # Map stat display names to Stats attribute names
        stat_map = {
            "HP": "hp",
            "Attack": "attack",
            "Defense": "defense",
            "Special Attack": "special_attack",
            "Special Defense": "special_defense",
            "Speed": "speed",
            # Short forms
            "Atk": "attack",
            "Def": "defense",
            "SAtk": "special_attack",
            "SDef": "special_defense",
            "Spd": "speed",
        }

        if stat_name not in stat_map:
            self.logger.warning(f"Unknown stat '{stat_name}' for Pokemon '{self._current_pokemon}'")
            return

        # Load current Pokemon data
        pokemon_id = name_to_id(self._current_pokemon)
        pokemon_data = PokeDBLoader.load_pokemon(pokemon_id)
        if pokemon_data is None:
            self.logger.warning(f"Could not load Pokemon '{self._current_pokemon}' for stat change")
            return

        attr_name = stat_map[stat_name]
        current_value = getattr(pokemon_data.stats, attr_name)
        setattr(pokemon_data.stats, attr_name, new_value)

        # Save updated Pokemon data
        PokeDBLoader.save_pokemon(pokemon_id, pokemon_data)
        self.logger.info(
            f"Updated {stat_name} for '{self._current_pokemon}': {current_value} -> {new_value}"
        )

    def _format_attribute(self, attribute: str, change: str) -> str:
        """Format an attribute for markdown output.

        Args:
            attribute (str): The attribute name.
            change (str): The attribute change.
        Returns:
            str: Formatted attribute string.
        """

        markdown = f"**{attribute}**:"
        if "secret" in change:
            markdown = f"\t{markdown + change}\n\n"
            return markdown

        values = re.split(r",\s+| and ", change)
        if len(values) > 1:
            markdown += "\n\n"

        for value in values:
            markdown += "- " if len(values) > 1 else " "

            if attribute == "Ability":
                # Parse ability notation: "Hydration {1}" means Hydration replaces slot 1
                # {} = Replaces Original slot
                ability_match = re.match(r"^(.+?)\s*\{(\d+)\}$", value)
                if ability_match:
                    ability = ability_match.group(1).strip()
                    slot = int(ability_match.group(2))
                    slot_display = f"{{{slot}}}"
                else:
                    ability = value.strip()
                    slot = None
                    slot_display = ""

                markdown += format_ability(ability)
                if slot_display:
                    markdown += f" {slot_display}"

                # Update Pokemon data - update specific ability slot
                self._update_ability_slot(ability, slot)
            elif attribute == "Level Up Moves":
                # Parse level-up move notation:
                # (N) = New move at level N, e.g., "Metal Claw (13)"
                # [N] = Shift from original position to level N, e.g., "Gust [1]"
                # {N} = Replace original at level N, e.g., "Bug Bite {11}"
                # [{N}] = Shift and replace at level N, e.g., "Crunch [{17}]"
                # Pattern matches: Name (N), Name [N], Name {N}, Name [{N}]
                move_match = re.match(r"^(.+?)\s*(\(\d+\)|\[\d+\]|\{\d+\}|\[\{\d+\}\])$", value)
                if move_match:
                    move = move_match.group(1).strip()
                    level_notation = move_match.group(2)
                    # Extract level number from any notation
                    level_search = re.search(r"(\d+)", level_notation)
                    level_num = int(level_search.group(1)) if level_search else 0
                else:
                    # Fallback: try simple split for edge cases
                    parts = value.rsplit(" ", 1)
                    if len(parts) == 2:
                        move, level_notation = parts
                        level_match = re.search(r"(\d+)", level_notation)
                        level_num = int(level_match.group(1)) if level_match else 0
                    else:
                        move = value
                        level_notation = ""
                        level_num = 0

                markdown += f"{format_move(move)} {level_notation}"
                # Collect for batched update
                self._pending_levelup_moves.append((level_num, move))
            elif attribute == "Stat Change":
                # Parse stat change notation: "StatName (Value)", e.g., "Special Attack (100)"
                # Value is the NEW absolute stat value
                stat_match = re.match(r"^(.+?)\s*\((\d+)\)$", value)
                if stat_match:
                    stat = stat_match.group(1).strip()
                    new_value = int(stat_match.group(2))
                    markdown += f"{stat} ({new_value})"
                    # Apply absolute stat change to Pokemon data (skip "Total")
                    if stat != "Total":
                        self._apply_stat_change(stat, new_value)
                else:
                    # Fallback for edge cases
                    markdown += value
            elif attribute == "Base Experience":
                old_exp, new_exp = value.split(" >> ")
                markdown = markdown.rstrip() + "\n\n"
                markdown += f"- **Old EXP**: {old_exp}\n"
                markdown += f"- **New EXP**: {new_exp}\n"
                # Update Pokemon data with new base experience
                AttributeService.update_attribute(
                    self._current_pokemon, attribute, new_exp
                )
            elif attribute == "TM" and (
                match := re.search(r"((?:TM|HM)\d+) \((.+?)\)", value)
            ):
                item, move = match.groups()
                markdown += (
                    f"Compatibility with {format_item(item)} ({format_move(move)})."
                )
                # Collect for batched update - parse machine type and number
                machine_type = "TM" if item.startswith("TM") else "HM"
                machine_num = item[2:]  # Get the number part
                self._pending_machine_moves.append((machine_type, machine_num, move))
            elif attribute == "Type Change":
                old_type, new_type = value.split(" >> ")
                markdown = markdown.rstrip() + "\n\n"
                markdown += f"- **Old Type**: {old_type}\n"
                markdown += f"- **New Type**: {new_type}\n"
                # Update Pokemon data with new type (convert "/" to " / " for AttributeService)
                type_value = new_type.replace("/", " / ")
                AttributeService.update_attribute(
                    self._current_pokemon, "Type", type_value
                )
            elif attribute == "Max Experience":
                old_exp, new_exp = value.split(" >> ")
                markdown += f"{old_exp} >> {new_exp}"
            elif attribute == "Item Change" and (
                match := re.match(r"^(.+?) \((\d+)% >> (\d+)%\)$", value)
            ):
                item, old_chance, new_chance = match.groups()
                markdown = markdown.rstrip() + f"{format_item(item)}\n\n"
                markdown += f"- **Old Chance**: {old_chance}%\n"
                markdown += f"- **New Chance**: {new_chance}%"
                # Update Pokemon data with new held item rarity
                PokemonItemService.update_held_item(
                    self._current_pokemon, item, int(new_chance)
                )
            else:
                self.logger.warning(
                    f"Unknown attribute '{attribute}' for value '{value}'."
                )

            markdown += "\n"

        markdown = "\n".join(f"\t{s}" if s else "" for s in markdown.split("\n")) + "\n"
        return markdown
