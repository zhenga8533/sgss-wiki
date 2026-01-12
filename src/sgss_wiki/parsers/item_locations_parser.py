"""
Parser for Item Locations documentation file.

This parser:
1. Reads data/documentation/Item Locations.txt
2. Generates a markdown file to docs/item_locations.md
"""

from rom_wiki_core.parsers.base_parser import BaseParser
from rom_wiki_core.utils.formatters.markdown_formatter import (
    format_item,
    format_move,
)


class ItemLocationsParser(BaseParser):
    """Parser for Item Locations documentation.

    Args:
        BaseParser (_type_): Abstract base parser class
    """

    def __init__(self, input_file: str, output_dir: str = "docs"):
        """Initialize the Item Locations parser.

        Args:
            input_file (str): Path to the input file.
            output_dir (str, optional): Path to the output directory. Defaults to "docs".
        """
        super().__init__(input_file=input_file, output_dir=output_dir)
        self._sections = [
            "General Notes",
            "Technical Machine Locations",
            "Evolutionary Item Locations",
            "Key Item Locations",
            "Fossil Locations",
            "Other Item Locations",
        ]

    def handle_section_change(self, new_section: str) -> None:
        super().handle_section_change(new_section)

        if new_section == "Technical Machine Locations":
            self._markdown += "| TM | Move | Locations |\n"
            self._markdown += "|:---|:-----|:----------|\n"
        elif new_section in [
            "Evolutionary Item Locations",
            "Key Item Locations",
            "Other Item Locations",
        ]:
            self._markdown += "| Item | Locations |\n"
            self._markdown += "|:-----|:----------|\n"

    def parse_general_notes(self, line: str) -> None:
        """Parse a line from the General Notes section.

        Args:
            line (str): A line from the General Notes section.
        """
        self.parse_default(line)

    def parse_technical_machine_locations(self, line: str) -> None:
        """Parse a line from the Technical Machine Locations section.

        Args:
            line (str): A line from the Technical Machine Locations section.
        """

        if ": " in line:
            item, locations = line.split(": ", 1)
            tm, move = item.split(" ", 1)

            self._markdown += (
                f"| {format_item(tm)} | {format_move(move)} | {locations} |\n"
            )
        elif line == "---":
            pass
        else:
            self.parse_default(line)

    def parse_evolutionary_item_locations(self, line: str) -> None:
        """Parse a line from the Evolutionary Item Locations section.

        Args:
            line (str): A line from the Evolutionary Item Locations section.
        """

        if ": " in line:
            item, locations = line.split(": ", 1)

            self._markdown += f"| {format_item(item)} | {locations} |\n"
        elif line.startswith("* "):
            self._markdown += f"\n{line.replace('*', '\\*')}\n"
        elif line == "---":
            pass
        else:
            self.parse_default(line)

    def parse_key_item_locations(self, line: str) -> None:
        """Parse a line from the Key Item Locations section.

        Args:
            line (str): A line from the Key Item Locations section.
        """
        self.parse_evolutionary_item_locations(line)

    def parse_fossil_locations(self, line: str) -> None:
        """Parse a line from the Fossil Locations section.

        Args:
            line (str): A line from the Fossil Locations section.
        """
        self.parse_default(line)

    def parse_other_item_locations(self, line: str) -> None:
        """Parse a line from the Other Item Locations section.

        Args:
            line (str): A line from the Other Item Locations section.
        """
        self.parse_evolutionary_item_locations(line)
