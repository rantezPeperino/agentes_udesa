"""
Experimentos de ablación para entender qué partes del framework importan.

Define múltiples experimentos A/B comparando baseline vs intervenciones específicas.
"""

import json
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.metrics import Metrics


class Experiment:
    """Define y ejecuta un experimento de ablación."""

    def __init__(
        self,
        name: str,
        description: str,
        cmd_args: list[str],
    ):
        self.name = name
        self.description = description
        self.cmd_args = cmd_args

    def run(self, output_path: str) -> dict:
        """
        Ejecuta el experimento.

        Args:
            output_path: Dónde guardar los resultados

        Returns:
            Dict con resultados o error
        """
        print(f"\n  📊 {self.name}")
        print(f"     {self.description}")
        print(f"     Ejecutando...", flush=True)

        # Ejecutar eval/run.py con args específicos
        cmd = ["python3", "eval/run.py"] + self.cmd_args + ["--output", output_path]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                print(f"     ❌ Error: {result.stderr[:100]}")
                return {"error": result.stderr}

            # Cargar y retornar resultados
            with open(output_path, "r") as f:
                return json.load(f)
        except subprocess.TimeoutExpired:
            print(f"     ⏱️  Timeout (>5 min)")
            return {"error": "Timeout"}
        except Exception as e:
            print(f"     ❌ Error: {str(e)}")
            return {"error": str(e)}


def run_experiments():
    """Ejecuta todos los experimentos definidos."""

    Path("eval/results").mkdir(parents=True, exist_ok=True)

    print("\n" + "="*70)
    print("  EXPERIMENTOS DE ABLACIÓN")
    print("="*70)

    # =========================================================================
    # BASELINE: Configuración normal
    # =========================================================================

    print("\n🎯 BASELINE: Configuración normal (max_steps=20)")

    cmd = ["python3", "eval/run.py", "--output", "eval/results/baseline.json"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    with open("eval/results/baseline.json", "r") as f:
        baseline = json.load(f)

    baseline_metrics = Metrics(baseline).summary()
    baseline_accuracy = baseline_metrics['accuracy_global']
    baseline_pass7 = baseline_metrics['pass@7']['pass@7']

    print(f"   Accuracy: {baseline_accuracy}%")
    print(f"   Pass@7:   {baseline_pass7}%")

    # =========================================================================
    # EXPERIMENTO 1: Limitar steps a 5
    # =========================================================================

    exp1 = Experiment(
        name="Exp 1: Max Steps = 5",
        description="¿Es crítico un horizonte largo? Limitar a 5 iteraciones.",
        cmd_args=["--scenario", "all", "--max-steps", "5"],
    )

    exp1_results = exp1.run("eval/results/exp1_max_steps_5.json")

    if "error" not in exp1_results:
        exp1_metrics = Metrics(exp1_results).summary()
        exp1_accuracy = exp1_metrics['accuracy_global']
        delta_exp1 = exp1_accuracy - baseline_accuracy

        print(f"\n   📊 Resultado:")
        print(f"     Accuracy: {exp1_accuracy}% (delta: {delta_exp1:+.1f}%)")

        if delta_exp1 < -10:
            conclusion1 = "✅ Horizonte corto es CRÍTICO"
        elif delta_exp1 < -5:
            conclusion1 = "⚠️  Horizonte corto tiene IMPACTO"
        else:
            conclusion1 = "ℹ️  Horizonte corto tiene IMPACTO MENOR"

        print(f"     Conclusión: {conclusion1}")
    else:
        delta_exp1 = None
        print(f"\n   ❌ Experimento fallido")

    # =========================================================================
    # EXPERIMENTO 2: Solo escenarios fáciles
    # =========================================================================

    exp2 = Experiment(
        name="Exp 2: Solo Easy Scenarios",
        description="¿Cuál es la línea base? Ejecutar solo los escenarios easy.",
        cmd_args=["--scenario", "easy"],
    )

    exp2_results = exp2.run("eval/results/exp2_easy_only.json")

    if "error" not in exp2_results:
        exp2_metrics = Metrics(exp2_results).summary()
        exp2_accuracy = exp2_metrics['accuracy_global']

        print(f"\n   📊 Resultado:")
        print(f"     Accuracy (easy): {exp2_accuracy}%")

        if exp2_accuracy == 100:
            conclusion2 = "✅ Escenarios easy RESOLVIBLES"
        elif exp2_accuracy > 50:
            conclusion2 = "⚠️  Escenarios easy PARCIALMENTE RESOLVIBLES"
        else:
            conclusion2 = "❌ Incluso easy es PROBLEMÁTICO"

        print(f"     Conclusión: {conclusion2}")
    else:
        print(f"\n   ❌ Experimento fallido")

    # =========================================================================
    # EXPERIMENTO 3: Max Steps = 30 (más tiempo)
    # =========================================================================

    exp3 = Experiment(
        name="Exp 3: Max Steps = 30",
        description="¿Mejora con más iteraciones? Aumentar a 30.",
        cmd_args=["--scenario", "all", "--max-steps", "30"],
    )

    exp3_results = exp3.run("eval/results/exp3_max_steps_30.json")

    if "error" not in exp3_results:
        exp3_metrics = Metrics(exp3_results).summary()
        exp3_accuracy = exp3_metrics['accuracy_global']
        delta_exp3 = exp3_accuracy - baseline_accuracy

        print(f"\n   📊 Resultado:")
        print(f"     Accuracy: {exp3_accuracy}% (delta: {delta_exp3:+.1f}%)")

        if delta_exp3 > 5:
            conclusion3 = "✅ MÁS STEPS MEJORA significativamente"
        elif delta_exp3 > 0:
            conclusion3 = "ℹ️  Mejora marginal con más steps"
        else:
            conclusion3 = "❌ Más steps NO AYUDA"

        print(f"     Conclusión: {conclusion3}")
    else:
        print(f"\n   ❌ Experimento fallido")

    # =========================================================================
    # RESUMEN COMPARATIVO
    # =========================================================================

    print("\n" + "="*70)
    print("  RESUMEN COMPARATIVO")
    print("="*70)

    print(f"\nBaseline (max_steps=20):  {baseline_accuracy:5.1f}%")

    if "error" not in exp1_results:
        exp1_accuracy = Metrics(exp1_results).summary()['accuracy_global']
        print(f"Exp 1 (max_steps=5):      {exp1_accuracy:5.1f}% (delta: {exp1_accuracy - baseline_accuracy:+5.1f}%)")

    if "error" not in exp3_results:
        exp3_accuracy = Metrics(exp3_results).summary()['accuracy_global']
        print(f"Exp 3 (max_steps=30):     {exp3_accuracy:5.1f}% (delta: {exp3_accuracy - baseline_accuracy:+5.1f}%)")

    print("\n" + "="*70)

    # Guardar resumen
    summary = {
        "baseline": {
            "accuracy": baseline_accuracy,
            "pass@7": baseline_pass7,
            "max_steps": 20,
        },
    }

    if "error" not in exp1_results:
        summary["exp1"] = {
            "accuracy": Metrics(exp1_results).summary()['accuracy_global'],
            "max_steps": 5,
        }

    if "error" not in exp3_results:
        summary["exp3"] = {
            "accuracy": Metrics(exp3_results).summary()['accuracy_global'],
            "max_steps": 30,
        }

    with open("eval/results/experiments_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n✅ Resumen guardado: eval/results/experiments_summary.json\n")


if __name__ == "__main__":
    run_experiments()
