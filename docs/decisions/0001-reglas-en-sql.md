# 0001 · Reglas como funciones SQL

Fecha: 2026-11-18 · Estado: aceptado · Confirma: D33 (reglas)

## Contexto

Las reglas R01–R14 son el control de todo el sistema (principio 4). Tienen que ser exactamente las mismas en el flujo de n8n, en la evaluación y en el plan B de Python (D30, D33). Casi todas son validaciones contra datos maestros: buscar una tarifa, contar a cuántos clientes pertenece un email, calcular una mediana en el histórico.

## Decisión

- **Una función SQL por regla**, escrita en SQL normal (`LANGUAGE sql`) siempre que se pueda. Cada una solo lee y devuelve sus motivos.
- **Un único punto de entrada, `evaluar_caso(caso_id)`, en PL/pgSQL:** aplica R01–R04, que cortan el flujo, y R05–R14, que acumulan motivos. En la misma transacción escribe los motivos, el evento y los envíos pendientes ([sección 2.7 de 04](../04-solution-design.md#27-envío-de-correos)).
- **Hora de referencia:** la de recepción del caso, nunca la hora actual. Los datos maestros se leen como están en ese momento.
- **Umbrales en una tabla de configuración**, no en el código.
- **La API solo expone** `evaluar_caso`, las funciones de decisión de la revisión y la de registro de aprobaciones. Las funciones de decisión comprueban en el servidor el rol de quien llama, que el motivo se pueda forzar (R04, R09, R11 y R13 nunca) y la verificación por teléfono en los casos de fraude.
- **El JSON extraído se valida también en la base de datos** con `pg_jsonschema` y el mismo archivo de esquema que usa la IA, como segunda capa tras la salida estructurada del proveedor.
- **Tests con pytest**, en dos niveles:
  - por regla, conectando directamente a la base de datos local con `psycopg`, sin exponer nada;
  - de punta a punta, llamando a `evaluar_caso` por la API, como lo hacen n8n y el script.
  
  Incluyen los casos límite: 0,01 €, 48 h, la mediana con menos de 3 pedidos y la nave distinta.

## Alternativas descartadas

- **Todas las reglas en PL/pgSQL:** innecesario. Solo `evaluar_caso` necesita variables, bucles y control de flujo.
- **Un servicio de Python (FastAPI) que n8n llama y el script importa:** se lee y se prueba mejor, pero es otro servicio que desplegar, al que n8n tiene que llegar. Es la "API propia" que se descartó en D27.
- **Reglas en nodos de n8n, copiadas en el script:** ya descartada en D33. Se evaluaría algo distinto de lo que funciona.
- **pgTAP para los tests:** es otro lenguaje que aprender. pytest es el mismo lenguaje que el script de evaluación.

## Consecuencias

- Una sola fuente para n8n, la evaluación y el plan B. Las reglas se ejecutan junto a los datos que consultan y dentro de una transacción.
- Encaja con la frontera entre `erp` e `intake` ([sección 5.2 de 04](../04-solution-design.md#52-frontera-con-el-erp)).
- La lógica de negocio queda en la base de datos. Las críticas habituales (versionarla, probarla, cambiar de base de datos) se cubren con migraciones en git y tests. Si las reglas pasaran a ser algoritmos complejos, se moverían a un servicio.
- Si `pg_jsonschema` no está disponible en Supabase local, queda solo la validación de la salida estructurada (se comprueba al construir).
