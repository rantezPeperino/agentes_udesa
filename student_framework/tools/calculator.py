"""Herramienta de calculadora simple."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from mia_agents.types import ToolSchema


def calculator(
    operand1: Annotated[float, Field(description="El primer operando numérico.")],
    operator: Annotated[Literal["+", "-", "*", "%"], Field(description="El operador a aplicar: +, -, *, o %.")],
    operand2: Annotated[float, Field(description="El segundo operando numérico.")],
) -> str:
    """Realiza una operación aritmética simple entre dos operandos.

    Soporta suma (+), resta (-), multiplicación (*) y módulo (%).
    """
    try:
        num1 = float(operand1)
    except (ValueError, TypeError):
        return f"Error: operand1 recibió {operand1!r}. Esperado número válido."

    try:
        num2 = float(operand2)
    except (ValueError, TypeError):
        return f"Error: operand2 recibió {operand2!r}. Esperado número válido."

    if operator not in ["+", "-", "*", "%"]:
        return f"Error: operador '{operator}' no soportado. Permitidos: +, -, *, %"

    try:
        if operator == "+":
            result = num1 + num2
        elif operator == "-":
            result = num1 - num2
        elif operator == "*":
            result = num1 * num2
        elif operator == "%":
            if num2 == 0:
                return f"Error: módulo por cero no permitido (num1={num1}, num2={num2})."
            result = num1 % num2
        return str(result)
    except ZeroDivisionError:
        return f"Error: división por cero no permitida (num1={num1}, num2={num2})."
    except Exception as e:
        return f"Error inesperado: {str(e)}"

calculator_schema = ToolSchema.from_callable(calculator)
