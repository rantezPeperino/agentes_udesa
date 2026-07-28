# Pasos para Ejecutar la Herramienta de Calculadora y Otras Herramientas

## Descripción General

Se han implementado las tres herramientas obligatorias del Milestone 1:

1. **Calculadora** - Operaciones aritméticas simples (+, -, *, %)
2. **Lector de Archivos** - Lectura de archivos de texto UTF-8
3. **Contador de Palabras** - Herramienta libre para contar palabras en un texto

## Archivos Creados

```
student_framework/tools/
├── calculator.py       # Herramienta de calculadora
├── file_reader.py      # Lector de archivos
└── word_counter.py     # Contador de palabras
```

## Implementación en el Agente

Las herramientas se registran automáticamente en `student_framework/__init__.py` en la función `build_agent()`:

```python
from student_framework.tools.calculator import calculator, calculator_schema
from student_framework.tools.file_reader import file_reader, file_reader_schema
from student_framework.tools.word_counter import word_counter, word_counter_schema

agent.register_tool(calculator, calculator_schema)
agent.register_tool(file_reader, file_reader_schema)
agent.register_tool(word_counter, word_counter_schema)
```

## Pasos para Ejecutar

### 1. Configurar el Entorno

```bash
# Navegar al directorio del proyecto
cd /home/rantez/MIA/agentes/tp_mia_agentes_2026

# Activar el entorno virtual (si no está activado)
source .venv/bin/activate
```

### 2. Ejecutar los Tests de Conformidad

Para verificar que todo funciona correctamente:

```bash
python -m pytest tests/conformance/test_m1.py -v
```

### 3. Ejecutar Demostración sin Credenciales (Recomendado)

Para ver las herramientas en acción sin necesidad de credenciales:

```bash
python demo_tools.py
```

Este script demuestra:
- ✓ Calculadora (25 * 4)
- ✓ Lector de archivos
- ✓ Contador de palabras
- ✓ Respuesta sin herramientas

### 4. Usar el Agente Interactivamente (CLI con Credenciales)

Para usar el agente con un LLM real (requiere variables de entorno configuradas para Bedrock u Ollama):

```bash
python -m mia_agents.cli run --message "¿Cuánto es 2 + 3?"
```

Sintaxis completa:
```bash
python -m mia_agents.cli run \
  --module student_framework \
  --message "Tu pregunta aquí"
```

### 5. Ejemplos de Uso

Para usar con credenciales configuradas, reemplaza `--message` con tu pregunta:

#### Ejemplo 1: Calculadora

```bash
python -m mia_agents.cli run --message "¿Cuánto es 15 * 7?"
```

El agente reconocerá que necesita usar la calculadora y ejecutará la operación.

#### Ejemplo 2: Lector de Archivos

```bash
python -m mia_agents.cli run --message "Lee el contenido del archivo ENUNCIADO_M1.md"
```

#### Ejemplo 3: Contador de Palabras

```bash
python -m mia_agents.cli run --message "Cuántas palabras hay en 'Hola mundo esto es un ejemplo de contador de palabras'"
```

### 5. Parámetros de Configuración

El agente puede configurarse con los siguientes parámetros:

- `--message`: Mensaje del usuario
- `--system`: System prompt personalizado (opcional)
- `--max-iterations`: Máximo de iteraciones del bucle (por defecto: 10)
- `--max-history-messages`: Máximo de mensajes en historial (por defecto: 50)

## Detalles Técnicos

### Estructura de Herramientas

Cada herramienta sigue el patrón:

```python
from typing import Annotated
from pydantic import Field
from mia_agents.types import ToolSchema

def tool_function(
    param: Annotated[type, Field(description="Descripción del parámetro")],
) -> str:
    """Docstring que describe la herramienta para el LLM."""
    # Implementación
    return resultado

tool_schema = ToolSchema.from_callable(tool_function)
```

### Bucle del Agente

El bucle del agente funciona así:

1. **Primera llamada**: Envía el mensaje del usuario al LLM con las herramientas disponibles
2. **Análisis**: El LLM decide si necesita una herramienta o puede responder directamente
3. **Ejecución**: Si se necesita una herramienta, el agente la ejecuta y captura el resultado
4. **Retroalimentación**: Envía el resultado al LLM para que formule una respuesta final
5. **Terminación**: El bucle termina cuando:
   - El LLM responde con texto sin tool_calls
   - Se alcanza el máximo de iteraciones (10 por defecto)

### Manejo de Errores

El agente maneja los siguientes casos de error:

- **Herramienta desconocida**: Si el LLM invoca una herramienta no registrada
- **Errores en la herramienta**: Si la función lanza una excepción
- **JSON inválido**: Si los argumentos no son JSON válido
- **Máximo de iteraciones**: Si el bucle alcanza el límite sin obtener respuesta

## Verificación

Para verificar que la implementación es correcta, ejecuta:

```bash
python -m pytest tests/conformance/test_m1.py -v
```

Todos los tests deben pasar:
- ✓ test_build_agent_factory_exists
- ✓ test_run_returns_agent_result
- ✓ test_no_tool_no_loop
- ✓ test_register_tool_signature
- ✓ test_tool_is_executed_when_called

## Notas Importantes

1. Las herramientas se registran en orden: calculadora, lector de archivos, contador de palabras
2. El agente requiere un cliente LLM configurado (real o mock para tests)
3. En M1, el agente no mantiene estado entre llamadas (sin memoria de conversación)
4. El sistema es determinista con MockLLMClient, permitiendo pruebas reproducibles
