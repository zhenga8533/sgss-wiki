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
from rom_wiki_core.utils.data.models import (
    EvolutionChain,
    EvolutionDetails,
    EvolutionNode,
)
from rom_wiki_core.utils.formatters.markdown_formatter import format_pokemon_card_grid
from rom_wiki_core.utils.services.evolution_service import EvolutionService
from rom_wiki_core.utils.text.text_util import name_to_id


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
        self._method_change: str | None = None

        # Condition Evolution states
        self._condition_pokemon: str | None = None
        self._evolutions: list[str] = []
        self._conditions: list[str] = []

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
            pokemon_list = line.split(", ")
            self._markdown += "\n"
            self._markdown += format_pokemon_card_grid(
                cast(Any, pokemon_list), relative_path="../pokedex/pokemon"
            )
            self._markdown += "\n\n"

            # Update evolution data immediately
            for pokemon_name in pokemon_list:
                if self._method_change == "use_item":
                    self._update_held_item_evolutions(pokemon_name)
                elif self._method_change == "covenant_orb":
                    self._update_trade_evolutions(pokemon_name, "covenant-orb")
                elif self._method_change == "voltaic_ore":
                    self._update_trade_evolutions(pokemon_name, "voltaic-ore")

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
            self._condition_pokemon = pokemon
            self._markdown += f"### {pokemon}\n\n"
            self._markdown += format_pokemon_card_grid(
                [pokemon], relative_path="../pokedex/pokemon"
            )
            self._markdown += "\n\n"
        elif line.startswith("- "):
            evolution, condition = line[2:].split(" - ")
            self._evolutions.append(evolution)
            self._conditions.append(condition)

            # Extract item name and update evolution data immediately
            if item_match := re.search(r'["\']([^"\']+)["\']', condition):
                item_name = name_to_id(item_match.group(1))
                if self._condition_pokemon:
                    self._update_condition_evolution(
                        self._condition_pokemon, evolution, item_name
                    )
        elif line == "":
            if self._evolutions and self._conditions:
                self._markdown += format_pokemon_card_grid(
                    cast(Any, self._evolutions),
                    relative_path="../pokedex/pokemon",
                    extra_info=self._conditions,
                )
                self._evolutions = []
                self._conditions = []
            self.parse_default(line)
        else:
            self.parse_default(line)

    def _update_held_item_evolutions(self, pokemon_name: str) -> None:
        """Update evolutions that convert held item trade to use-item.

        Finds trade evolutions with held items and converts them to use-item
        evolutions using the same item.

        Args:
            pokemon_name (str): Name of the Pokemon to update
        """
        pokemon_id = name_to_id(pokemon_name)
        pokemon_data = PokeDBLoader.load_pokemon(pokemon_id)
        if pokemon_data is None:
            self.logger.warning(f"Could not load Pokemon data for {pokemon_name}")
            return

        evolution_chain = pokemon_data.evolution_chain
        if not evolution_chain or not evolution_chain.species_name:
            self.logger.warning(f"No evolution chain found for {pokemon_name}")
            return

        # Find evolutions from this Pokemon that have held items (trade evolutions)
        # Create a copy since update_evolution_chain modifies the list
        evolutions = list(self._find_evolutions_from(evolution_chain, pokemon_id))
        for evo in evolutions:
            if evo.evolution_details and evo.evolution_details.trigger == "trade":
                item_name = evo.evolution_details.held_item
                if not item_name:
                    self.logger.warning(
                        f"Trade evolution {pokemon_name} -> {evo.species_name} "
                        f"has no held_item, skipping"
                    )
                    continue

                evolution_details = EvolutionDetails(
                    trigger="use-item",
                    item=item_name,
                )

                self.logger.info(
                    f"Updating held item evolution: {pokemon_name} -> {evo.species_name} "
                    f"(item: {item_name})"
                )

                self.evolution_service.update_evolution_chain(
                    pokemon_id=pokemon_id,
                    evolution_id=name_to_id(evo.species_name),
                    evolution_chain=evolution_chain,
                    evolution_details=evolution_details,
                    keep_existing=False,
                )

    def _update_trade_evolutions(self, pokemon_name: str, item_name: str) -> None:
        """Update pure trade evolutions to use-item with specified item.

        Finds trade evolutions (without held items) and converts them to
        use-item evolutions with the given item.

        Args:
            pokemon_name (str): Name of the Pokemon to update
            item_name (str): Name of the item to use for evolution
        """
        pokemon_id = name_to_id(pokemon_name)
        pokemon_data = PokeDBLoader.load_pokemon(pokemon_id)
        if pokemon_data is None:
            self.logger.warning(f"Could not load Pokemon data for {pokemon_name}")
            return

        evolution_chain = pokemon_data.evolution_chain
        if not evolution_chain or not evolution_chain.species_name:
            self.logger.warning(f"No evolution chain found for {pokemon_name}")
            return

        # Find evolutions from this Pokemon that are trade-based
        # Create a copy since update_evolution_chain modifies the list
        evolutions = list(self._find_evolutions_from(evolution_chain, pokemon_id))
        for evo in evolutions:
            if evo.evolution_details and evo.evolution_details.trigger == "trade":
                evolution_details = EvolutionDetails(
                    trigger="use-item",
                    item=item_name,
                )

                self.logger.info(
                    f"Updating trade evolution: {pokemon_name} -> {evo.species_name} "
                    f"(item: {item_name})"
                )

                self.evolution_service.update_evolution_chain(
                    pokemon_id=pokemon_id,
                    evolution_id=name_to_id(evo.species_name),
                    evolution_chain=evolution_chain,
                    evolution_details=evolution_details,
                    keep_existing=False,
                )

    def _update_condition_evolution(
        self, base_pokemon: str, evolution_target: str, item_name: str
    ) -> None:
        """Update a condition-based evolution to use-item.

        Args:
            base_pokemon (str): Name of the base Pokemon
            evolution_target (str): Name of the evolution target
            item_name (str): Name of the item to use for evolution
        """
        pokemon_id = name_to_id(base_pokemon)
        pokemon_data = PokeDBLoader.load_pokemon(pokemon_id)
        if pokemon_data is None:
            self.logger.warning(f"Could not load Pokemon data for {base_pokemon}")
            return

        evolution_chain = pokemon_data.evolution_chain
        if not evolution_chain or not evolution_chain.species_name:
            self.logger.warning(f"No evolution chain found for {base_pokemon}")
            return

        evolution_details = EvolutionDetails(
            trigger="use-item",
            item=item_name,
        )

        self.logger.info(
            f"Updating condition evolution: {base_pokemon} -> {evolution_target} "
            f"(item: {item_name})"
        )

        self.evolution_service.update_evolution_chain(
            pokemon_id=pokemon_id,
            evolution_id=name_to_id(evolution_target),
            evolution_chain=evolution_chain,
            evolution_details=evolution_details,
            keep_existing=False,
        )

    def _find_evolutions_from(
        self, evolution_chain: EvolutionChain | EvolutionNode, pokemon_id: str
    ) -> list[EvolutionNode]:
        """Find all evolutions from a specific Pokemon in the chain.

        Args:
            evolution_chain: The evolution chain to search
            pokemon_id (str): The Pokemon ID to find evolutions from

        Returns:
            list[EvolutionNode]: List of evolution nodes that this Pokemon evolves to
        """
        if name_to_id(evolution_chain.species_name) == pokemon_id:
            return evolution_chain.evolves_to

        for evo in evolution_chain.evolves_to:
            result = self._find_evolutions_from(evo, pokemon_id)
            if result:
                return result

        return []
