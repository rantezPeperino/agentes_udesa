"""Configuración de escenarios para M3."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScenarioMeta:
    """Metadatos de un escenario."""
    id: str
    difficulty: str
    optimal_calls: int
    scenario_file: Path | str


# Tabla de escenarios con óptimos
SCENARIOS = [
    ScenarioMeta("study-with-key", "easy", 3, "scenarios/01-study-with-key.json"),
    ScenarioMeta("color-locks", "medium", 11, "scenarios/02-medium-color-locks.json"),
    ScenarioMeta("apartment-keys", "medium", 7, "scenarios/05-medium-apartment-keys.json"),
    ScenarioMeta("library-search", "hard", 7, "scenarios/03-hard-library-search.json"),
    ScenarioMeta("office-sequence", "hard", 13, "scenarios/06-hard-office-sequence.json"),
    ScenarioMeta("extreme-archive", "extreme", 4, "scenarios/04-extreme-archive.json"),
    ScenarioMeta("vault-combination", "extreme", 21, "scenarios/07-extreme-vault-combination.json"),
    ScenarioMeta("backtracking-vault", "extreme", 18, "scenarios/08-extreme-backtracking-vault.json"),
]

SCENARIO_MAP = {s.id: s for s in SCENARIOS}


def get_scenario_meta(scenario_id: str) -> ScenarioMeta | None:
    """Obtiene metadatos de un escenario."""
    return SCENARIO_MAP.get(scenario_id)
