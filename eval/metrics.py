"""Métricas agregadas para M3."""

from __future__ import annotations

from typing import Any
from collections import defaultdict
import statistics


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcula métricas cuantitativas y cualitativas.

    Args:
        results: Lista de CaseResult (como dicts para serialización)

    Returns:
        Diccionario con métricas agregadas
    """
    if not results:
        return {"error": "No results"}

    # Métricas cuantitativas
    goals_achieved = sum(1 for r in results if r["goal_achieved"])
    goal_success_rate = goals_achieved / len(results) if results else 0

    # Eficiencia (solo casos ganados)
    efficiencies = []
    for r in results:
        if r["goal_achieved"] and r.get("n_tool_calls", 0) > 0:
            eff = r["optimal_calls"] / r["n_tool_calls"]
            efficiencies.append(eff)

    step_efficiency = statistics.mean(efficiencies) if efficiencies else None

    # Latencias (media, p50, p95)
    latencies = [r["latency_s"] for r in results if r["latency_s"] > 0]
    latency_mean = statistics.mean(latencies) if latencies else 0
    latency_p50 = statistics.median(latencies) if latencies else 0
    latency_p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies) if latencies else 0

    # Tokens
    input_tokens_all = [r["input_tokens"] for r in results if r["input_tokens"]]
    output_tokens_all = [r["output_tokens"] for r in results if r["output_tokens"]]
    tokens_in_mean = statistics.mean(input_tokens_all) if input_tokens_all else 0
    tokens_out_mean = statistics.mean(output_tokens_all) if output_tokens_all else 0

    # Por dificultad
    by_difficulty = defaultdict(list)
    for r in results:
        by_difficulty[r["difficulty"]].append(r)

    difficulty_metrics = {}
    for difficulty, cases in by_difficulty.items():
        achieved = sum(1 for c in cases if c["goal_achieved"])
        rate = achieved / len(cases) if cases else 0
        difficulty_metrics[difficulty] = {
            "n_cases": len(cases),
            "success_rate": rate,
            "avg_tool_calls": statistics.mean([c["n_tool_calls"] for c in cases]) if cases else 0,
        }

    return {
        "main_metric": "goal_success_rate",
        "goal_success_rate": goal_success_rate,
        "step_efficiency": step_efficiency,
        "latency_mean_s": latency_mean,
        "latency_p50_s": latency_p50,
        "latency_p95_s": latency_p95,
        "tokens_in_mean": tokens_in_mean,
        "tokens_out_mean": tokens_out_mean,
        "by_difficulty": difficulty_metrics,
        "n_cases_total": len(results),
        "n_cases_passed": goals_achieved,
    }


def pass_at_k(results: list[dict[str, Any]], k: int = 3) -> float:
    """Calcula pass@k sobre repeticiones."""
    # Agrupar por scenario_id
    by_scenario = defaultdict(list)
    for r in results:
        by_scenario[r["scenario_id"]].append(r["goal_achieved"])

    # Para cada escenario, calcular si al menos 1 de k pasó
    pass_count = sum(1 for outcomes in by_scenario.values() if any(outcomes[:k]))
    return pass_count / len(by_scenario) if by_scenario else 0
