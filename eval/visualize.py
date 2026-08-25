"""Generador de reportes visuales con Plotly."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from collections import defaultdict
import statistics

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from eval.metrics import compute_metrics, pass_at_k
from eval.taxonomy import CATEGORY_DESCRIPTIONS


def jsonl_to_results(jsonl_path: Path) -> list[dict[str, Any]]:
    """Lee un archivo JSONL."""
    results = []
    try:
        with open(jsonl_path) as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    except FileNotFoundError:
        pass
    return results


def create_success_gauge(metrics: dict[str, Any]) -> go.Figure:
    """Gauge de tasa de éxito agregada."""
    success_rate = metrics["goal_success_rate"] * 100
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=success_rate,
        delta={"reference": 50},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "darkblue"},
            "steps": [
                {"range": [0, 50], "color": "lightgray"},
                {"range": [50, 100], "color": "lightgreen"}
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 75
            }
        },
        domain={"x": [0, 1], "y": [0, 1]}
    ))
    fig.update_layout(height=400, font={"size": 12})
    return fig


def create_difficulty_bar(metrics: dict[str, Any]) -> go.Figure:
    """Bar chart de éxito por dificultad."""
    difficulties = []
    success_rates = []
    for difficulty, dmetrics in sorted(metrics["by_difficulty"].items()):
        difficulties.append(difficulty.upper())
        success_rates.append(dmetrics["success_rate"] * 100)

    fig = go.Figure([
        go.Bar(x=difficulties, y=success_rates, marker_color="steelblue")
    ])
    fig.update_layout(
        yaxis_title="Éxito (%)",
        height=400,
        showlegend=False
    )
    return fig


def create_efficiency_scatter(results: list[dict[str, Any]]) -> go.Figure:
    """Scatter de eficiencia (pasos)."""
    efficiencies = []
    scenarios = []
    for r in results:
        if r["goal_achieved"] and r.get("n_tool_calls", 0) > 0:
            eff = r["optimal_calls"] / r["n_tool_calls"]
            efficiencies.append(eff)
            scenarios.append(r["scenario_id"])

    fig = go.Figure([
        go.Scatter(
            x=scenarios,
            y=efficiencies,
            mode="markers",
            marker=dict(size=10, color="green", opacity=0.6),
            text=[f"{e:.2f}x" for e in efficiencies],
            textposition="top center"
        )
    ])
    fig.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="Óptimo")
    fig.update_layout(
        yaxis_title="Eficiencia (óptimo/usado)",
        height=400,
        showlegend=False
    )
    return fig


def create_latency_box(results: list[dict[str, Any]]) -> go.Figure:
    """Box plot de latencia."""
    by_difficulty = defaultdict(list)
    for r in results:
        if r["latency_s"] > 0:
            by_difficulty[r["difficulty"].upper()].append(r["latency_s"])

    fig = go.Figure()
    for diff in sorted(by_difficulty.keys()):
        fig.add_trace(go.Box(
            y=by_difficulty[diff],
            name=diff,
            boxmean="sd"
        ))

    fig.update_layout(
        yaxis_title="Latencia (s)",
        height=400
    )
    return fig


def create_error_bar(results: list[dict[str, Any]]) -> go.Figure:
    """Horizontal bar de categorías de error."""
    error_counts = defaultdict(int)
    for r in results:
        for cat in r.get("error_categories", []):
            error_counts[cat] += 1

    if not error_counts:
        error_counts = {"Sin errores": 0}

    # Limitar a top 8
    top_errors = sorted(error_counts.items(), key=lambda x: -x[1])[:8]
    cats = [c for c, _ in top_errors]
    counts = [cnt for _, cnt in top_errors]

    fig = go.Figure([
        go.Bar(
            x=counts,
            y=cats,
            orientation="h",
            marker_color="indianred"
        )
    ])
    fig.update_layout(
        xaxis_title="Cantidad",
        height=400,
        showlegend=False
    )
    return fig


def create_tokens_area(results: list[dict[str, Any]]) -> go.Figure:
    """Área stacked de tokens consumidos."""
    by_difficulty = defaultdict(list)
    for r in results:
        if r["input_tokens"] and r["output_tokens"]:
            by_difficulty[r["difficulty"]].append({
                "in": r["input_tokens"],
                "out": r["output_tokens"]
            })

    difficulties = []
    tokens_in = []
    tokens_out = []
    for diff in sorted(by_difficulty.keys()):
        difficulties.append(diff.upper())
        in_avg = statistics.mean([t["in"] for t in by_difficulty[diff]])
        out_avg = statistics.mean([t["out"] for t in by_difficulty[diff]])
        tokens_in.append(in_avg)
        tokens_out.append(out_avg)

    fig = go.Figure(data=[
        go.Bar(name="Input", x=difficulties, y=tokens_in),
        go.Bar(name="Output", x=difficulties, y=tokens_out)
    ])
    fig.update_layout(
        barmode="stack",
        yaxis_title="Tokens (promedio)",
        height=400
    )
    return fig


def create_metrics_table(metrics: dict[str, Any]) -> go.Figure:
    """Tabla de métricas agregadas."""
    pass_k3 = pass_at_k([{
        "goal_achieved": r["goal_achieved"],
        "scenario_id": r["scenario_id"]
    } for r in metrics.get("_results", [])], k=3) if "_results" in metrics else 0

    metrics_data = [
        ["Métrica", "Valor"],
        ["Tasa de Éxito", f"{metrics['goal_success_rate']:.1%}"],
        ["Eficiencia (pasos)", f"{metrics['step_efficiency']:.2f}x" if metrics['step_efficiency'] else "N/A"],
        ["Pass@3", f"{pass_k3:.1%}"],
        ["Latencia (media)", f"{metrics['latency_mean_s']:.2f}s"],
        ["Latencia (p95)", f"{metrics['latency_p95_s']:.2f}s"],
        ["Tokens In (avg)", f"{metrics['tokens_in_mean']:.0f}"],
        ["Tokens Out (avg)", f"{metrics['tokens_out_mean']:.0f}"],
        ["Total Casos", str(metrics['n_cases_total'])],
        ["Casos Ganados", str(metrics['n_cases_passed'])],
    ]

    fig = go.Figure(data=[go.Table(
        header=dict(values=metrics_data[0], fill_color="steelblue", font=dict(color="white")),
        cells=dict(values=list(zip(*metrics_data[1:])), fill_color="lavender")
    )])
    fig.update_layout(height=400)
    return fig


def generate_html_report(jsonl_path: Path, output_file: Path | None = None) -> Path:
    """Genera un HTML completo con todos los gráficos.

    Args:
        jsonl_path: Ruta al archivo JSONL
        output_file: Ruta para guardar HTML (default: mismo dir, .html)

    Returns:
        Ruta del HTML generado
    """
    # Leer resultados
    results = jsonl_to_results(jsonl_path)
    if not results:
        print(f"⚠️  No se encontraron resultados en {jsonl_path}")
        return None

    # Calcular métricas
    metrics = compute_metrics(results)
    metrics["_results"] = results  # Para pass@k

    # Crear subplots
    fig = make_subplots(
        rows=4, cols=2,
        subplot_titles=(
            "Tasa de Éxito",
            "Éxito por Dificultad",
            "Eficiencia de Pasos",
            "Latencia",
            "Errores Detectados",
            "Tokens Consumidos",
            "Métricas Agregadas",
            "Resumen"
        ),
        specs=[
            [{"type": "indicator"}, {"type": "bar"}],
            [{"type": "scatter"}, {"type": "box"}],
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "table"}, {"type": "indicator"}]
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.1
    )

    # 1. Gauge de éxito
    gauge = create_success_gauge(metrics)
    for trace in gauge.data:
        fig.add_trace(trace, row=1, col=1)

    # 2. Bar por dificultad
    diff_fig = create_difficulty_bar(metrics)
    for trace in diff_fig.data:
        fig.add_trace(trace, row=1, col=2)

    # 3. Scatter eficiencia
    eff_fig = create_efficiency_scatter(results)
    for trace in eff_fig.data:
        fig.add_trace(trace, row=2, col=1)

    # 4. Box latencia
    lat_fig = create_latency_box(results)
    for trace in lat_fig.data:
        fig.add_trace(trace, row=2, col=2)

    # 5. Errores
    err_fig = create_error_bar(results)
    for trace in err_fig.data:
        fig.add_trace(trace, row=3, col=1)

    # 6. Tokens
    tok_fig = create_tokens_area(results)
    for trace in tok_fig.data:
        fig.add_trace(trace, row=3, col=2)

    # 7. Tabla métricas
    table_fig = create_metrics_table(metrics)
    for trace in table_fig.data:
        fig.add_trace(trace, row=4, col=1)

    # 8. Pass@k indicator
    pass_k3 = pass_at_k(results, k=3)
    pass_k_indicator = go.Indicator(
        mode="number+gauge",
        value=pass_k3 * 100,
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "darkgreen"},
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 80
            }
        }
    )
    fig.add_trace(pass_k_indicator, row=4, col=2)

    # Actualizar layout
    fig.update_layout(
        title_text="<b>Reporte M3 — Evaluación de Agente en Mundo Simulado</b>",
        height=2800,
        showlegend=True,
        font=dict(size=10),
        hovermode="closest"
    )

    # Agregar recuadro de referencia de gráficos al final
    reference_text = """
    <b>REFERENCIA DE GRÁFICOS</b><br>
    <br>
    <b>Tasa de Éxito:</b> % de escenarios resueltos correctamente<br>
    <b>Éxito por Dificultad:</b> Tasa de éxito desglosada por nivel de dificultad (easy, medium, hard, extreme)<br>
    <b>Eficiencia de Pasos:</b> Eficiencia = pasos_óptimos / pasos_usados. 1.0x = perfecto, 0.5x = usó el doble<br>
    <b>Latencia:</b> Tiempo en segundos para resolver. Distribución por dificultad (media, cuartiles, desviación estándar)<br>
    <b>Errores Detectados:</b> Categorías de errores encontrados durante la ejecución (top 8)<br>
    <b>Tokens Consumidos:</b> Tokens input (enviados al LLM) vs output (generados por LLM) por dificultad<br>
    <b>Métricas Agregadas:</b> Resumen numérico de todas las métricas principales (tasa éxito, eficiencia, pass@3, latencias, tokens)<br>
    <b>Resumen (Pass@3):</b> Confiabilidad: % de probabilidad de éxito si se repite 3 veces
    """

    fig.add_annotation(
        x=0.5, y=-0.08,
        text=reference_text,
        showarrow=False,
        xref="paper", yref="paper",
        xanchor="center", yanchor="top",
        align="left",
        bgcolor="rgba(240,248,255,0.9)",
        bordercolor="#4472C4",
        borderwidth=2,
        borderpad=15,
        font=dict(size=11, color="#333")
    )

    # Guardar HTML en eval/results/
    if output_file is None:
        output_file = Path("eval/results") / f"{jsonl_path.stem}_report.html"

    fig.write_html(str(output_file))
    return output_file
