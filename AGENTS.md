# AGENTS.md - Directrices para el Backend (CFO AI Assistant)

## 1. Stack Tecnológico y Entorno
- **Framework:** FastAPI (Python)
- **Base de datos & Vector Store:** Supabase (PostgreSQL con extensión `pgvector`)
- **Procesamiento de PDF:** PyMuPDF (`fitz`)
- **Inteligencia Artificial:** Google Gemini API (Modelo de Embeddings con dimensión 768)
- **Almacenamiento:** Supabase Storage (Bucket privado `waveStorageTest`, carpeta `CFO_PDFs`)

## 2. Arquitectura del Proyecto (Modular)
El código debe mantenerse estrictamente separado en la siguiente estructura dentro de `backend/app/`:
- `routers/`: Endpoints de FastAPI. Contiene `ingesta.py` (subida y procesamiento de PDFs) y `consulta.py` (futuro RAG).
- `services/`: Lógica de negocio pesada:
  - `pdf_service.py`: Extracción de texto página por página y funciones de *chunking* (fragmentos controlados de ~800 caracteres).
  - `vector_service.py`: Conexión con la API de Gemini para generar vectores de 768 dimensiones e inserción en Supabase (`pgvector`).
  - `storage_service.py`: Gestión de subida de archivos al bucket de Supabase Storage.
- `core/`: Configuración centralizada (`config.py`) usando Pydantic Settings para variables de entorno (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`).

## 3. Reglas de Negocio para la Ingesta (Paso 1)
Cuando se reciba un PDF junto con sus metadatos (título, tipo de documento, departamento de origen, fecha de emisión, resumen ejecutivo):
1. **Storage:** Subir el archivo físico del PDF a la ruta `CFO_PDFs/` dentro del bucket `waveStorageTest`. Obtener su URL pública o referencia en el storage.
2. **Base de Datos (Tabla Principal):** Insertar un registro en la tabla `documentos` con los metadatos y la URL del storage. (Nota: Las tablas tienen RLS deshabilitado temporalmente para desarrollo).
3. **Procesamiento de Texto (Chunking):** Leer el PDF página por página con PyMuPDF. Dividir el texto en fragmentos (*chunks*) óptimos para la búsqueda semántica.
4. **Vectorización y Carga:** 
   - Llamar a la API de Google Gemini para convertir cada fragmento de texto en un vector de 768 dimensiones.
   - Insertar los fragmentos, el número de página, el `document_id` y su respectivo vector en la tabla `document_chunks`.

## 4. Estándares de Código
- Usar tipado estricto en Python (`Type Hints`).
- Manejar excepciones de forma robusta devolviendo códigos de error HTTP claros en FastAPI (`HTTPException`).
- Mantener el fichero `main.py` limpio, limitándose a instanciar FastAPI, configurar CORS básicos y registrar los routers de la carpeta `app/routers/`.

## 5. Esquema de Base de Datos

La tabla `documentos` es el registro principal de cada documento:

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

La tabla `document_chunks` contiene los fragmentos y sus embeddings de 768 dimensiones.
Cada fragmento referencia `documentos.id_documento`; al eliminar un documento,
PostgreSQL elimina sus fragmentos en cascada.

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

Al procesar un documento, insertar primero sus metadatos en `documentos` y después
sus fragmentos en `document_chunks`, usando el `id_documento` como `document_id`.
