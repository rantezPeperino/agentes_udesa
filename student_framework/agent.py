"""Implementación de su agente.

Completen `register_tool` y `run` para el Milestone 1.
En el Milestone 2 amplíen `MyAgent` para que sea estatal y respete
`max_history_messages`.

Los tests de conformidad en `tests/conformance/test_m1.py` y
`test_m2.py` describen con precisión qué comportamientos deben funcionar
— léanlos antes de empezar.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from mia_agents.protocols import LLMClient
from mia_agents.types import AgentResult, AgentStep, ToolSchema


class MyAgent:
    def __init__(
        self,
        llm_client: LLMClient,
        system_prompt: str = "Eres un asistente útil.",
        max_iterations: int = 30,
        max_history_messages: int = 50,
    ) -> None:
        """Inicializa el agente.

        Parameters
        ----------
        llm_client : LLMClient
            Cliente LLM (real o mock) que el agente utilizará.
        system_prompt : str
            System prompt por defecto.
        max_iterations : int
            Tope de iteraciones del bucle del agente (M1).
        max_history_messages : int
            Número máximo de mensajes que se permiten en la lista
            `messages` enviada al LLM en una única llamada. En M1 este
            valor es ignorado; el agente sólo necesita aceptarlo en su
            constructor. En M2 deben respetarlo: la longitud de la
            lista de mensajes pasada a `self._llm.chat(...)` no puede
            superar este número en ninguna llamada, sin importar la
            estrategia de memoria que elijan.
        """
        self._llm = llm_client
        self._system = system_prompt
        self._max_iterations = max_iterations
        self._max_history_messages = max_history_messages
        self._tools: dict[str, Callable[..., str]] = {}
        self._schemas: dict[str, ToolSchema] = {}
        self._conversation_history: list[dict[str, Any]] = []
        self._last_window_stats: dict[str, Any] = {}
        self._window_stats_history: list[dict[str, Any]] = []

    def register_tool(
        self,
        tool: Callable[..., str],
        schema: ToolSchema,
    ) -> None:
        """Registra una herramienta callable junto a su esquema.

        El esquema suele obtenerse con `ToolSchema.from_callable(fn)`. En
        `run`, pasá `tools=list(self._schemas.values())`; el cliente LLM
        aplica `to_llm_spec()` al llamar al proveedor.

        El callable se invoca con kwargs que coinciden con la firma.
        Debe devolver una cadena.
        """
        self._tools[schema.name] = tool
        self._schemas[schema.name] = schema

    def run(self, user_message: str) -> AgentResult:
        """Ejecuta el bucle del agente hasta una respuesta final o hasta max_iterations.

        Comportamiento esperado (consulta tests/conformance/test_m1.py
        para el contrato exacto del M1):
          - Llama a `self._llm.chat(..., tools=list(self._schemas.values()))`.
          - Si la respuesta contiene tool_calls, ejecuta cada uno y vuelca
            los resultados en la siguiente llamada al chat.
          - Si la respuesta solo contiene texto (sin `tool_calls`),
            devuélvelo en `AgentResult.answer`. En M1 no uses la tool
            sintética `final_result`; ese patrón es de M2 (ver README y
            ENUNCIADO_M2.md).
          - Limita el bucle a `self._max_iterations` y termina de forma
            limpia cuando se alcance.
          - Registra cada invocación de herramienta como un `AgentStep`
            dentro de `result.steps`.

        En el M2, además, llamadas sucesivas sobre la misma instancia
        deben continuar la conversación, y la longitud de la lista de
        mensajes enviada al LLM no debe superar `self._max_history_messages`.
        Acumula los tokens de entrada/salida reportados por los
        `LLMResponse` y exponlos en `AgentResult.input_tokens` /
        `AgentResult.output_tokens`.
        """
        self._conversation_history.append({"role": "user", "content": user_message})

        steps: list[AgentStep] = []
        total_input_tokens = 0
        total_output_tokens = 0

        for _ in range(self._max_iterations):
            messages = self._apply_sliding_window()

            response = self._llm.chat(
                messages=messages,
                tools=list(self._schemas.values()),
                system=self._system,
            )

            if response.input_tokens is not None:
                total_input_tokens += response.input_tokens
            if response.output_tokens is not None:
                total_output_tokens += response.output_tokens

            if not response.tool_calls:
                self._conversation_history.append({"role": "assistant", "content": response.content or ""})
                return AgentResult(
                    answer=response.content or "",
                    steps=steps,
                    input_tokens=total_input_tokens if total_input_tokens > 0 else None,
                    output_tokens=total_output_tokens if total_output_tokens > 0 else None,
                )

            self._conversation_history.append({
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
            })

            for tool_call in response.tool_calls:
                try:
                    arguments = json.loads(tool_call.arguments)
                except (json.JSONDecodeError, TypeError):
                    arguments = {}

                tool_name = tool_call.name
                tool_func = self._tools.get(tool_name)

                if tool_func is None:
                    error_msg = f"Herramienta desconocida: {tool_name}"
                    tool_output = error_msg
                    step_error = error_msg
                else:
                    try:
                        tool_output = tool_func(**arguments)
                        step_error = None
                    except Exception as e:
                        tool_output = f"Error al ejecutar {tool_name}: {str(e)}"
                        step_error = str(e)

                self._conversation_history.append({
                    "role": "tool",
                    "content": tool_output,
                    "tool_call_id": tool_call.id,
                })

                steps.append(AgentStep(
                    tool_name=tool_name,
                    tool_input=tool_call.arguments,
                    tool_output=tool_output,
                    error=step_error,
                ))

        return AgentResult(
            answer="Máximo de iteraciones alcanzado.",
            steps=steps,
            error="max_iterations_reached",
            input_tokens=total_input_tokens if total_input_tokens > 0 else None,
            output_tokens=total_output_tokens if total_output_tokens > 0 else None,
        )

    def _apply_sliding_window(self) -> list[dict[str, Any]]:
        """Aplica ventana deslizante con recorte consciente de bloques atómicos.

        Estrategia:
        1. Agrupa mensajes en bloques indivisibles: un `assistant` con
           `tool_calls` + todos sus `tool` consecutivos = 1 bloque. Otros
           mensajes forman bloques de 1 elemento.
        2. Selecciona bloques de atrás hacia adelante acumulando mientras
           el total no supere `max_history_messages`.
        3. Aplana en orden original y sanitiza (nunca empieza con `tool`).

        Invariantes garantizadas:
        - len(resultado) <= max_history_messages
        - resultado nunca empieza con rol "tool"
        - cada `tool` está emparejado con su `assistant` con `tool_calls`
        - si un `assistant` con `tool_calls` está presente, TODOS sus `tool`
          consecutivos también lo están
        - resultado es subsecuencia contigua del historial original
        - si historial entra en presupuesto, se devuelve copia íntegra

        Caso degenerado: si el último bloque por sí solo supera el presupuesto,
        se busca el último mensaje `user` disponible. Esto degrada el contexto
        pero permite que el agente continúe (vs. abortar). Se registra en
        `_last_window_stats["degraded"]`.
        """
        H = self._conversation_history
        m = self._max_history_messages

        # Caso trivial: todo entra.
        if len(H) <= m:
            self._last_window_stats = {
                "total_blocks": len(H),
                "sent_blocks": 1,
                "sent_messages": len(H),
                "dropped_messages": 0,
                "degraded": False,
            }
            self._window_stats_history.append(self._last_window_stats)
            return list(H)

        # Fase 1: Agrupar en bloques atómicos.
        blocks: list[list[dict[str, Any]]] = []
        i = 0
        while i < len(H):
            msg = H[i]
            if msg["role"] == "assistant" and msg.get("tool_calls"):
                # Bloque: este assistant + todos los tool consecutivos
                block = [msg]
                i += 1
                while i < len(H) and H[i]["role"] == "tool":
                    block.append(H[i])
                    i += 1
                blocks.append(block)
            else:
                # Bloque de un elemento
                blocks.append([msg])
                i += 1

        # Fase 2: Seleccionar bloques de atrás hacia adelante.
        selected_blocks: list[list[dict[str, Any]]] = []
        total = 0
        for block in reversed(blocks):
            block_size = len(block)
            if total + block_size <= m:
                selected_blocks.insert(0, block)
                total += block_size
            else:
                # El bloque no cabe. BREAK para garantizar contiguidad.
                break

        # Fase 3: Aplanar y sanear.
        R = [msg for block in selected_blocks for msg in block]
        while R and R[0]["role"] == "tool":
            R.pop(0)

        # Caso degenerado: si R quedó vacío, buscar el último `user`.
        degraded = False
        if not R:
            for msg in reversed(H):
                if msg["role"] == "user" and not msg.get("tool_calls"):
                    R = [msg]
                    degraded = True
                    break
            # Si tampoco hay `user`, R queda [] (respeta presupuesto, pero
            # mandarle a Bedrock también es error. El agente degradará aquí).

        # Registrar estadísticas.
        self._last_window_stats = {
            "total_blocks": len(blocks),
            "sent_blocks": len(selected_blocks),
            "sent_messages": len(R),
            "dropped_messages": len(H) - len(R),
            "degraded": degraded,
        }
        self._window_stats_history.append(self._last_window_stats)

        return R

    def structured_call(
        self,
        prompt: str,
        schema: Any,
        max_repair_attempts: int = 2,
    ) -> Any:
        """Pide al LLM una respuesta validada contra `schema` (M2).

        Obligatorio: herramienta sintética `final_result` (ver
        `mia_agents.final_result_tool_schema` / `FINAL_RESULT_TOOL_NAME`).
        El agente ofrece esa tool al LLM, valida los `arguments` del
        `tool_call` y reintenta con contexto de reparación si el modelo
        responde con texto libre o con argumentos inválidos.

        Implementa esto en el M2:
          - Pasa `tools=[final_result_tool_schema(schema)]` en cada
            llamada a `chat` dentro de este método.
          - Termina solo cuando llega un `tool_call` a `final_result`
            cuyos argumentos validan con `schema.model_validate(...)`.
          - Reintenta hasta `max_repair_attempts` incluyendo el fallo en
            los mensajes (respuesta previa, mensaje `tool`, o user de
            reparación).
          - Si tras los reintentos sigue fallando, levanta una excepción
            limpia (no devuelvas valores parciales ni `None` sin avisar).

        El M1 deja esto como stub; los tests de M2 verifican el contrato.
        """
        from mia_agents.tool_schema import final_result_tool_schema, FINAL_RESULT_TOOL_NAME

        final_result_tool = final_result_tool_schema(schema)
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

        for attempt in range(max_repair_attempts + 1):
            response = self._llm.chat(
                messages=messages,
                tools=[final_result_tool],
                system=self._system,
            )

            if not response.tool_calls:
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "tool",
                    "content": "No invocaste la herramienta final_result. Debes invocar la herramienta para terminar.",
                    "tool_call_id": "repair",
                })
                if attempt < max_repair_attempts:
                    continue
                else:
                    raise ValueError("El LLM no invocó final_result tras reintentos.")

            tool_call = response.tool_calls[0]
            if tool_call.name != FINAL_RESULT_TOOL_NAME:
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "tool",
                    "content": f"Debes invocar solo final_result, no {tool_call.name}.",
                    "tool_call_id": tool_call.id,
                })
                if attempt < max_repair_attempts:
                    continue
                else:
                    raise ValueError(f"El LLM invocó {tool_call.name} en lugar de final_result.")

            try:
                arguments = json.loads(tool_call.arguments)
            except (json.JSONDecodeError, TypeError) as e:
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "tool",
                    "content": f"Los argumentos no son JSON válido: {str(e)}",
                    "tool_call_id": tool_call.id,
                })
                if attempt < max_repair_attempts:
                    continue
                else:
                    raise

            try:
                parsed = schema.model_validate(arguments)
                return parsed
            except Exception as e:
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "tool",
                    "content": f"Validación fallida: {str(e)}. Reintenta con argumentos válidos.",
                    "tool_call_id": tool_call.id,
                })
                if attempt < max_repair_attempts:
                    continue
                else:
                    raise
