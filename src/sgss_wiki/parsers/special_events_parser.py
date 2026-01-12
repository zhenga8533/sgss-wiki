"""
Parser for Special Events documentation file.

This parser:
1. Reads data/documentation/Special Events.txt
2. Generates a markdown file to docs/special_events.md
"""

import re
from typing import Any, cast

from rom_wiki_core.parsers.base_parser import BaseParser
from rom_wiki_core.utils.formatters.markdown_formatter import format_pokemon_card_grid


class SpecialEventsParser(BaseParser):
    """Parser for Special Events documentation.

    Args:
        BaseParser (_type_): Abstract base parser class
    """

    def __init__(self, input_file: str, output_dir: str = "docs"):
        """Initialize the Special Events parser.

        Args:
            input_file (str): Path to the input file.
            output_dir (str, optional): Path to the output directory. Defaults to "docs".
        """
        super().__init__(input_file=input_file, output_dir=output_dir)
        self._sections = [
            "General Notes",
            "Non-Legendary Encounters",
            "Pseudo-Legend Encounters",
            "Gifted Pokémon",
            "Starters",
            "Legendary Pokémon",
            "Final Notes",
        ]

    def parse_general_notes(self, line: str) -> None:
        """Parse a line from the General Notes section.

        Args:
            line (str): A line from the General Notes section.
        """
        self.parse_default(line)

    def parse_non_legendary_encounters(self, line: str) -> None:
        """Parse a line from the Non-Legendary Encounters section.

        Args:
            line (str): A line from the Non-Legendary Encounters section.
        """
        if line.startswith("#"):
            pokemon = line.split(", ")
            pokemon = [p.split(" ", 1)[1] for p in pokemon]

            self._markdown += f"### {', '.join(pokemon)}\n\n"
            self._markdown += format_pokemon_card_grid(
                cast(Any, pokemon), relative_path="../pokedex/pokemon"
            )
            self._markdown += "\n\n"
        elif line.endswith(":"):
            self._markdown += f"**{line}**\n\n"
        else:
            self.parse_default(line)

    def parse_pseudo_legend_encounters(self, line: str) -> None:
        """Parse a line from the Pseudo-Legendary Encounters section.

        Args:
            line (str): A line from the Pseudo-Legendary Encounters section.
        """
        if line.startswith("* "):
            self._markdown += f"### {line[2:]}\n\n"
        elif match := re.match(r"^#\d+ (.+?)$", line):
            pokemon = match.group(1)
            self._markdown += format_pokemon_card_grid(
                [pokemon], relative_path="../pokedex/pokemon"
            )
            self._markdown += "\n\n"
        else:
            self.parse_default(line)

    def parse_gifted_pokemon(self, line: str) -> None:
        """Parse a line from the Gifted Pokémon section.

        Args:
            line (str): A line from the Gifted Pokémon section.
        """
        self.parse_non_legendary_encounters(line)

    def parse_starters(self, line: str) -> None:
        """Parse a line from the Starters section.

        Args:
            line (str): A line from the Starters section.
        """
        self.parse_non_legendary_encounters(line)

    def parse_legendary_pokemon(self, line: str) -> None:
        """Parse a line from the Legendary Pokémon section.

        Args:
            line (str): A line from the Legendary Pokémon section.
        """
        self.parse_non_legendary_encounters(line)

    def parse_final_notes(self, line: str) -> None:
        """Parse a line from the Final Notes section.

        Args:
            line (str): A line from the Final Notes section.
        """
        self.parse_default(line)
