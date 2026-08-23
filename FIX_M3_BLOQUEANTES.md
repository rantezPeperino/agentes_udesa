cat > FIX_M3_BLOQUEANTES.md << 'EOF'
# Tarea: arreglar los 5 bloqueantes de M3 antes de construir eval/

## Contexto

Framework de agentes con tool-calling. M1/M2 se corrigen con `MockLLMClient`
(determinista, no valida el historial). M3 corre contra un LLM real
(AWS Bedrock Converse u Ollama) sobre escenarios de sala de escape que
requieren hasta 21 tool calls encadenadas.

Los bugs de abajo son invisibles bajo el mock pero rompen contra Bedrock
en la segunda vuelta del bucle.

## Reglas duras

- NO modificar nada dentro de `mia_agents/` — es código fijo del curso.
- NO modificar `tests/conformance/test_m1.py` ni `test_m2.py`.
- Al terminar, `pytest tests/` debe pasar en verde, sin excepción.
- Todo el código nuevo va en `student_framework/`.
- Comentarios y docstrings en español.

## BUG 1 — `run()` descarta los `tool_calls` del turno assistant

Archivo: `student_framework/agent.py`, método `run()`.

Actual:

    self._conversation_history.append(
        {"role": "assistant", "content": response.content}
    )

Problema: cuando `response.tool_calls` no está vacío, el mensaje se guarda
sin ese campo. Después `BedrockProvider._normalize_messages()` construye un
`assistant` sin bloques `toolUse`, seguido de un `toolResult` huérfano.
La API Converse exige que todo `toolResult` siga inmediatamente a su
`toolUse` -> `ValidationException`.

Arreglo: al guardar el turno assistant que SÍ pidió herramientas, incluir
`tool_calls` en el formato interno que ambos providers ya saben leer
(ver `BedrockProvider._normalize_messages` y `OllamaProvider._normalize_messages`):

    {
        "role": "assistant",
        "content": response.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": tc.arguments},
            }
            for tc in response.tool_calls
        ],
    }

Notas:
- `response.content` es `None` cuando el modelo solo pide herramientas;
  normalizar a `""` para no generar bloques de texto vacíos.
- El turno assistant FINAL (sin tool_calls) se sigue guardando como hoy,
  pero también normalizando `content` a `""` si viniera `None`.

## BUG 2 — clave equivocada en el mensaje de resultado de herramienta

Archivo: `student_framework/agent.py`, en `run()` y en `structured_call()`.

Actual: se escribe `"tool_use_id"`.
Ambos providers leen `"tool_call_id"`:

    "toolUseId": tm.get("tool_call_id", "")   # hoy devuelve siempre ""

Arreglo: renombrar la clave a `tool_call_id` en TODAS las apariciones,
tanto en `run()` como en los mensajes de reparación de `structured_call()`.
Verificar con grep que no queda ningún `tool_use_id` en `student_framework/`.

## BUG 3 — `_apply_sliding_window()` viola el presupuesto y parte pares

Archivo: `student_framework/agent.py`, método `_apply_sliding_window()`.

Problemas:
1. La rama `if latest_user_idx < len(hist) - max: return hist[latest_user_idx:]`
   devuelve `len - latest_user_idx` mensajes, que por la propia condición es
   MAYOR que `max_history_messages`. Rompe el contrato de M2.
2. Los cortes `hist[-max:]` pueden empezar en un mensaje `tool` huérfano o
   partir un bloque assistant+tool por la mitad -> historial inválido para
   Bedrock.

Arreglo: reescribir con recorte consciente de bloques.

Algoritmo:
1. Agrupar el historial en bloques atómicos recorriendo de inicio a fin:
   - un `assistant` con `tool_calls` + todos los mensajes `tool`
     consecutivos que le siguen = UN bloque;
   - cualquier otro mensaje (`user`, `assistant` sin tool_calls) = bloque
     de un solo elemento.
