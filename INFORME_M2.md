# Informe M2 - Agente Conversacional con Resiliencia

## 1. Estrategia de Memoria

**Implementación:** Sliding window obligatorio con recencia garantizada.

**Cómo funciona:**
- `self._conversation_history` acumula todos los mensajes (user, assistant, tool) entre turnos.
- Antes de cada `chat()`, se aplica `_apply_sliding_window()` que limita la lista a `max_history_messages`.
- **Invariante crítica:** El último user message siempre se preserva (recencia).
- Si el historial supera el límite, se descartan mensajes antiguos (FIFO), comenzando desde el más antiguo, pero manteniendo el último user message intacto.
- System prompt no se incluye en el conteo de mensajes.

**Tradeoffs:**
- **Ventaja:** Simplicidad O(1) espacial, sin acceso a DB ni resúmenes costosos. Ideal para conversaciones hasta ~100 turnos con presupuestos típicos.
- **Limitación:** Contexto antiguo se pierde irreversiblemente. Para conversaciones largas (1000+ turnos) o donde es crítico recuperar detalles tempranos, estrategias como summarization o retrieval-augmented serían mejores.

**Juicio:** Se elige sliding window porque el TP exige estrategia simple, obligatoria y determinista. La recencia preserva la inteligencia del LLM en el turno actual, que es lo más importante.

---

## 2. Salida Estructurada

**Cómo se ofrece `final_result` al LLM:**
- `structured_call(prompt, schema)` crea una tool sintética con `final_result_tool_schema(schema)` (generador Pydantic en `mia_agents.tool_schema`).
- Esa tool se pasa como `tools=[final_result_tool]` en la primera y todas las llamadas a `chat()`.
- El LLM ve que `final_result` es su único camino válido para terminar.

**Validación de argumentos:**
- Se parsean los `arguments` (JSON) del tool_call con `json.loads()`.
- Se validan contra el schema con `schema.model_validate(arguments)`.
- Si validación pasa, se retorna la instancia.
- Si falla (tipos incorrectos, campos faltantes, restricciones), se captura la excepción.

**Reparación ante fallos:**
1. **Sin tool_call (texto libre):** Se agrega mensaje de tool indicando que debe invocar `final_result`.
2. **JSON malformado:** Se reporta el error de parseo.
3. **Validación fallida:** Se reporta el error de Pydantic (ej: "field 'result' must be int, not str").
4. En cada caso se reintenta con el error incluido en los mensajes.

**Límite de reintentos:**
- Loop corre desde `attempt=0` hasta `attempt=max_repair_attempts` (default 2).
- En cada fallo, se agrega contexto y se continúa.
- Tras agotar reintentos (3 llamadas totales con default), se levanta excepción limpia (ValidationError o ValueError según el error).
- **Nunca retorna `None` o valores parciales.**

---

## 3. Errores Recuperables en Herramientas

### Calculadora

**Errores detectados:**

| Error | Condición | Mensaje | Recuperable |
|-------|-----------|---------|-------------|
| Operando 1 no numérico | `float(operand1)` falla | `"Error: operand1 recibió X. Esperado número válido."` | ✓ LLM corrige tipo |
| Operando 2 no numérico | `float(operand2)` falla | `"Error: operand2 recibió Y. Esperado número válido."` | ✓ LLM corrige tipo |
| Operador inválido | `op not in ["+", "-", "*", "%"]` | `"Error: operador 'X' no soportado. Permitidos: +, -, *, %"` | ✓ LLM elige operador válido |
| Módulo por cero | `num2 == 0` y `op == "%"` | `"Error: módulo por cero no permitido (num1=X, num2=0)."` | ✓ LLM usa distinto divisor |
| División por cero | `ZeroDivisionError` | `"Error: división por cero no permitida (num1=X, num2=0)."` | ✓ LLM usa distinto divisor |

**Ejemplo de recuperación:** LLM intenta `calculator("cuarenta", "+", 2)` → recibe `"Error: operand1 recibió 'cuarenta'. Esperado número válido."` → reintenta con `calculator(40, "+", 2)` → éxito.

### Lector de Archivos

**Errores detectados:**

| Error | Condición | Mensaje | Recuperable |
|-------|-----------|---------|-------------|
| Ruta vacía | `not file_path` | `"Error: la ruta está vacía. Proporciona una ruta relativa válida."` | ✓ LLM proporciona ruta |
| Ruta absoluta | `file_path.startswith("/")` | `"Error: no se permiten rutas absolutas. Usa rutas relativas."` | ✓ LLM remove prefijo `/` |
| Escape de directorio | `".." in file_path` | `"Error: no se permiten '..' en la ruta. Usa rutas relativas sin escapar."` | ✓ LLM simplifica ruta |
| Archivo no existe (dir existe) | `not path.exists()` y padre es dir | `"Error: el archivo 'X' no existe. Archivos disponibles en 'Y': [lista]"` | ✓ LLM elige de lista |
| Es directorio | `path.is_dir()` | `"Error: 'X' es un directorio, no un archivo. Archivos dentro: [lista]"` | ✓ LLM elige archivo de lista |
| No es UTF-8 | `UnicodeDecodeError` | `"Error: el archivo 'X' no es texto válido (UTF-8)."` | ✗ No recuperable (binario) |

**Ejemplo de recuperación:** LLM intenta `file_reader("archivo_inexistente.txt")` en directorio `docs/` → recibe `"Error: el archivo 'archivo_inexistente.txt' no existe. Archivos disponibles en 'docs': ['readme.md', 'guide.txt']"` → reintenta con `file_reader("docs/readme.md")` → éxito.

---

## 4. Modos de Fallo Deliberadamente Fuera del Alcance

- **Persistencia de conversación entre sesiones:** `_conversation_history` es en memoria. Cerrar la app pierde historial. Alternativa: serializar a DB.
- **Summarization de contexto antiguo:** No se implementa resumen automático. Alternativa: detectar limite próximo y pedir al LLM resumen.
- **Retrieval-augmented context:** No se implementa indexación/búsqueda de turnos antiguos. Alternativa: vector DB + embedding.
- **Reintentos con backoff exponencial:** No se implementa delay en reintentos transitorios (tests son deterministas). Alternativa: `time.sleep(2 ** attempt)`.
- **Herramientas con estado interno:** Las herramientas son stateless. No hay cache de cálculos previos.
- **Validación de argumentos en cliente LLM:** Solo se valida post-hoc en el agente. El LLM no recibe restricciones JSON Schema robustas.

---

## Verificación de Criterios de Aprobación

- ✅ **Conversación multi-turno:** Segundo turno ve primer turno (statefulness).
- ✅ **Presupuesto respetado:** Historial nunca supera `max_history_messages`.
- ✅ **final_result ofrecida:** Tool presente en primera llamada de `structured_call`.
- ✅ **Reparación de validación:** Intentos fallidos con argumentos inválidos se reintentean y se recuperan.
- ✅ **Excepción tras reintentos:** Agotar `max_repair_attempts` levanta excepción (no `None`).
- ✅ **Token tracking:** `input_tokens` y `output_tokens` suman correctamente desde cada `LLMResponse`.
