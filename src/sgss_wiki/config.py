"""
Configuration for Sacred Gold and Storm Silver Wiki.

This module creates a WikiConfig instance for use throughout the project.
"""

from pathlib import Path

from rom_wiki_core.config import WikiConfig

# Find the project root (where pyproject.toml is located)
_current_file = Path(__file__).resolve()
_package_root = _current_file.parent
PROJECT_ROOT = _package_root.parent.parent

# Create the configuration instance
CONFIG = WikiConfig(
    # Project paths
    project_root=PROJECT_ROOT,
    # Game information
    game_title="Sacred Gold and Storm Silver",
    version_group="heartgold-soulsilver",
    version_group_friendly="Heart Gold & Soul Silver",
    # PokeDB configuration
    pokedb_repo_url="https://github.com/zhenga8533/pokedb",
    pokedb_branch="data",
    pokedb_data_dir=str(PROJECT_ROOT / "data" / "pokedb"),
    pokedb_generations=["gen4", "gen5"],
    pokedb_version_groups=["platinum", "diamond_pearl", "heartgold_soulsilver"],
    pokedb_game_versions=["platinum", "diamond", "pearl", "heartgold", "soulsilver"],
    pokedb_sprite_version="heartgold_soulsilver",
    # Logging configuration
    logging_level="DEBUG",
    logging_format="text",
    logging_log_dir=str(PROJECT_ROOT / "logs"),
    logging_max_log_size_mb=10,
    logging_backup_count=5,
    logging_console_colors=True,
    logging_clear_on_run=True,
    # Parser registry (keep your existing parsers)
    parsers_registry={
        "evolution_changes": {
            "module": "sgss_wiki.parsers.evolution_changes_parser",
            "class": "EvolutionChangesParser",
            "input_file": "Evolution Changes.txt",
            "output_dir": str(PROJECT_ROOT / "docs" / "changes"),
        },
        "item_locations": {
            "module": "sgss_wiki.parsers.item_locations_parser",
            "class": "ItemLocationsParser",
            "input_file": "Item Locations.txt",
            "output_dir": str(PROJECT_ROOT / "docs" / "reference"),
        },
        "pokemon_changes": {
            "module": "sgss_wiki.parsers.pokemon_changes_parser",
            "class": "PokemonChangesParser",
            "input_file": "Pokemon Changes.txt",
            "output_dir": str(PROJECT_ROOT / "docs" / "changes"),
        },
        "pokemon_locations": {
            "module": "sgss_wiki.parsers.pokemon_locations_parser",
            "class": "PokemonLocationsParser",
            "input_file": "Pokemon Locations.txt",
            "output_dir": str(PROJECT_ROOT / "docs" / "reference"),
        },
        "special_events": {
            "module": "sgss_wiki.parsers.special_events_parser",
            "class": "SpecialEventsParser",
            "input_file": "Special Events.txt",
            "output_dir": str(PROJECT_ROOT / "docs" / "reference"),
        },
        "trainer_pokemon": {
            "module": "sgss_wiki.parsers.trainer_pokemon_parser",
            "class": "TrainerPokemonParser",
            "input_file": "Trainer Pokemon.txt",
            "output_dir": str(PROJECT_ROOT / "docs" / "reference"),
        },
    },
    # Parser configuration
    parser_dex_relative_path="..",
    # Generator registry
    generators_registry={
        "pokemon": {
            "module": "rom_wiki_core.generators.pokemon_generator",
            "class": "PokemonGenerator",
            "output_dir": str(PROJECT_ROOT / "docs" / "pokedex"),
        },
        "abilities": {
            "module": "rom_wiki_core.generators.ability_generator",
            "class": "AbilityGenerator",
            "output_dir": str(PROJECT_ROOT / "docs" / "pokedex"),
        },
        "items": {
            "module": "rom_wiki_core.generators.item_generator",
            "class": "ItemGenerator",
            "output_dir": str(PROJECT_ROOT / "docs" / "pokedex"),
        },
        "moves": {
            "module": "rom_wiki_core.generators.move_generator",
            "class": "MoveGenerator",
            "output_dir": str(PROJECT_ROOT / "docs" / "pokedex"),
        },
        "locations": {
            "module": "rom_wiki_core.generators.location_generator",
            "class": "LocationGenerator",
            "output_dir": str(PROJECT_ROOT / "docs" / "locations"),
        },
    },
    # Generator configuration
    generator_dex_relative_path="../..",
    generator_index_relative_path="..",
    # Location generator configuration
    location_index_columns=["Location", "Trainers", "Wild Encounters"],
)
