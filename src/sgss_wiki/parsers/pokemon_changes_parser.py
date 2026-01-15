"""
Parser for Pokemon Changes documentation file.

This parser:
1. Reads data/documentation/Pokemon Changes.txt
2. Updates pokemon data in data/pokedb/parsed/
3. Generates a markdown file to docs/pokemon_changes.md
"""

import re

from rom_wiki_core.parsers.base_parser import BaseParser
from rom_wiki_core.utils.core.loader import PokeDBLoader
from rom_wiki_core.utils.formatters.markdown_formatter import (
    format_ability,
    format_item,
    format_move,
    format_pokemon_card_grid,
)
from rom_wiki_core.utils.services.evolution_service import EvolutionService
from rom_wiki_core.utils.text.text_util import format_display_name


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

    def parse_general_notes(self, line: str) -> None:
        """Parse a line from the General Notes section.

        Args:
            line (str): A line from the General Notes section.
        """
        self.parse_default(line)

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
                ability, slot = value.rsplit(" ", 1) if "{" in value else (value, "")
                markdown += format_ability(ability)
                if slot:
                    markdown += f" {slot}"
            elif attribute == "Level Up Moves":
                move, level = value.rsplit(" ", 1)
                markdown += f"{format_move(move)} {level}"
            elif attribute == "Stat Change":
                stat, change = value.rsplit(" ", 1)
                markdown += f"{stat} {change}"
            elif attribute == "Base Experience":
                old_exp, new_exp = value.split(" >> ")
                markdown = markdown.rstrip() + "\n\n"
                markdown += f"- **Old EXP**: {old_exp}\n"
                markdown += f"- **New EXP**: {new_exp}\n"
            elif attribute == "TM" and (
                match := re.search(r"((?:TM|HM)\d+) \((.+?)\)", value)
            ):
                item, move = match.groups()
                markdown += (
                    f"Compatibility with {format_item(item)} ({format_move(move)})."
                )
            elif attribute == "Type Change":
                old_type, new_type = value.split(" >> ")
                markdown = markdown.rstrip() + "\n\n"
                markdown += f"- **Old Type**: {old_type}\n"
                markdown += f"- **New Type**: {new_type}\n"
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
            else:
                self.logger.warning(
                    f"Unknown attribute '{attribute}' for value '{value}'."
                )

            markdown += "\n"

        markdown = "\n".join(f"\t{s}" if s else "" for s in markdown.split("\n")) + "\n"
        return markdown