2. Recorrer los bloques de atrás hacia adelante acumulando mientras
   `total + len(bloque) <= max_history_messages`. Cortar al primer bloque
   que no entre.
3. Devolver los bloques seleccionados aplanados, en orden original.

Invariantes que la función debe garantizar SIEMPRE:
- `len(resultado) <= self._max_history_messages`.
- El resultado nunca empieza con un mensaje `role == "tool"`.
- Todo `assistant` con `tool_calls` presente en el resultado va seguido de
  sus mensajes `tool`; nunca aparece un `tool` sin su assistant.
- Si un único bloque ya excede el presupuesto por sí solo, devolver una
  lista vacía o solo el último mensaje `user` disponible, pero NUNCA
  superar el límite ni devolver un bloque partido.
- Si el historial completo entra en el presupuesto, devolver una copia
  íntegra (comportamiento actual).

## BUG 4 — `max_iterations = 10` es insuficiente para M3

Archivos: `student_framework/agent.py` y `student_framework/__init__.py`.

Los escenarios `vault-combination` (21 calls) y `backtracking-vault`
(18 calls) no caben en 10 iteraciones.

Arreglo:
- Subir el default de `MyAgent.__init__` a `max_iterations: int = 30`.
- Que `build_agent` lo lea de `config["max_iterations"]` si está presente,
  con el mismo patrón condicional que ya usa `max_history_messages`.
- Añadir también `config["system_prompt"]`, necesario para el experimento
  de especificidad del prompt en M3.

## BUG 5 — `build_agent` registra las herramientas equivocadas

Archivo: `student_framework/__init__.py`.

Hoy registra siempre `calculator`, `file_reader`, `word_counter`. Para M3
hacen falta las de `mia_world`, que se obtienen con
`make_world_tools(world)` y quedan acopladas a una instancia concreta de
`World` (cada escenario necesita su propio mundo y su propio agente).

Arreglo: extender `build_agent` sin romper su firma ni el comportamiento
por defecto:
- Si `config["tools"]` está presente, se espera un iterable de pares
  `(callable, ToolSchema)`; registrar esos y NO registrar los tres por
  defecto.
- Si además/en su lugar viene `config["world"]`, derivar las herramientas
  con `make_world_tools(config["world"])` (import local dentro de la
  función, para no crear dependencia dura de `mia_world` cuando no se usa).
- Si no viene ninguna de las dos, mantener exactamente el comportamiento
  actual (las tres herramientas de M1). Los tests de M1/M2 dependen de esto.
- No tocar las líneas marcadas `#NO CAMBIAR`.

## Tests nuevos

Crear `tests/test_history_integrity.py` (archivo propio, no tocar los de
conformidad). Debe cubrir, usando `MockLLMClient`:

1. Tras un `run()` con tool call, el historial contiene un `assistant` con
   la clave `tool_calls` y con el id correcto.
2. El mensaje de resultado usa la clave `tool_call_id` y no `tool_use_id`.
3. El historial producido por `run()` sobrevive a
   `BedrockProvider._normalize_messages(...)` generando, para cada
   `toolResult`, un `toolUseId` no vacío que matchea un `toolUse` previo
   en el mensaje assistant inmediatamente anterior.
4. `_apply_sliding_window()` nunca devuelve más de `max_history_messages`,
   probado sobre un historial sintético con bloques assistant+tool de
   longitud variable.
5. `_apply_sliding_window()` nunca devuelve una lista que empiece con
   `role == "tool"`.
6. Un `run()` con presupuesto chico (`max_history_messages=6`) y varias
   iteraciones de herramientas mantiene el invariante en TODAS las
   llamadas registradas en `mock.calls`.

## Verificación final

Ejecutar y pegar la salida:

    pytest tests/ -q
    grep -rn "tool_use_id" student_framework/    # debe salir vacío

Al terminar, escribir un resumen corto: qué se cambió en cada archivo y
por qué, sin repetir el código.
EOF