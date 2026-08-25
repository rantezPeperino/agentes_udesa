"""Generador de reportes a partir de JSONL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from collections import defaultdict

from eval.metrics import compute_metrics, pass_at_k
from eval.taxonomy import CATEGORY_DESCRIPTIONS


def jsonl_to_results(jsonl_path: Path) -> list[dict[str, Any]]:
    """Lee un archivo JSONL y devuelve una lista de resultados."""
    results = []
    try:
        with open(jsonl_path) as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    except FileNotFoundError:
        pass
    return results


def generate_report(results_dir: Path, output_file: Path | None = None) -> str:
    """Genera un reporte markdown desde los resultados.

    Args:
        results_dir: Directorio para guardar el reporte (output) - busca JSONL en eval/json/
        output_file: Archivo para guardar el reporte (opcional)

    Returns:
        Reporte en markdown
    """
    # Leer todos los JSONL desde eval/results/json/
    json_dir = results_dir / "json"
    all_results = []
    for jsonl_file in json_dir.glob("results_*.jsonl"):
        all_results.extend(jsonl_to_results(jsonl_file))

    if not all_results:
        report = "# Reporte M3\n\nSin resultados aún.\n"
        if output_file:
            output_file.write_text(report)
        return report

    # Calcular métricas
    metrics = compute_metrics(all_results)
    pass_k3 = pass_at_k(all_results, k=3)

    # Contar errores
    error_counts = defaultdict(int)
    for r in all_results:
        for cat in r.get("error_categories", []):
            error_counts[cat] += 1

    # Generar reporte
    lines = [
        "# Reporte M3 — Evaluación de Agente en Mundo Simulado",
        "",
        "## Resumen Ejecutivo",
        "",
        f"- **Tasa de Éxito**: {metrics['goal_success_rate']:.1%}",
        f"- **Eficiencia (pasos)**: {metrics['step_efficiency']:.2f}x óptimo (casos ganados)" if metrics['step_efficiency'] else "- **Eficiencia (pasos)**: N/A (sin casos ganados)",
        f"- **Pass@3**: {pass_k3:.1%}",
        f"- **Latencia media**: {metrics['latency_mean_s']:.2f}s (p95: {metrics['latency_p95_s']:.2f}s)",
        f"- **Tokens (in/out)**: {metrics['tokens_in_mean']:.0f} / {metrics['tokens_out_mean']:.0f}",
        "",
        "## Resultados por Dificultad",
        "",
    ]

    for difficulty, dmetrics in sorted(metrics["by_difficulty"].items()):
        lines.append(f"### {difficulty.upper()} ({dmetrics['n_cases']} casos)")
        lines.append(f"- Éxito: {dmetrics['success_rate']:.1%}")
        lines.append(f"- Pasos promedio: {dmetrics['avg_tool_calls']:.1f}")
        lines.append("")

    lines.extend([
        "## Categorías de Error Detectadas",
        "",
    ])

    if error_counts:
        for cat, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            desc = CATEGORY_DESCRIPTIONS.get(cat, cat)
            lines.append(f"- **{cat}**: {count} ({desc})")
    else:
        lines.append("Sin errores detectados.")

    lines.extend([
        "",
        "## Notas",
        "- Generado desde resultados JSONL",
        f"- Total de casos: {metrics['n_cases_total']}",
        f"- Casos resueltos: {metrics['n_cases_passed']}",
    ])

    report = "\n".join(lines)

    if output_file:
        output_file.write_text(report)

    return report
