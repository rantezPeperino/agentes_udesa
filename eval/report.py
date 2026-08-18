"""
Generador de informe Markdown con resultados, métricas y análisis.

Uso:
    python eval/report.py [--input baseline.json] [--output INFORME_M3.md]
"""

import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.metrics import Metrics
from eval.analysis import ErrorAnalysis


def generate_report(
    results_path: str = "eval/results/baseline.json",
    output_path: str = "INFORME_M3.md",
) -> None:
    """
    Genera informe Markdown desde archivo de resultados.

    Args:
        results_path: Ruta al JSON con resultados
        output_path: Ruta donde guardar el informe
    """

    if not Path(results_path).exists():
        print(f"❌ Error: {results_path} no existe")
        return

    # Cargar resultados
    with open(results_path, "r") as f:
        results = json.load(f)

    metrics = Metrics(results).summary()
    analysis = ErrorAnalysis(results).summary()

    # Construir markdown
    md = []

    # Título
    md.append("# Informe M3 - Evaluación sobre un Problema Objetivo\n")
    md.append("## Resumen Ejecutivo\n")

    # Resumen
    accuracy = metrics['accuracy_global']
    by_diff = metrics['accuracy_by_difficulty']
    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    md.append(f"**Accuracy global:** {accuracy}%\n\n")
    md.append(f"**Escenarios resueltos:** {passed}/{total}\n\n")

    md.append("**Desglose por dificultad:**\n")
    for diff, acc in sorted(by_diff.items()):
        difficulty_results = [r for r in results if r["difficulty"] == diff]
        diff_passed = sum(1 for r in difficulty_results if r["passed"])
        md.append(f"- **{diff.capitalize()}**: {acc}% ({diff_passed}/{len(difficulty_results)})\n")

    md.append("\n")

    # Tabla de resultados
    md.append("## Resultados por Escenario\n\n")
    md.append("| Escenario | Dificultad | ✓ | Steps | Tokens | Error |\n")
    md.append("|-----------|------------|---|-------|--------|-------|\n")

    for result in sorted(results, key=lambda r: r['scenario_id']):
        scenario_id = result['scenario_id']
        difficulty = result['difficulty'].capitalize()
        passed = "✅" if result['passed'] else "❌"
        steps = str(result['steps']) if result['steps'] > 0 else "—"
        tokens = str(result['total_tokens']) if result['total_tokens'] > 0 else "—"
        error = result.get('error_type', '—') or "—"

        md.append(f"| {scenario_id} | {difficulty} | {passed} | {steps} | {tokens} | {error} |\n")

    md.append("\n")

    # Métricas detalladas
    md.append("## Métricas Cuantitativas\n\n")

    md.append(f"**Pass@7:** {metrics['pass@7']['pass@7']}% ({metrics['pass@7']['count']}/{metrics['pass@7']['total']})\n\n")
    md.append(f"**Pass@13:** {metrics['pass@13']['pass@13']}% ({metrics['pass@13']['count']}/{metrics['pass@13']['total']})\n\n")
    md.append(f"**Pass@21:** {metrics['pass@21']['pass@21']}% ({metrics['pass@21']['count']}/{metrics['pass@21']['total']})\n\n")

    md.append(f"**Eficiencia promedio:** {metrics['efficiency']['average']}%\n")
    md.append("(Ratio: optimal_steps / actual_steps)\n\n")

    md.append(f"**Tokens/paso promedio:** {metrics['tokens']['avg_tokens_per_step']}\n\n")

    # Desglose por dificultad
    md.append("### Desglose Detallado por Dificultad\n\n")

    for diff, data in sorted(metrics['breakdown_by_difficulty'].items()):
        md.append(f"**{diff.capitalize()}** ({data['count']} escenarios)\n")
        md.append(f"- Accuracy: {data['accuracy']}%\n")
        md.append(f"- Steps totales: {data['total_steps']}\n")
        md.append(f"- Tokens totales: {data['total_tokens']}\n")
        md.append(f"- Tokens/paso: {data['avg_tokens_per_step']}\n\n")

    # Análisis de errores
    if analysis['total_failed'] > 0:
        md.append("## Análisis de Errores\n\n")
        md.append(f"**Total fallidos:** {analysis['total_failed']}/{total}\n\n")

        if analysis['error_types']:
            md.append("### Por Tipo de Error\n\n")
            for error_type, details in sorted(
                analysis['error_types'].items(),
                key=lambda x: x[1]['count'],
                reverse=True
            ):
                md.append(
                    f"- **{error_type}**: {details['count']} escenarios ({details['percentage']}%)\n"
                )
                md.append(f"  Escenarios: {', '.join(details['scenarios'])}\n\n")

    # Análisis por mecánica
    md.append("## Análisis por Mecánica del Escenario\n\n")

    for mech, data in sorted(analysis['by_mechanic'].items()):
        md.append(
            f"**{mech.replace('_', ' ').title()}** — {data['accuracy']}% "
            f"({data['passed']}/{data['count']})\n"
        )

    md.append("\n")

    # Conclusiones
    md.append("## Conclusiones\n\n")

    if accuracy >= 75:
        conclusion = "El agente resuelve la mayoría de escenarios correctamente."
    elif accuracy >= 50:
        conclusion = "El agente resuelve algunos escenarios, pero presenta problemas en casos más complejos."
    elif accuracy >= 25:
        conclusion = "El agente enfrenta dificultades significativas, resolviendo solo escenarios simples."
    else:
        conclusion = "El agente presenta limitaciones críticas en este problema."

    md.append(conclusion)
    md.append("\n\n")

    # Limitaciones
    md.append("## Limitaciones Observadas\n\n")

    md.append("- El escenario `extreme-archive` consume ~16K tokens, excediendo ventanas de contexto pequeñas.\n")
    md.append("- Los escenarios multi-sala (`apartment-keys`) requieren memoria de estado robusta entre turnos.\n")
    md.append("- Goals compuestos (`office-sequence` con tipo `sequence`) exigen planificación explícita del orden.\n")
    md.append("- Cerraduras multi-item (`vault-combination`) requieren coordinación compleja entre 3 salas.\n")
    md.append("- Backtracking profundo (`backtracking-vault`) demanda recolección de items en orden inverso.\n")

    md.append("\n## Qué Construirías Después\n\n")

    md.append("- **Memory buffers:** Resumen explícito de estado del mundo para no perder contexto.\n")
    md.append("- **Planning layer:** Descomposición de goals compuestos antes de actuar.\n")
    md.append("- **Tool use optimization:** Reducir pasos usando secuencias más eficientes.\n")
    md.append("- **Context management:** Poda inteligente de event logs en escenarios largos.\n")
    md.append("- **Multi-agent coordination:** Agentes especializados para navegación vs search.\n")

    # Escribir archivo
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        f.write("".join(md))

    print(f"✅ Informe generado: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Genera informe Markdown de evaluación")
    parser.add_argument(
        "--input",
        default="eval/results/baseline.json",
        help="Archivo JSON con resultados (default: eval/results/baseline.json)",
    )
    parser.add_argument(
        "--output",
        default="INFORME_M3.md",
        help="Archivo Markdown de salida (default: INFORME_M3.md)",
    )

    args = parser.parse_args()
    generate_report(results_path=args.input, output_path=args.output)
