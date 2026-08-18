"""
Calcula métricas cuantitativas de la evaluación.

Métricas principales:
  - Accuracy: % de escenarios resueltos
  - Pass@k: % que resuelven en ≤k steps
  - Efficiency: (optimal_steps / actual_steps) × 100%
  - Tokens/step: eficiencia en uso de tokens
"""

import json
from pathlib import Path
from typing import Optional


OPTIMAL_STEPS = {
    "study-with-key": 3,
    "color-locks": 11,
    "library-search": 7,
    "extreme-archive": 4,
    "apartment-keys": 7,
    "office-sequence": 13,
    "vault-combination": 21,
    "backtracking-vault": 18,
}


class Metrics:
    """Calcula métricas sobre resultados de evaluación."""

    def __init__(self, results: list[dict]):
        self.results = results

    def accuracy(self, by_difficulty: bool = False) -> dict | float:
        """
        Porcentaje de escenarios resueltos.

        Args:
            by_difficulty: Si es True, retorna desglose por dificultad

        Returns:
            Float entre 0-100, o dict si by_difficulty=True
        """
        if by_difficulty:
            by_diff = {}
            for difficulty in ["easy", "medium", "hard", "extreme"]:
                filtered = [
                    r for r in self.results
                    if r.get("difficulty") == difficulty
                ]
                if filtered:
                    passed = sum(1 for r in filtered if r["passed"])
                    by_diff[difficulty] = round((passed / len(filtered)) * 100, 1)
            return by_diff
        else:
            passed = sum(1 for r in self.results if r["passed"])
            return round((passed / len(self.results)) * 100, 1) if self.results else 0

    def pass_at_k(self, k: int = 7) -> dict:
        """
        % de escenarios resueltos en ≤k steps.

        Args:
            k: Máximo de steps permitido

        Returns:
            Dict con porcentaje y detalles
        """
        passed_at_k = sum(
            1 for r in self.results
            if r["passed"] and r["steps"] <= k
        )
        total = len(self.results)
        return {
            f"pass@{k}": round((passed_at_k / total) * 100, 1) if total > 0 else 0,
            "count": passed_at_k,
            "total": total,
        }

    def efficiency(self) -> dict:
        """
        (optimal_steps / actual_steps) × 100% por escenario.

        Mide qué tan lejos está el agente del óptimo.

        Returns:
            Dict con eficiencia por escenario y promedio
        """
        efficiency = {}
        valid_count = 0
        valid_sum = 0

        for result in self.results:
            scenario_id = result["scenario_id"]
            optimal = OPTIMAL_STEPS.get(scenario_id, result["steps"])

            if result["passed"] and result["steps"] > 0:
                eff = round((optimal / result["steps"]) * 100, 1)
                valid_count += 1
                valid_sum += eff
            else:
                eff = 0

            efficiency[scenario_id] = eff

        avg = round(valid_sum / valid_count, 1) if valid_count > 0 else 0

        return {
            "by_scenario": efficiency,
            "average": avg,
        }

    def tokens_per_step(self) -> dict:
        """Promedio de tokens consumido por paso."""
        steps_total = sum(r["steps"] for r in self.results if r["steps"] > 0)
        tokens_total = sum(r["total_tokens"] for r in self.results)

        return {
            "total_tokens": tokens_total,
            "total_steps": steps_total,
            "avg_tokens_per_step": round(tokens_total / steps_total, 1) if steps_total > 0 else 0,
        }

    def breakdown_by_difficulty(self) -> dict:
        """Desglose detallado por dificultad."""
        by_diff = {}

        for difficulty in ["easy", "medium", "hard", "extreme"]:
            filtered = [
                r for r in self.results
                if r.get("difficulty") == difficulty
            ]
            if filtered:
                passed = sum(1 for r in filtered if r["passed"])
                total_steps = sum(r["steps"] for r in filtered if r["steps"] > 0)
                total_tokens = sum(r["total_tokens"] for r in filtered)

                by_diff[difficulty] = {
                    "count": len(filtered),
                    "passed": passed,
                    "accuracy": round((passed / len(filtered)) * 100, 1),
                    "total_steps": total_steps,
                    "total_tokens": total_tokens,
                    "avg_tokens_per_step": round(total_tokens / total_steps, 1) if total_steps > 0 else 0,
                }

        return by_diff

    def summary(self) -> dict:
        """Resumen completo de todas las métricas."""
        return {
            "accuracy_global": self.accuracy(),
            "accuracy_by_difficulty": self.accuracy(by_difficulty=True),
            "pass@7": self.pass_at_k(k=7),
            "pass@13": self.pass_at_k(k=13),
            "pass@21": self.pass_at_k(k=21),
            "efficiency": self.efficiency(),
            "tokens": self.tokens_per_step(),
            "breakdown_by_difficulty": self.breakdown_by_difficulty(),
        }

    def print_summary(self) -> None:
        """Imprime resumen formateado."""
        metrics = self.summary()

        print("\n" + "="*70)
        print("  MÉTRICAS")
        print("="*70)
        print(f"  Accuracy global:         {metrics['accuracy_global']}%")
        print("\n  Por dificultad:")
        for diff, acc in metrics['accuracy_by_difficulty'].items():
            print(f"    {diff:10s}: {acc:5.1f}%")

        print(f"\n  Pass@7:                  {metrics['pass@7']['pass@7']}%")
        print(f"  Pass@13:                 {metrics['pass@13']['pass@13']}%")
        print(f"  Pass@21:                 {metrics['pass@21']['pass@21']}%")
        print(f"\n  Eficiencia promedio:     {metrics['efficiency']['average']}%")
        print(f"  Tokens/paso promedio:    {metrics['tokens']['avg_tokens_per_step']}")
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

    if not Path(results_path).exists():
        print(f"❌ Error: {results_path} no existe")
        sys.exit(1)

    results = load_results(results_path)
    metrics = Metrics(results)
    metrics.print_summary()
