"""
Parser for Pokemon Locations documentation file.

This parser:
1. Reads data/documentation/Pokemon Locations.txt
2. Generates a markdown file to docs/pokemon_locations.md
3. Generates JSON data files to data/locations/ for each location with wild encounter information
"""

import re

from rom_wiki_core.parsers.location_parser import LocationParser
from rom_wiki_core.utils.core.loader import PokeDBLoader
from rom_wiki_core.utils.formatters.markdown_formatter import (
    format_pokemon,
    format_type_badge,
)


class PokemonLocationsParser(LocationParser):
    """Parser for Pokemon Locations documentation.

    Args:
        LocationParser (_type_): Location parser base class.
    """

    def __init__(self, input_file: str, output_dir: str = "docs"):
        """Initialize the Pokemon Locations parser.

        Args:
            input_file (str): Path to the input file.
            output_dir (str, optional): Path to the output directory. Defaults to "docs".
        """
        super().__init__(
            input_file=input_file,
            output_dir=output_dir,
            location_separators=[" [ ", " - "],
        )
        self._sections = ["General Notes", "Encounters"]

        # Register tracking key for wild encounters
        self._register_tracking_key("wild_encounters")

        # Encounters states
        self._levels = {
            "Sacred Gold": "",
            "Storm Silver": "",
        }
        self._current_method = None
        self._encounters = {}

    def parse_general_notes(self, line: str) -> None:
        """Parse a line from the General Notes section.

        Args:
            line (str): A line from the General Notes section.
        """
        self.parse_default(line)

    def parse_encounters(self, line: str) -> None:
        """Parse a line from the Encounters section.

        Args:
            line (str): A line from the Encounters section.
        """
        next_line = self.peek_line(1) or ""

        # Wild Levels
        if line.startswith("Wild Levels:"):
            levels = line.split(": ")[1]
            self._levels["Sacred Gold"] = levels
            self._levels["Storm Silver"] = levels
        elif line.startswith("Sacred Gold Wild Levels:"):
            self._levels["Sacred Gold"] = line.split(": ")[1]
        elif line.startswith("Storm Silver Wild Levels:"):
            self._levels["Storm Silver"] = line.split(": ")[1]
        # Location
        elif "Wild Levels:" in next_line:
            if match := re.match(r"^(.+?) \[ (.+?) \]$", line):
                location = match.group(1)
                sublocation = match.group(2)

                if self._current_location != location:
                    self._current_location = location
                    self._current_sublocation = ""
                    self._initialize_location_data(location)
                    self._markdown += f"### {self._current_location}\n\n"

                self._current_sublocation = sublocation
                self._ensure_sublocation_exists(self._current_location, sublocation)
                self._clear_location_data_on_first_encounter(
                    "wild_encounters", "wild_encounters"
                )
                self._markdown += f"#### {self._current_sublocation}\n\n"
            else:
                self._current_location = line
                self._current_sublocation = ""
                self._initialize_location_data(line)
                self._clear_location_data_on_first_encounter(
                    "wild_encounters", "wild_encounters"
                )
                self._markdown += f"### {line}\n\n"
        # Encounter method
        elif line.endswith(":"):
            self._current_method = line[:-1]
            self._encounters[self._current_method] = {}
        # End of location block
        elif line == "" and self._current_method is not None:
            self._markdown += self._format_encounters()
            self._save_encounters_to_location()
            self.parse_default(line)

            self._current_method = None
            self._encounters.clear()
        # Encounters
        elif self._current_method is not None:
            for encounter in line.split(", "):
                if match := re.match(r"^(.+?) \((\d+)%\)$", encounter):
                    pokemon = match.group(1)
                    chance = match.group(2)
                    self._encounters[self._current_method][pokemon] = chance
        # Default
        else:
            self.parse_default(line)

    def _format_encounters(self) -> str:
        """Format the encounters data into markdown.

        Returns:
            str: Formatted markdown string of encounters.
        """
        md = ""

        # Format levels
        if self._levels["Sacred Gold"] == self._levels["Storm Silver"]:
            level_md = self._levels["Sacred Gold"]
        else:
            level_md = f'Sacred Gold: {self._levels["Sacred Gold"]}<br>Storm Silver: {self._levels["Storm Silver"]}'

        # Format encounters
        for method in self._encounters:
            md += f"**{method}**\n\n"

            # Format table header
            md += "| Pokémon | Type(s) | Level(s) | Chance |\n"
            md += "|:-------:|:-------:|:---------|:-------|\n"

            for pokemon_name, chance in self._encounters[method].items():
                # Load Pokemon data
                pokemon_data = PokeDBLoader.load_pokemon(pokemon_name)
                if pokemon_data is None:
                    continue
                pokemon_md = format_pokemon(pokemon_data)

                # Format type badges
                types = pokemon_data.types
                type_badges = " ".join([format_type_badge(t) for t in types])
                type_html = f"<div class='badges-vstack'>{type_badges}</div>"

                md += f"| {pokemon_md} | {type_html} | {level_md} | {chance}% |\n"

            md += "\n"

        return md

    def _save_encounters_to_location(self) -> None:
        """Save the current encounters to location JSON data."""
        if not self._current_location or self._current_location not in self._locations_data:
            return

        # Format levels for JSON
        if self._levels["Sacred Gold"] == self._levels["Storm Silver"]:
            level_str = self._levels["Sacred Gold"]
        else:
            level_str = f"SG: {self._levels['Sacred Gold']} / SS: {self._levels['Storm Silver']}"

        # Get target location/sublocation
        if self._current_sublocation:
            target = self._get_or_create_sublocation(
                self._locations_data[self._current_location], self._current_sublocation
            )
        else:
            target = self._locations_data[self._current_location]

        # Ensure wild_encounters exists
        if "wild_encounters" not in target:
            target["wild_encounters"] = {}

        # Add encounters for each method
        for method, pokemon_dict in self._encounters.items():
            if method not in target["wild_encounters"]:
                target["wild_encounters"][method] = []

            for pokemon_name, chance in pokemon_dict.items():
                pokemon_data = PokeDBLoader.load_pokemon(pokemon_name)
                types = pokemon_data.types if pokemon_data else []

                encounter_entry = {
                    "pokemon": pokemon_name,
                    "types": types,
                    "level": level_str,
                    "chance": int(chance),
                }
                target["wild_encounters"][method].append(encounter_entry)
