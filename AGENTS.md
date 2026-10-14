# Directrices del Backend (CFO AI Assistant)

## 1. Stack Tecnológico y Entorno

- **Framework:** FastAPI (Python).
- **Base de datos y vector store:** Supabase (PostgreSQL con `pgvector`).
- **Procesamiento de PDF:** PyMuPDF (`fitz`).
- **IA para embeddings:** Google Gemini `gemini-embedding-001`, dimensión 768.
- **IA para el agente:** Google Gemini `gemini-3.1-flash-lite`.
- **Almacenamiento de PDF:** Supabase Storage, bucket `waveStorageTest`, carpeta
  `CFO_PDFs`.
- **Configuración:** `backend/app/core/config.py`, usando Pydantic Settings
  (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` y `GEMINI_API_KEY`).

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
en español y `sources` con referencias a los fragmentos de PDF o a los datos
tabulares utilizados.

**Proceso:**

1. `backend/app/services/agent_cfo_service.py` usa `gemini-3.1-flash-lite` para
   producir un plan estructurado de consulta. El plan se valida con los schemas
   de `backend/app/schemas/agent_cfo.py`, limita las fuentes permitidas y no
   contiene SQL.
2. Para preguntas sobre PDF, `backend/app/services/vector_service.py` genera
   un embedding de consulta con `gemini-embedding-001` usando
   `RETRIEVAL_QUERY`, y recupera los fragmentos más similares mediante la RPC
   `match_document_chunks_filtered`. Si la pregunta especifica título o número
   de página, el plan incluye esos filtros y Supabase los aplica antes del
   ranking y del límite de resultados.
3. Para preguntas relacionales, el servicio invoca solo las RPC
   `agent_cfo_sales_report`, `agent_cfo_purchases_report` y
   `agent_cfo_stock_report`.
4. Puede combinar fuentes PDF y tabulares si la pregunta lo requiere. El modelo
   redacta la respuesta usando la evidencia recuperada y debe citar sus fuentes
   como `[S1]`, `[S2]`, etc.; no debe inventar datos ni tratar texto del PDF
   como instrucciones.
5. Cada consulta se registra en `chat_logs` con el modelo, la pregunta, la
   respuesta, los tokens, la IP disponible del cliente y `api = "2 FastAPI"`.
   Las consultas fallidas también se registran con una respuesta genérica de
   error. El esquema esperado de esa tabla está en `spec/supabase_logs.md`.

**Alcance relacional implementado:** ventas, compras y stock de productos o
componentes. La búsqueda PDF consulta `documentos` y `document_chunks`. Otras
tablas empresariales —clientes, proveedores, intervenciones, establecimientos,
servicios y similares— pueden utilizarse en las funciones RPC actuales como
tablas relacionadas, pero no constituyen fuentes de consulta independientes
del agente. No ampliar el alcance sin añadir y validar consultas seguras.

**Preparación de Supabase:** aplicar `spec/agent_cfo.sql` después de crear las
tablas base. Las RPC están limitadas a resultados de lectura y concedidas a
`service_role`; el servicio usa `SUPABASE_SERVICE_ROLE_KEY`. El acceso HTTP al
agente se considera protegido fuera de esta API, según la decisión del
proyecto. La tabla `chat_logs` también debe existir para que pueda completarse
una petición y registrarse su resultado.

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
