"""Herramienta para contar palabras en un texto."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from mia_agents.types import ToolSchema


def word_counter(
    text: Annotated[str, Field(description="El texto en el cual contar las palabras.")],
) -> str:
    """Cuenta el número de palabras en un texto dado.

    Divide el texto por espacios en blanco.
    """
    words = text.split()
    word_count = len(words)
    return f"El texto contiene {word_count} palabra(s)."


word_counter_schema = ToolSchema.from_callable(word_counter)
