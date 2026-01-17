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
from rom_wiki_core.utils.data.constants import normalize_stat
from rom_wiki_core.utils.data.models import MoveLearn
from rom_wiki_core.utils.formatters.markdown_formatter import (
    format_ability,
    format_item,
    format_move,
    format_pokemon_card_grid,
)
from rom_wiki_core.utils.services.attribute_service import AttributeService
from rom_wiki_core.utils.services.move_service import MoveService
from rom_wiki_core.utils.services.pokemon_item_service import PokemonItemService
from rom_wiki_core.utils.services.pokemon_move_service import PokemonMoveService
from rom_wiki_core.utils.text.text_util import format_display_name, name_to_id

from sgss_wiki.config import CONFIG


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
        self._sections = ["General Notes", "Changes"]

        # Changes states
        self._pokemon = []
        self._extra_info = []

        self._current_pokemon = ""
        self._generation = None
        self._change_markdown = ""

        # Data update states (for batched updates)
        # Level-up moves: (level, move_name, notation_type)
        # notation_type: "new" for (), "replace" for {}, "shift" for [], "shift_replace" for [{}]
        self._pending_levelup_moves: list[tuple[int, str, str]] = []
        self._pending_machine_moves: list[tuple[str, str, str]] = []

    def parse_general_notes(self, line: str) -> None:
        """Parse a line from the General Notes section.

        Args:
            line (str): A line from the General Notes section.
        """
        # Pattern: "- MoveName is a X-power TypeName move..."
        if match := re.match(r"^- (.+?) is a (\d+)-power (.+?) move", line):
            move_name, power, move_type = match.groups()
            move_id = name_to_id(move_name)
            MoveService.update_move_power(move_id, int(power))
            MoveService.update_move_type(move_id, name_to_id(move_type))
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

                # Apply the Gen 5 upgrade using specific methods
                updated = False
                if attr == "power":
                    updated = MoveService.update_move_power(move_id, gen5_value)
                elif attr == "accuracy":
                    updated = MoveService.update_move_accuracy(move_id, gen5_value)
                elif attr == "pp":
                    updated = MoveService.update_move_pp(move_id, gen5_value)

                if updated:
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

        # Flush pending level-up moves by merging with existing moves
        if self._pending_levelup_moves:
            self._merge_and_update_levelup_moves()
            self._pending_levelup_moves = []

        # Flush pending machine moves (TM/HM)
        if self._pending_machine_moves:
            # Extract move names and convert to IDs
            move_ids = [name_to_id(move) for _, _, move in self._pending_machine_moves]
            PokemonMoveService.update_move_category(
                name_to_id(self._current_pokemon), "machine", move_ids
            )
            self._pending_machine_moves = []

    def _merge_and_update_levelup_moves(self) -> None:
        """Merge pending level-up move changes with existing moves and update.

        Instead of replacing all moves, this method:
        1. Loads the Pokemon's existing level-up moves
        2. Applies changes based on notation type:
           - "new" (): Add new move at specified level
           - "replace" {}: Remove move at that level, add new move
           - "shift" []: Move already exists, change its level
           - "shift_replace" [{}]: Change existing move's level, remove move at target level
        3. Saves the merged result
        """
        pokemon_id = name_to_id(self._current_pokemon)
        pokemon_data = PokeDBLoader.load_pokemon(pokemon_id)
        if pokemon_data is None:
            self.logger.warning(
                f"Could not load Pokemon '{self._current_pokemon}' for move update"
            )
            return

        # Build a dict of existing moves: move_id -> level
        existing_moves = {
            move.name: move.level_learned_at for move in pokemon_data.moves.level_up
        }

        # Apply pending changes based on notation type
        for level, move_name, notation_type in self._pending_levelup_moves:
            move_id = name_to_id(move_name)

            if notation_type == "new":
                # () = New move: simply add it at the specified level
                existing_moves[move_id] = level

            elif notation_type == "replace":
                # {} = Replace: remove whatever move was at this level, add new move
                # Find and remove the move that was at this level
                to_remove = [m for m, lvl in existing_moves.items() if lvl == level]
                for m in to_remove:
                    del existing_moves[m]
                existing_moves[move_id] = level

            elif notation_type == "shift":
                # [] = Shift: move already exists, just update its level
                # The move should already be in the list, update its level
                if move_id in existing_moves:
                    existing_moves[move_id] = level
                else:
                    # Move not found, add it anyway (defensive)
                    existing_moves[move_id] = level

            elif notation_type == "shift_replace":
                # [{}] = Shift and replace: move exists, change its level,
                # and remove whatever was at the target level
                # First remove any move at the target level
                to_remove = [m for m, lvl in existing_moves.items() if lvl == level]
                for m in to_remove:
                    del existing_moves[m]
                # Then set the move to the new level
                existing_moves[move_id] = level

        # Convert to list of MoveLearn objects for the service
        merged_moves = [
            MoveLearn(
                name=move_id,
                level_learned_at=level,
                version_groups=[CONFIG.version_group],
            )
            for move_id, level in existing_moves.items()
        ]
        # Sort by level for consistent ordering
        merged_moves.sort(key=lambda x: (x.level_learned_at, x.name))

        # Update with the merged move list
        PokemonMoveService.update_levelup_moves(
            name_to_id(self._current_pokemon), merged_moves
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

                # Update Pokemon data - use AttributeService for proper change tracking
                AttributeService.update_ability_slot(
                    name_to_id(self._current_pokemon), ability, slot
                )
            elif attribute == "Level Up Moves":
                # Parse level-up move notation:
                # (N) = New move at level N, e.g., "Metal Claw (13)"
                # [N] = Shift from original position to level N, e.g., "Gust [1]"
                # {N} = Replace original at level N, e.g., "Bug Bite {11}"
                # [{N}] = Shift and replace at level N, e.g., "Crunch [{17}]"
                # Pattern matches: Name (N), Name [N], Name {N}, Name [{N}]
                move_match = re.match(
                    r"^(.+?)\s*(\(\d+\)|\[\d+\]|\{\d+\}|\[\{\d+\}\])$", value
                )
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

                # Determine notation type
                if "[{" in level_notation:
                    notation_type = "shift_replace"
                elif "{" in level_notation:
                    notation_type = "replace"
                elif "[" in level_notation:
                    notation_type = "shift"
                else:
                    notation_type = "new"

                markdown += f"{format_move(move)} {level_notation}"
                # Collect for batched update with notation type
                self._pending_levelup_moves.append((level_num, move, notation_type))
            elif attribute == "Stat Change":
                # Parse stat change notation: "StatName (Value)", e.g., "Special Attack (100)"
                # Value is the NEW absolute stat value
                stat_match = re.match(r"^(.+?)\s*\((\d+)\)$", value)
                if stat_match:
                    stat_display = stat_match.group(1).strip()
                    new_value = int(stat_match.group(2))
                    markdown += f"{stat_display} ({new_value})"
                    # Normalize display name to canonical slug, then call service (skip "Total")
                    if stat_display != "Total":
                        stat_slug = normalize_stat(stat_display)
                        if stat_slug:
                            AttributeService.update_single_stat(
                                name_to_id(self._current_pokemon), stat_slug, new_value
                            )
                        else:
                            self.logger.warning(
                                f"Unknown stat '{stat_display}' for {self._current_pokemon}"
                            )
                else:
                    # Fallback for edge cases
                    markdown += value
            elif attribute == "Base Experience":
                old_exp, new_exp = value.split(" >> ")
                markdown = markdown.rstrip() + "\n\n"
                markdown += f"- **Old EXP**: {old_exp}\n"
                markdown += f"- **New EXP**: {new_exp}\n"
                # Update Pokemon data with new base experience
                AttributeService.update_base_experience(
                    name_to_id(self._current_pokemon), int(new_exp)
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
                # Update Pokemon data with new type (parse types into list of slugs)
                types_list = [name_to_id(t.strip()) for t in new_type.split("/")]
                AttributeService.update_type(
                    name_to_id(self._current_pokemon), types_list
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
                    name_to_id(self._current_pokemon), name_to_id(item), int(new_chance)
                )
            else:
                self.logger.warning(
                    f"Unknown attribute '{attribute}' for value '{value}'."
                )

            markdown += "\n"

        markdown = "\n".join(f"\t{s}" if s else "" for s in markdown.split("\n")) + "\n"
        return markdown
