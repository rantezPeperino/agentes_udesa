"""Herramienta para leer archivos de texto."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from pydantic import Field

from mia_agents.types import ToolSchema


def file_reader(
    file_path: Annotated[str, Field(description="La ruta del archivo de texto a leer.")],
) -> str:
    """Lee y devuelve el contenido de un archivo de texto.

    Solo lee archivos de texto con codificación UTF-8.
    """
    if not file_path:
        return "Error: la ruta está vacía. Proporciona una ruta relativa válida."

    if file_path.startswith("/"):
        return "Error: no se permiten rutas absolutas. Usa rutas relativas."

    if ".." in file_path:
        return "Error: no se permiten '..' en la ruta. Usa rutas relativas sin escapar."

    path = Path(file_path)
    try:
        if not path.exists():
            parent_dir = path.parent
            if parent_dir.exists() and parent_dir.is_dir():
                try:
                    files = [f.name for f in parent_dir.iterdir() if f.is_file()]
                    return f"Error: el archivo '{file_path}' no existe. Archivos disponibles en '{parent_dir}': {files}"
                except Exception:
                    return f"Error: el archivo '{file_path}' no existe."
            else:
                return f"Error: el archivo '{file_path}' no existe."

        if path.is_dir():
            try:
                files = [f.name for f in path.iterdir() if f.is_file()]
                return f"Error: '{file_path}' es un directorio, no un archivo. Archivos dentro: {files}"
            except Exception:
                return f"Error: '{file_path}' es un directorio, no un archivo."

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except UnicodeDecodeError:
        return f"Error: el archivo '{file_path}' no es texto válido (UTF-8)."
    except Exception as e:
        return f"Error al leer '{file_path}': {str(e)}"


file_reader_schema = ToolSchema.from_callable(file_reader)
