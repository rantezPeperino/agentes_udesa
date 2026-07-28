#!/usr/bin/env python3
"""Script de demostración para probar las herramientas del agente.

Ejecutar:
    python demo_tools.py
"""

import json
from mia_agents.testing import MockLLMClient
from mia_agents.types import LLMResponse, ToolCall
from student_framework import build_agent


def demo_calculator():
    """Demuestra el uso de la herramienta de calculadora."""
    print("\n" + "="*60)
    print("DEMO 1: Herramienta de Calculadora")
    print("="*60)

    mock = MockLLMClient([
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCall(
                    id="calc1",
                    name="calculator",
                    arguments=json.dumps({
                        "operand1": 25,
                        "operator": "*",
                        "operand2": 4
                    })
                )
            ],
        ),
        LLMResponse(content="El resultado de 25 * 4 es 100."),
    ])

    agent = build_agent({"llm_client": mock})
    result = agent.run("¿Cuánto es 25 * 4?")

    print(f"Pregunta: ¿Cuánto es 25 * 4?")
    print(f"Respuesta: {result.answer}")
    print(f"Pasos ejecutados: {len(result.steps)}")
    for i, step in enumerate(result.steps):
        print(f"  Paso {i+1}: {step.tool_name}")
        print(f"    Input: {step.tool_input}")
        print(f"    Output: {step.tool_output}")


def demo_file_reader():
    """Demuestra el uso de la herramienta de lector de archivos."""
    print("\n" + "="*60)
    print("DEMO 2: Herramienta de Lector de Archivos")
    print("="*60)

    mock = MockLLMClient([
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCall(
                    id="file1",
                    name="file_reader",
                    arguments=json.dumps({
                        "file_path": "ENUNCIADO_M1.md"
                    })
                )
            ],
        ),
        LLMResponse(content="El archivo contiene la especificación del Milestone 1."),
    ])

    agent = build_agent({"llm_client": mock})
    result = agent.run("¿Qué contiene el archivo ENUNCIADO_M1.md?")

    print(f"Pregunta: ¿Qué contiene el archivo ENUNCIADO_M1.md?")
    print(f"Respuesta: {result.answer}")
    print(f"Pasos ejecutados: {len(result.steps)}")
    for i, step in enumerate(result.steps):
        print(f"  Paso {i+1}: {step.tool_name}")
        print(f"    Input: {step.tool_input}")
        print(f"    Output (primeras 100 chars): {step.tool_output[:100]}...")


def demo_word_counter():
    """Demuestra el uso de la herramienta de contador de palabras."""
    print("\n" + "="*60)
    print("DEMO 3: Herramienta de Contador de Palabras")
    print("="*60)

    mock = MockLLMClient([
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCall(
                    id="words1",
                    name="word_counter",
                    arguments=json.dumps({
                        "text": "Hola mundo esto es un ejemplo de contador de palabras"
                    })
                )
            ],
        ),
        LLMResponse(content="La frase tiene 9 palabras."),
    ])

    agent = build_agent({"llm_client": mock})
    result = agent.run("¿Cuántas palabras hay en 'Hola mundo esto es un ejemplo de contador de palabras'?")

    print(f"Pregunta: ¿Cuántas palabras hay en 'Hola mundo esto es un ejemplo de contador de palabras'?")
    print(f"Respuesta: {result.answer}")
    print(f"Pasos ejecutados: {len(result.steps)}")
    for i, step in enumerate(result.steps):
        print(f"  Paso {i+1}: {step.tool_name}")
        print(f"    Input: {step.tool_input}")
        print(f"    Output: {step.tool_output}")


def demo_sin_herramientas():
    """Demuestra el agente respondiendo sin necesidad de herramientas."""
    print("\n" + "="*60)
    print("DEMO 4: Respuesta sin Herramientas")
    print("="*60)

    mock = MockLLMClient([
        LLMResponse(content="El Milestone 1 es sobre construir el bucle básico del agente."),
    ])

    agent = build_agent({"llm_client": mock})
    result = agent.run("¿Qué es el Milestone 1?")

    print(f"Pregunta: ¿Qué es el Milestone 1?")
    print(f"Respuesta: {result.answer}")
    print(f"Herramientas utilizadas: {len(result.steps)}")


if __name__ == "__main__":
    print("\n🤖 DEMOSTRACIÓN DE HERRAMIENTAS DEL AGENTE\n")

    demo_calculator()
    demo_file_reader()
    demo_word_counter()
    demo_sin_herramientas()

    print("\n" + "="*60)
    print("✅ Todas las demostraciones completadas exitosamente")
    print("="*60 + "\n")
