#!/usr/bin/env python3
"""Validación manual del agente contra el mundo simulado (M3 Paso 0).

Script exploratorio para verificar que el agente resuelve escenarios del
mundo simulado antes de construir la infraestructura de evaluación completa.

Uso:
    python scripts/validate_world.py --scenario easy
    python scripts/validate_world.py --scenario easy --dry-run
    python scripts/validate_world.py --all --max-difficulty medium
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Intentar importar del mundo simulado
MIAWORLD_AVAILABLE = False
try:
    from mia_world import (
        load_scenario,
        make_world_tools,
        check_goal,
        list_scenarios,
    )
    MIAWORLD_AVAILABLE = True
except ImportError as e:
    # Guardar el error para diagnóstico
    _IMPORT_ERROR = str(e)

from mia_agents.llm_client import LLMClient
from mia_agents._env import load_env_files
from student_framework import build_agent


# Diccionario de soluciones optimas para --dry-run (replicado de test_m3_world.py)
_SCENARIO_SOLUTIONS = {
    "study-with-key": {
        "difficulty": "easy",
        "optimal_calls": 3,
        "solution": ["examine:alfombra", "take:llave_oro", "use:llave_oro,puerta_principal"],
    },
    # Extender cuando esten disponibles los otros escenarios
}


def resolve_scenario_path(scenario_spec: str) -> Path:
    """Resuelve la ruta del escenario desde un nombre corto o path."""
    # Si es un archivo directo
    if scenario_spec.endswith(".json"):
        return Path(scenario_spec)

    # Mapeo de nombres cortos a nombres de archivo
    scenario_map = {
        "easy": "01-easy-study-with-key.json",
        "medium": "02-medium-color-locks.json",
        "hard": "03-hard-library-search.json",
        "extreme": "04-extreme-archive.json",
    }

    if scenario_spec in scenario_map:
        filename = scenario_map[scenario_spec]
        return Path(__file__).parent.parent / "scenarios" / filename

    # Si no es corto, intentar como ID
    return Path(__file__).parent.parent / "scenarios" / f"{scenario_spec}.json"


def load_scenario_safe(path: Path) -> dict[str, Any] | None:
    """Carga un escenario JSON o desde mia_world."""
    if MIAWORLD_AVAILABLE:
        try:
            return load_scenario(path.stem)
        except Exception as e:
            print(f"❌ Error al cargar escenario desde mia_world: {e}", file=sys.stderr)
            # Continuar con fallback JSON

    # Fallback: intentar cargar JSON
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error al cargar JSON: {e}", file=sys.stderr)
            return None

    print(f"❌ Escenario no encontrado: {path}", file=sys.stderr)
    if not MIAWORLD_AVAILABLE:
        print(f"   (mia_world no disponible)", file=sys.stderr)
    return None


def check_llm_config() -> tuple[LLMClient | None, str]:
    """Verifica que la configuración del LLM esté disponible."""
    load_env_files()

    import os

    ollama_host = os.environ.get("OLLAMA_HOST")
    bedrock_model = os.environ.get("BEDROCK_MODEL_ID")

    if not ollama_host and not bedrock_model:
        return None, (
            "Configuración LLM incompleta:\n"
            "  Define OLLAMA_HOST (ej: http://localhost:11434)\n"
            "  O BEDROCK_MODEL_ID (ej: amazon.nova-lite-v1:0)"
        )

    try:
        llm = LLMClient.from_env()
        provider_name = "Ollama" if ollama_host else "AWS Bedrock"
        model_name = ollama_host or bedrock_model
        return llm, f"{provider_name}: {model_name}"
    except Exception as e:
        return None, f"Error al construir LLMClient: {e}"


def format_result_truncated(text: str, max_length: int = 120) -> str:
    """Trunca un resultado de tool a longitud máxima para legibilidad."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def print_separator(char: str = "=", length: int = 60) -> None:
    """Imprime un separador de línea."""
    print(char * length)


def print_section_header(title: str) -> None:
    """Imprime un encabezado de sección."""
    print_separator("-")
    print(title)
    print_separator("-")


