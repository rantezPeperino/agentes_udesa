"""
Runner reproducible para evaluar agente sobre escenarios de M3.

Ejecuta el agente sobre cada escenario, captura métricas y guarda resultados en JSON.

Uso:
    python eval/run.py [--scenario all|easy|medium|hard|extreme] [--max-steps 20] [--output results.json]

Ejemplos:
    python eval/run.py                                  # todos, salida: eval/results/baseline.json
    python eval/run.py --scenario easy --output easy.json
    python eval/run.py --scenario all --max-steps 5 --output ablated.json
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional, Any
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from mia_world import load_scenario, list_scenarios, make_world_tools, check_goal
from mia_agents import AgentResult
from student_framework import build_agent


# Pasos óptimos por escenario (del enunciado M3)
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


def _infer_difficulty(scenario_id: str) -> str:
    """Inferir dificultad del ID del escenario."""
    if "01-" in scenario_id or "study" in scenario_id:
        return "easy"
    elif "02-" in scenario_id or "05-" in scenario_id or "color" in scenario_id or "apartment" in scenario_id:
        return "medium"
    elif "03-" in scenario_id or "06-" in scenario_id or "library" in scenario_id or "office" in scenario_id:
        return "hard"
    elif "04-" in scenario_id or "07-" in scenario_id or "08-" in scenario_id or "archive" in scenario_id or "vault" in scenario_id or "backtracking" in scenario_id:
        return "extreme"
    return "unknown"


def run_scenario(scenario: Any, max_steps: int = 20) -> dict:
    """
    Ejecuta un escenario y captura métricas.

    Args:
        scenario: Objeto Scenario ya cargado
        max_steps: Máximo de iteraciones del agente

    Returns:
        Dict con resultados (passed, steps, tokens, error, etc)
    """
    start_time = time.time()

    try:
        # El scenario ya está cargado
        world = scenario.initial_world

        # Construir agente
        agent = build_agent()

        # Registrar herramientas del mundo
        for tool_fn, tool_schema in make_world_tools(world):
            agent.register_tool(tool_fn, tool_schema)

        # Ejecutar agente
        result: AgentResult = agent.run(
            user_message=scenario.user_message,
            max_iterations=max_steps,
        )

        # Verificar goal
        goal_achieved = check_goal(world, scenario.goal)

        # Extraer métricas
        return {
            "scenario_id": scenario.id,
            "description": scenario.description,
            "difficulty": scenario.difficulty,
            "passed": goal_achieved,
            "steps": len(result.steps),
            "input_tokens": result.input_tokens or 0,
            "output_tokens": result.output_tokens or 0,
            "total_tokens": (result.input_tokens or 0) + (result.output_tokens or 0),
            "latency_seconds": round(time.time() - start_time, 2),
            "error_type": None,
            "error_message": None,
            "event_log": world.event_log,
            "final_inventory": world.inventory,
            "final_room": world.current_room,
            "optimal_steps": OPTIMAL_STEPS.get(scenario.id, result.steps),
        }

    except Exception as e:
        return {
            "scenario_id": scenario.id,
            "description": "ERROR",
            "difficulty": scenario.difficulty,
            "passed": False,
            "steps": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "latency_seconds": round(time.time() - start_time, 2),
            "error_type": type(e).__name__,
            "error_message": str(e),
            "event_log": [],
            "final_inventory": [],
            "final_room": "unknown",
            "optimal_steps": OPTIMAL_STEPS.get(scenario.id, 0),
        }


def main():
    parser = argparse.ArgumentParser(
        description="Evalúa agente sobre escenarios M3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python eval/run.py                              # Todos los escenarios
  python eval/run.py --scenario easy              # Solo easy
  python eval/run.py --scenario medium --max-steps 10
  python eval/run.py --output custom_results.json
        """
    )
    parser.add_argument(
        "--scenario",
        default="all",
        help="Escenario a ejecutar: all, easy, medium, hard, extreme, o ID específico (default: all)",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Máximo de iteraciones del agente (default: 20)",
    )
    parser.add_argument(
        "--output",
        default="eval/results/baseline.json",
        help="Archivo de salida JSON (default: eval/results/baseline.json)",
    )

    args = parser.parse_args()

    # Determinar escenarios a ejecutar
    scenarios_dir = Path(__file__).resolve().parents[1] / "scenarios"
    all_scenarios = list_scenarios(scenarios_dir)

    if args.scenario == "all":
        scenarios_to_run = all_scenarios
    elif args.scenario in ["easy", "medium", "hard", "extreme"]:
        scenarios_to_run = [
            s for s in all_scenarios
            if s.difficulty == args.scenario
        ]
    else:
        # Buscar por ID específico
        scenarios_to_run = [s for s in all_scenarios if s.id == args.scenario]
        if not scenarios_to_run:
            print(f"❌ Error: Escenario '{args.scenario}' no encontrado")
            return

    # Ejecutar evaluación
    print(f"\n🎯 Ejecutando evaluación ({len(scenarios_to_run)} escenarios, max_steps={args.max_steps})\n")

    results = []
    for i, scenario in enumerate(scenarios_to_run, 1):
        print(f"  [{i}/{len(scenarios_to_run)}] {scenario.id:30s} ", end="", flush=True)
        result = run_scenario(scenario, max_steps=args.max_steps)
        results.append(result)

        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        steps = f"{result['steps']:2d}" if result["steps"] > 0 else " —"
        tokens = f"{result['total_tokens']:5d}" if result['total_tokens'] > 0 else "    —"
        error = f" ({result['error_type']})" if result["error_type"] else ""

        print(f"{status} | steps:{steps} | tokens:{tokens}{error}")

    # Guardar resultados
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    # Resumen
    passed = sum(1 for r in results if r["passed"])
    total_tokens = sum(r["total_tokens"] for r in results)
    total_steps = sum(r["steps"] for r in results if r["steps"] > 0)

    print(f"\n{'='*70}")
    print(f"  RESULTADO")
    print(f"{'='*70}")
    print(f"  Escenarios resueltos: {passed}/{len(results)} ({100*passed//len(results)}%)")
    print(f"  Pasos totales:        {total_steps}")
    print(f"  Tokens totales:       {total_tokens}")
    if len(results) > 0:
        print(f"  Tokens/paso promedio: {total_tokens / total_steps:.1f}" if total_steps > 0 else "  —")
    print(f"\n  📁 Resultados: {output_path}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
