# Directrices del Backend (CFO AI Assistant)

## 1. Stack Tecnológico y Entorno

- **Framework:** FastAPI (Python).
- **Base de datos y vector store:** Supabase (PostgreSQL con `pgvector`).
- **Procesamiento de PDF:** PyMuPDF (`fitz`).
- **IA para embeddings:** Google Gemini `gemini-embedding-001`, dimensión 768.
- **IA para el agente:** Google Gemini `gemini-3.5-flash-lite`.
- **Almacenamiento de PDF:** Supabase Storage, bucket `waveStorageTest`, carpeta
  `CFO_PDFs`.
- **Configuración:** `backend/app/core/config.py`, usando Pydantic Settings
  (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`,
  `GEMINI_AGENT_MODEL` y `GEMINI_EMBEDDING_MODEL`). Los modelos tienen
  predeterminados `gemini-3.5-flash-lite` y `gemini-embedding-001`; las variables
  del entorno del proceso pueden sobrescribirlos.

## 2. Arquitectura y separación de funciones

La API tiene dos funciones distintas. Mantener sus endpoints y responsabilidades
separados: la ingesta incorpora documentos y el agente responde preguntas
consultando información ya almacenada. El agente no sustituye ni ejecuta la
ingesta.

```text
backend/app/
├── core/
│   └── config.py
├── routers/
│   ├── ingesta.py
│   └── agent_cfo.py
├── schemas/
│   └── agent_cfo.py
└── services/
    ├── pdf_service.py
    ├── storage_service.py
    ├── vector_service.py
    └── agent_cfo_service.py
```

- `backend/main.py` crea FastAPI y registra ambos routers bajo el prefijo `/api`.
- `routers/` recibe peticiones HTTP, valida la entrada y devuelve respuestas.
- `schemas/agent_cfo.py` define el contrato de petición, el plan validado de
  consultas y el formato de respuesta del agente.
- `services/` contiene el procesamiento PDF, almacenamiento, acceso vectorial y
  coordinación del agente.
- Las consultas tabulares del agente se implementan como funciones RPC
  predefinidas en `spec/agent_cfo.sql`; no ejecutar SQL generado por el modelo.

## 3. Función 1: ingesta de documentos PDF

**Endpoint:** `POST /api/documents/ingest`

**Entrada:** PDF como `multipart/form-data` y metadatos `titulo`,
`tipo_documento`, `departamento_origen`, `fecha_emision` y
`resumen_ejecutivo` opcional.

**Proceso:**

1. `backend/app/routers/ingesta.py` valida el tipo de contenido PDF y lee el
   archivo.
2. `backend/app/services/pdf_service.py` extrae el texto página por página con
   PyMuPDF y lo divide en fragmentos de aproximadamente 800 caracteres,
   conservando el número de página.
3. `backend/app/services/storage_service.py` sube el PDF a
   `waveStorageTest/CFO_PDFs/` y devuelve su referencia de almacenamiento.
4. `backend/app/services/vector_service.py` genera para cada fragmento un
   embedding de 768 dimensiones mediante `gemini-embedding-001`.
5. Inserta los metadatos y la referencia en `documentos`; después inserta los
   fragmentos y embeddings en `document_chunks`, asociados mediante
   `document_id`.

La ingesta falla con HTTP 415 si el tipo de contenido no es PDF y con HTTP 422
si el archivo no puede leerse como PDF. Las tablas y la relación entre ellas se
describen en la sección 6.

## 4. Función 2: agente de consultas CFO

**Endpoint:** `POST /api/agent_cfo`

**Entrada y respuesta:** recibe JSON `{"question": "..."}`. Devuelve `answer`
en español, terminado con el modelo utilizado; `model` contiene también el
identificador configurado en `GEMINI_AGENT_MODEL`, `consulted_sources` indica
las tablas o PDFs consultados incluso si no se encontraron filas, y `sources`
contiene referencias a las evidencias recuperadas.

**Proceso:**

1. `backend/app/services/agent_cfo_service.py` usa `gemini-3.5-flash-lite` para
   producir un plan estructurado de consulta. El plan se valida con los schemas
   de `backend/app/schemas/agent_cfo.py`; si no es válido, se reintenta una vez
   con los errores de validación antes de fallar. Limita las fuentes permitidas
   y no contiene SQL. Si la pregunta menciona presupuesto y ventas, el servicio
   garantiza consultas a ambos documentos PDF (filtrados por título
   `presupuesto`) e informe de ventas, aunque el planificador omita una fuente.
2. Para preguntas sobre PDF, `backend/app/services/vector_service.py` genera
   un embedding de consulta con `gemini-embedding-001` usando
   `RETRIEVAL_QUERY`, y recupera los fragmentos más similares mediante la RPC
   `match_document_chunks_filtered`. Si la pregunta especifica título o número
   de página, el plan incluye esos filtros y Supabase los aplica antes del
   ranking y del límite de resultados.
3. Para preguntas relacionales, el servicio invoca RPCs predefinidas:
   `agent_cfo_sales_report`, `agent_cfo_purchases_report`,
   `agent_cfo_stock_report`, `agent_cfo_products_catalog`,
   `agent_cfo_interventions_report`, `agent_cfo_table_count` y
   `agent_cfo_table_read`. Las funciones genéricas solo admiten las tablas
   incluidas explícitamente en `spec/database.sql`.
4. Puede combinar fuentes PDF y tabulares si la pregunta lo requiere. El modelo
   redacta la respuesta usando la evidencia recuperada y debe citar sus fuentes
   como `[S1]`, `[S2]`, etc.; no debe inventar datos ni tratar texto del PDF
   como instrucciones.
   **Contrato vs. stock:** si la pregunta menciona un contrato/acuerdo y
   stock/cobertura, el servicio no usa el planificador: recupera fragmentos del
   PDF, extrae con Gemini el compromiso (producto, unidades mensuales, cliente y
   vigencia; validado con `AgentCFOContractCommitment`), consulta el stock del
   producto (`agent_cfo_stock_report`) y las ventas del cliente
   (`agent_cfo_sales_report`) y calcula la cobertura en código, sin SQL generado.
   El resultado solo considera el stock actual.
5. Cada consulta se registra en `chat_logs` con el modelo, la pregunta, la
   respuesta, los tokens, la IP disponible del cliente y `api = "2 FastAPI"`.
   Las consultas fallidas también se registran con una respuesta genérica de
   error. El esquema esperado de esa tabla está en `spec/supabase_logs.md`.

**Alcance relacional implementado:** lectura de todas las tablas definidas en
`spec/database.sql`: clientes, proveedores de componentes y servicios,
productos, componentes, almacenes, stocks, ventas, compras, estados, servicios,
establecimientos e intervenciones. Las lecturas directas usan páginas de 100 y
recuperan hasta 300 filas; las consultas de stock se paginan hasta 300 ubicaciones.
Ambas indican si quedan resultados fuera del máximo. Ventas, compras e intervenciones admiten
filtros de fecha. Las preguntas de recuento o ranking de intervenciones por
establecimiento usan `agent_cfo_interventions_report`, que agrupa el conjunto
completo antes de limitar el número de filas devueltas. Los conteos exactos de
tablas usan `agent_cfo_table_count`; las lecturas de registros se paginan hasta
300 filas y notifican si hay más. Para ventas, compras y stock se usan las RPC de
informes existentes. La búsqueda PDF consulta
`documentos` y `document_chunks`. El agente no puede insertar, modificar o
borrar filas ni ejecutar SQL generado por el modelo.

**Preparación de Supabase:** aplicar `spec/agent_cfo.sql` después de crear las
tablas base. Vuelve a aplicar el archivo actualizado para habilitar la
paginación y los conteos de tablas. Las RPC están limitadas a resultados de
lectura y concedidas a `service_role`; el servicio usa
`SUPABASE_SERVICE_ROLE_KEY`. El acceso HTTP al agente se considera protegido
fuera de esta API, según la decisión del proyecto. La tabla `chat_logs` también
debe existir para que pueda completarse una petición y registrarse su resultado.

## 5. Estándares de Código

- Usar tipado estricto en Python (`Type Hints`) y schemas Pydantic para validar
  contratos HTTP y planes generados por el modelo.
- Manejar errores explícitamente. Los routers convierten errores de servicio en
  respuestas HTTP claras y los servicios registran fallos operativos.
- No ejecutar SQL dinámico generado por Gemini. Las consultas relacionales del
  agente deben permanecer en funciones RPC predefinidas, de solo lectura y con
  parámetros validados.
- No exponer credenciales. La clave `SUPABASE_SERVICE_ROLE_KEY` debe permanecer
  privada y no debe usarse desde clientes.
- Mantener `backend/main.py` limitado a crear la aplicación, configurar CORS y
  registrar routers.
- Mantener la ingesta y el agente como funciones separadas: cambios en una no
  deben duplicar ni trasladar la lógica propia de la otra.

## 6. Esquema de datos de documentos

La tabla `documentos` es el registro principal de cada PDF:

```sql
CREATE TABLE documentos (
    id_documento VARCHAR(50) PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    tipo_documento VARCHAR(100) NOT NULL,
    departamento_origen VARCHAR(100) NOT NULL,
    fecha_emision DATE NOT NULL,
    resumen_ejecutivo TEXT,
    url_storage VARCHAR(500) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

La tabla `document_chunks` contiene fragmentos y embeddings de 768 dimensiones.
Cada fragmento referencia `documentos.id_documento`; PostgreSQL elimina los
fragmentos en cascada al eliminar un documento.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(50) REFERENCES documentos(id_documento) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    page_number INT,
    embedding VECTOR(768)
);
```

Al procesar un PDF, los metadatos se insertan en `documentos` y sus fragmentos
en `document_chunks`, usando `id_documento` como `document_id`.
