"""
Análisis cualitativo: categorización de errores y patrones de fallo.

Dimensiones de análisis:
  1. Por tipo de error (context_exceeded, timeout, hallucination, etc)
  2. Por dificultad (easy/medium/hard/extreme)
  3. Por mecánica (simple, navegación, goal compuesto, etc)
"""

import json
from collections import defaultdict
from typing import Optional


def categorize_error(result: dict) -> Optional[str]:
    """
    Categoriza el tipo de error de un resultado.

    Categorías:
      - context_exceeded: Error de contexto/tokens
      - timeout: max_steps excedido
      - hallucination: herramienta/parámetro inválido
      - lost_state: olvida dónde está o qué llevaba
      - goal_ordering: goal tipo sequence en orden incorrecto
      - navigation: falla en navegar multi-sala
      - unknown: otro tipo de error
    """
    if result["passed"]:
        return None

    error_type = result.get("error_type", "")
    error_msg = result.get("error_message", "").lower()
    scenario_id = result.get("scenario_id", "")

    if "context" in error_msg or "token" in error_msg or "context_length_exceeded" in error_msg:
        return "context_exceeded"

    if "timeout" in error_msg or "max_iteration" in error_msg:
        return "timeout"

    if "no such tool" in error_msg or "invalid" in error_msg or "unknown" in error_msg:
        return "hallucination"

    if "not found" in error_msg or "key" in error_msg:
        return "lost_state"

    if "office" in scenario_id or "sequence" in scenario_id:
        return "goal_ordering"

    if "apartment" in scenario_id:
        return "navigation"

    return "unknown"


class ErrorAnalysis:
    """Análisis cualitativo de errores y patrones de fallo."""

    def __init__(self, results: list[dict]):
        self.results = results

    def by_error_type(self) -> dict:
        """Desglose de errores por tipo."""
        errors = defaultdict(list)

        for result in self.results:
            if not result["passed"]:
                error = categorize_error(result)
                errors[error].append(result["scenario_id"])

        error_summary = {}
        failed_count = len([r for r in self.results if not r["passed"]])

        for error_type, scenarios in errors.items():
            count = len(scenarios)
            pct = round((count / failed_count) * 100, 1) if failed_count > 0 else 0
            error_summary[error_type] = {
                "count": count,
                "percentage": pct,
                "scenarios": scenarios,
            }

        return error_summary

    def by_difficulty(self) -> dict:
        """Desglose de éxito/fallo por dificultad."""
        by_diff = defaultdict(lambda: {"passed": 0, "failed": 0, "accuracy": 0})

        for result in self.results:
            difficulty = result.get("difficulty", "unknown")
            if result["passed"]:
                by_diff[difficulty]["passed"] += 1
            else:
                by_diff[difficulty]["failed"] += 1

        # Calcular accuracy
        for diff in by_diff:
            total = by_diff[diff]["passed"] + by_diff[diff]["failed"]
            by_diff[diff]["accuracy"] = round(
                (by_diff[diff]["passed"] / total) * 100, 1) if total > 0 else 0

        return dict(by_diff)

    def by_mechanic(self) -> dict:
        """Desglose por mecánica del escenario."""
        mechanics = {
            "simple": ["study-with-key"],
            "color_chain": ["color-locks"],
            "library_search": ["library-search"],
            "archive_long": ["extreme-archive"],
            "multi_room_navigation": ["apartment-keys"],
            "sequence_goal": ["office-sequence"],
            "multi_item_lock": ["vault-combination"],
            "backtracking": ["backtracking-vault"],
        }

        by_mech = {}
        for mech_name, keywords in mechanics.items():
            results_for_mech = [
                r for r in self.results
                if any(keyword in r["scenario_id"] for keyword in keywords)
            ]

            if results_for_mech:
                passed = sum(1 for r in results_for_mech if r["passed"])
                failed = len(results_for_mech) - passed
                accuracy = round((passed / len(results_for_mech)) * 100, 1)

                by_mech[mech_name] = {
                    "count": len(results_for_mech),
                    "passed": passed,
                    "failed": failed,
                    "accuracy": accuracy,
                    "scenarios": [r["scenario_id"] for r in results_for_mech],
                }

        return by_mech

    def failure_patterns(self) -> dict:
        """Patrones de fallo más comunes."""
        failed_results = [r for r in self.results if not r["passed"]]

        patterns = {
            "no_steps_taken": 0,  # Agent no hizo nada
            "context_exhausted": 0,  # Contexto lleno
            "repeated_same_action": 0,  # Loop infinito
            "wrong_goal_order": 0,  # Goal compuesto en orden incorrecto
            "navigation_failure": 0,  # No pudo navegar
        }

        for result in failed_results:
            if result["steps"] == 0:
                patterns["no_steps_taken"] += 1
            elif "context" in result.get("error_message", "").lower():
                patterns["context_exhausted"] += 1
            elif "sequence" in result.get("scenario_id", ""):
                patterns["wrong_goal_order"] += 1
            elif "apartment" in result.get("scenario_id", ""):
                patterns["navigation_failure"] += 1

        return patterns

    def summary(self) -> dict:
        """Resumen completo de análisis de errores."""
        total_failed = len([r for r in self.results if not r["passed"]])

        return {
            "total_failed": total_failed,
            "total_passed": len([r for r in self.results if r["passed"]]),
            "error_types": self.by_error_type() if total_failed > 0 else {},
            "by_difficulty": self.by_difficulty(),
            "by_mechanic": self.by_mechanic(),
            "failure_patterns": self.failure_patterns() if total_failed > 0 else {},
        }

    def print_summary(self) -> None:
        """Imprime análisis formateado."""
        analysis = self.summary()

        print("\n" + "="*70)
        print("  ANÁLISIS DE ERRORES")
        print("="*70)

        print(f"  Total ejecutados: {analysis['total_passed'] + analysis['total_failed']}")
        print(f"  Resueltos:        {analysis['total_passed']}")
        print(f"  Fallidos:         {analysis['total_failed']}")

        if analysis["total_failed"] > 0:
            print("\n  Tipos de error:")
            for error_type, details in analysis["error_types"].items():
                print(
                    f"    {error_type:20s}: {details['count']:2d} ({details['percentage']:5.1f}%)"
                )

        print("\n  Por dificultad:")
        for diff, data in analysis["by_difficulty"].items():
            print(
                f"    {diff:10s}: {data['passed']}/{data['passed']+data['failed']} ({data['accuracy']:5.1f}%)"
            )

        print("\n  Por mecánica:")
        for mech, data in analysis["by_mechanic"].items():
            print(
                f"    {mech:20s}: {data['passed']}/{data['count']} ({data['accuracy']:5.1f}%)"
            )

        print("="*70 + "\n")


def load_results(path: str) -> list[dict]:
    """Carga resultados de un archivo JSON."""
    with open(path, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        results_path = sys.argv[1]
    else:
        results_path = "eval/results/baseline.json"

    results = load_results(results_path)
    analysis = ErrorAnalysis(results)
    analysis.print_summary()
