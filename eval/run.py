#!/usr/bin/env python3
"""CLI orquestador para evaluación de M3."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.config import SCENARIO_MAP, SCENARIOS
from eval.runner import run_case
from eval.experiments import EXPERIMENTS, get_experiment
from eval.judge import judge_case
from eval.report import generate_report
from eval.visualize import generate_html_report
from eval.taxonomy import classify_case


def main():
    parser = argparse.ArgumentParser(description="Evaluación de M3")
    parser.add_argument(
        "--scenarios",
        default="all",
        help="Escenarios: all, easy, medium, hard, extreme, o ID específico"
    )
    parser.add_argument(
        "--k", type=int, default=3,
        help="Número de repeticiones por escenario"
    )
    parser.add_argument(
        "--experiment",
        default="baseline",
        help="Experimento: baseline, exp1_window, exp2_budget, exp3_prompt, exp4_noop_tool, all"
    )
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Omitir evaluación LLM-as-judge"
    )
    parser.add_argument(
        "--out",
        default="eval/results",
        help="Directorio para resultados"
    )

    args = parser.parse_args()

    # Crear directorios de salida
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Directorio específico para JSON dentro de results
    json_dir = out_dir / "json"
    json_dir.mkdir(parents=True, exist_ok=True)

    # Filtrar escenarios
    scenarios_to_run = []
    if args.scenarios == "all":
        scenarios_to_run = SCENARIOS
    elif args.scenarios in ["easy", "medium", "hard", "extreme"]:
        scenarios_to_run = [s for s in SCENARIOS if s.difficulty == args.scenarios]
    else:
        meta = SCENARIO_MAP.get(args.scenarios)
        if meta:
            scenarios_to_run = [meta]
        else:
            print(f"Escenario desconocido: {args.scenarios}")
            return 1

    # Determinar experimentos
    experiments_to_run = []
    if args.experiment == "all":
        experiments_to_run = [(e.name, e.variants) for e in EXPERIMENTS]
    elif args.experiment == "baseline":
        experiments_to_run = [("baseline", [("baseline", {})])]
    else:
        exp = get_experiment(args.experiment)
        if exp:
            experiments_to_run = [(exp.name, exp.variants)]
        else:
            print(f"Experimento desconocido: {args.experiment}")
            return 1

    # Ejecutar evaluaciones
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = json_dir / f"results_{timestamp}.jsonl"

    total_cases = 0
    passed_cases = 0

    with open(results_file, "w") as f_results:
        for exp_name, variants in experiments_to_run:
            print(f"\n{'='*60}")
            print(f"Experimento: {exp_name}")
            print(f"{'='*60}")

            for variant_label, config_override in variants:
                print(f"\n  Variante: {variant_label}")

                for scenario_meta in scenarios_to_run:
                    for rep in range(args.k):
                        run_id = f"{exp_name}_{variant_label}_{scenario_meta.id}_rep{rep+1}"

                        # Preparar config
                        config = {
                            **config_override,
                        }

                        # Ejecutar caso
                        case_result = run_case(scenario_meta.id, config, run_id)

                        # Clasificar errores
                        case_result.error_categories = classify_case(
                            case_result.goal_achieved,
                            case_result.agent_error,
                            case_result.steps,
                        )

                        # Opcional: LLM-as-judge
                        if not args.no_judge:
                            case_result.judge = judge_case(case_result.__dict__)

                        # Rellenar optimal_calls desde config
                        case_result.optimal_calls = scenario_meta.optimal_calls
                        case_result.config = {
                            "experiment": exp_name,
                            "variant": variant_label,
                            **config,
                        }

                        # Guardar resultado
                        from dataclasses import asdict
                        f_results.write(json.dumps(asdict(case_result)) + "\n")
                        f_results.flush()

                        # Imprimir progreso
                        status = "✓" if case_result.goal_achieved else "✗"
                        print(
                            f"    {status} {scenario_meta.id} "
                            f"({case_result.n_tool_calls}/{scenario_meta.optimal_calls}) "
                            f"{case_result.latency_s:.2f}s"
                        )

                        total_cases += 1
                        if case_result.goal_achieved:
                            passed_cases += 1

    # Generar reporte markdown
    print(f"\n{'='*60}")
    print("Generando reporte markdown...")
    report = generate_report(out_dir, out_dir / "INFORME_M3_AUTO.md")
    print(f"✓ Reporte guardado en {out_dir / 'INFORME_M3_AUTO.md'}")

    # Generar reporte visual (HTML con gráficos)
    print("Generando reporte visual...")
    try:
        html_file = generate_html_report(results_file)
        if html_file:
            print(f"✓ Visualización guardada en {html_file}")
    except Exception as e:
        print(f"⚠️  Error generando HTML: {e}")
        print("   (Continuar sin gráficos interactivos)")

    # Resumen final
    print(f"\n{'='*60}")
    print(f"RESUMEN: {passed_cases}/{total_cases} casos resueltos ({passed_cases/total_cases*100:.1f}%)")
    print(f"Resultados guardados en: {results_file}")

    return 0 if passed_cases > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