def run_validation(
    scenario_id: str,
    dry_run: bool = False,
    max_iterations: int = 30,
    system_prompt: str | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Ejecuta la validación de un escenario."""

    report = {
        "scenario": scenario_id,
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "success": False,
        "error": None,
        "won": False,
        "reason": "",
        "steps": [],
        "tokens_in": None,
        "tokens_out": None,
        "latency": 0,
        "answer": "",
        "event_log": [],
        "hallazgos": [],
    }

    # Paso 1: Resolver escenario
    scenario_path = resolve_scenario_path(scenario_id)
    scenario = load_scenario_safe(scenario_path)
    if not scenario:
        report["error"] = f"No se pudo cargar el escenario: {scenario_id}"
        return report

    print_separator("=")
    print(f"ESCENARIO: {scenario.get('id', scenario_id)}")
    print_separator("=")

    difficulty = scenario.get("difficulty", "unknown")
    meta = scenario.get("goal", {})
    print(f"Meta          : {meta.get('type', '?')} / {meta.get('item', '?')}")

    # Obtener solución óptima (si disponible)
    scenario_key = scenario.get("id", scenario_id)
    optimal_calls = _SCENARIO_SOLUTIONS.get(scenario_key, {}).get("optimal_calls", "?")
    print(f"Optimal       : {optimal_calls} tool calls")

    # Paso 2: Obtener herramientas
    tools = []
    world = scenario.get("initial_world")

    if MIAWORLD_AVAILABLE and world:
        try:
            tools = list(make_world_tools(world))
            tool_names = [name for name, _ in tools]
            print(f"Herramientas  : {', '.join(tool_names)}   ({len(tools)})")
        except Exception as e:
            report["error"] = f"Error al obtener herramientas: {e}"
            return report
    elif not dry_run and not MIAWORLD_AVAILABLE:
        print("⚠️  mia_world no disponible. Saltando validación con LLM.")
        report["error"] = "mia_world no disponible (necesario para modo normal)"
        return report

    print(f"Modelo        : (--dry-run)" if dry_run else "Configurando...")
    print(f"Presupuesto   : {max_iterations} iteraciones, 50 msgs de historial")

    # Paso 3: En modo dry-run, ejecutar solución hardcodeada
    if dry_run:
        print_section_header("MODO DRY-RUN (sin LLM)")

        if not MIAWORLD_AVAILABLE:
            print("❌ No se puede ejecutar dry-run sin mia_world disponible.")
            report["error"] = "mia_world requerido para dry-run"
            return report

        solution = _SCENARIO_SOLUTIONS.get(scenario_key, {}).get("solution", [])
        if not solution:
            print(f"❌ No hay solución hardcodeada para {scenario_key}")
            report["error"] = f"Solución no disponible: {scenario_key}"
            return report

        # Ejecutar las acciones de la solución
        print_section_header("TRAZA DE ACCIONES")
        steps_executed = []

        try:
            # Reconstruir tools dict
            tools_dict = {name: fn for fn, schema in make_world_tools(world)}

            for i, action_spec in enumerate(solution, 1):
                # Parsear "tool_name:arg1,arg2..."
                parts = action_spec.split(":")
                tool_name = parts[0]
                args_str = parts[1] if len(parts) > 1 else ""

                # Construir argumentos (simplificado)
                kwargs = {}
                if args_str:
                    arg_parts = args_str.split(",")
                    if tool_name == "examine":
                        kwargs = {"target": arg_parts[0]}
                    elif tool_name == "take":
                        kwargs = {"item": arg_parts[0]}
                    elif tool_name == "use":
                        kwargs = {"item": arg_parts[0], "target": arg_parts[1]}
                    elif tool_name == "go":
                        kwargs = {"direction": arg_parts[0]}

                # Ejecutar la herramienta
                if tool_name in tools_dict:
                    try:
                        output = tools_dict[tool_name](**kwargs)
                        truncated = format_result_truncated(str(output))
                        print(f"  {i}  {tool_name}({', '.join(f'{k}=\"{v}\"' for k, v in kwargs.items())})")
                        print(f"     -> {truncated}")
                        steps_executed.append(
                            {
                                "tool_name": tool_name,
                                "tool_input": json.dumps(kwargs),
                                "tool_output": str(output),
                                "error": None,
                            }
                        )
                    except Exception as e:
                        print(f"  {i}  ERROR {tool_name}(...)")
                        print(f"     -> {str(e)[:120]}")
                        steps_executed.append(
                            {
                                "tool_name": tool_name,
                                "tool_input": json.dumps(kwargs),
                                "tool_output": f"Error: {str(e)}",
                                "error": str(e),
                            }
                        )
                else:
                    print(f"  {i}  UNKNOWN {tool_name}(...)")

            # Verificar goal
            report["steps"] = steps_executed
            report["latency"] = 0  # dry-run no tiene latencia

            try:
                won, reason = check_goal(world, scenario.get("goal", {}))
                report["won"] = won
                report["reason"] = reason
                report["success"] = True
            except Exception as e:
                report["error"] = f"Error al verificar goal: {e}"

        except Exception as e:
            report["error"] = f"Error en dry-run: {e}"

        # Imprimir resultado
        print_section_header("RESULTADO")
        print(
            f"Meta alcanzada : {'SI' if report['won'] else 'NO'}"
        )
        print(f"Razon          : {report['reason']}")
        print(f"Tool calls     : {len(steps_executed)}")
        print(f"Errores tool   : {sum(1 for s in steps_executed if s['error'])}")

        return report

    # Paso 4: Modo normal (con LLM real) — NO EJECUTAR en esta tarea
    print("⚠️  Modo con LLM real no ejecutado (--dry-run es el único modo para esta tarea)")
    report["error"] = "Solo --dry-run está permitido en esta tarea exploratoria"
    return report


def main() -> int:
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Validación manual del agente contra mundo simulado (M3 Paso 0)"
    )
    parser.add_argument(
        "--scenario",
        default="easy",
        help="Escenario: easy/medium/hard/extreme o archivo JSON",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ejecutar todos los escenarios",
    )
    parser.add_argument(
        "--max-difficulty",
        default="medium",
        choices=["easy", "medium", "hard", "extreme"],
        help="Con --all, cortar tras esta dificultad",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ejecutar solución hardcodeada sin LLM",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=30,
        help="Override del presupuesto de pasos",
    )
    parser.add_argument(
        "--system-prompt",
        help="System prompt alternativo",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Imprimir historial completo",
    )

    args = parser.parse_args()

    # Protocolo de ejecución
    # Paso 1: pytest tests/ -q (ya verificado antes)
    print("Paso 0: Validación manual de escenarios M3\n")

    # Paso 2: Ejecutar dry-run
    if args.dry_run or not args.all:
        scenario_to_run = args.scenario if not args.all else "easy"
        print(f"Ejecutando: {scenario_to_run} (--dry-run)")
        print()

        report = run_validation(
            scenario_to_run,
            dry_run=True,
            max_iterations=args.max_iterations,
            system_prompt=args.system_prompt,
            verbose=args.verbose,
        )

        if report["error"]:
            print()
            print(f"❌ Error: {report['error']}")
            return 2 if "mia_world" in report["error"] else 1

        return 0 if report["won"] else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
