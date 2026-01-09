"""
Parser for Evolution Changes documentation file.

This parser:
1. Reads data/documentation/Evolution Changes.txt
2. Updates pokemon evolution data in data/pokedb/parsed/
3. Generates a markdown file to docs/evolution_changes.md
"""

import re
from typing import Any, cast

from rom_wiki_core.parsers.base_parser import BaseParser
from rom_wiki_core.utils.core.loader import PokeDBLoader
from rom_wiki_core.utils.data.models import EvolutionChain, EvolutionDetails, Gender
from rom_wiki_core.utils.formatters.markdown_formatter import (
    format_item,
    format_pokemon,
    format_pokemon_card_grid,
)
from rom_wiki_core.utils.services.evolution_service import EvolutionService
from rom_wiki_core.utils.text.text_util import name_to_id, parse_pokemon_forme


class EvolutionChangesParser(BaseParser):
    """Parser for Evolution Changes documentation.

    Args:
        BaseParser (_type_): Abstract base parser class
    """

    def __init__(self, input_file: str, output_dir: str = "docs"):
        """Initialize the Evolution Changes parser.

        Args:
            input_file (str): Path to the input file.
            output_dir (str, optional): Path to the output directory. Defaults to "docs".
        """
        super().__init__(input_file=input_file, output_dir=output_dir)
        self.evolution_service = EvolutionService()
        self._sections = ["General Notes", "Trade Evolutions", "Condition Evolutions"]

        # Trade Evolution states
        self._method_change = None

        # Condition Evolution states
        self._evolutions = []
        self._conditions = []

    def parse_general_notes(self, line: str) -> None:
        """Parse a line from the General Notes section.

        Args:
            line (str): A line from the General Notes section.
        """
        self.parse_default(line)

    def parse_trade_evolutions(self, line: str) -> None:
        """Parse a line from the Trade Evolutions section.

        Args:
            line (str): A line from the Trade Evolutions section.
        """
        # Method change detection
        if "evolutionary stone" in line:
            self._method_change = "use_item"
            self._markdown += "### Use Item\n\n"
            self.parse_default(line)
        elif "Covenant Orb" in line:
            self._method_change = "covenant_orb"
            self._markdown += "### Covenant Orb\n\n"
            self.parse_default(line)
        elif "Voltaic Ore" in line:
            self._method_change = "voltaic_ore"
            self._markdown += "### Voltaic Ore\n\n"
            self.parse_default(line)
        # Pokemon line detection
        elif self._method_change is not None:
            pokemon = line.split(", ")
            self._markdown += "\n"
            self._markdown += format_pokemon_card_grid(
                cast(Any, pokemon), relative_path="../pokedex/pokemon"
            )
            self._markdown += "\n\n"
            self._method_change = None
        # Default
        else:
            self.parse_default(line)

    def parse_condition_evolutions(self, line: str) -> None:
        """Parse a line from the Condition Evolutions section.

        Args:
            line (str): A line from the Condition Evolutions section.
        """
        if match := re.match(r"^#\d+ (.+?)$", line):
            pokemon = match.group(1)
            self._markdown += f"### {pokemon}\n\n"
            self._markdown += format_pokemon_card_grid(
                [pokemon], relative_path="../pokedex/pokemon"
            )
            self._markdown += "\n\n"
        elif line.startswith("- "):
            evolution, condition = line[2:].split(" - ")
            self._evolutions.append(evolution)
            self._conditions.append(condition)
        elif line == "":
            if self._evolutions and self._conditions:
                self._markdown += format_pokemon_card_grid(
                    self._evolutions,
                    relative_path="../pokedex/pokemon",
                    extra_info=self._conditions,
                )
                self._evolutions = []
                self._conditions = []
            self.parse_default(line)
        else:
            self.parse_default(line)
