# Wavecore API CFO

API backend para la ingesta de documentos PDF del asistente CFO. Está construida
con FastAPI y utiliza Supabase para almacenamiento y persistencia, y Google Gemini
para generar embeddings de 768 dimensiones.

## Requisitos

- Git
- Python 3.12
- Un proyecto de Supabase
- Una API key de Google Gemini

## Instalación en un equipo nuevo

1. Clona el repositorio:

   ```powershell
   git clone <URL_DEL_REPOSITORIO>
   cd wavecore-api-cfo
   ```

2. Si Python 3.12 no está instalado, instálalo con Python Install Manager:

   ```powershell
   py install 3.12
   ```

3. Crea el archivo local de variables de entorno en la raíz del repositorio:

   ```powershell
   Copy-Item .env.example .env
   ```

   Configura `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` y `GEMINI_API_KEY`
   dentro de `.env`. Opcionalmente, configura `GEMINI_AGENT_MODEL` y
   `GEMINI_EMBEDDING_MODEL`; por defecto se usan `gemini-3.5-flash-lite` y
   `gemini-embedding-001`, respectivamente. Las variables del entorno del
   proceso prevalecen sobre los valores de `.env`. No compartas ni subas este
   archivo al repositorio.

4. Prepara Supabase:
   - Ejecuta el SQL de las tablas `documentos` y `document_chunks` que aparece
     en [AGENTS.md](./AGENTS.md).
   - Ejecuta [spec/agent_cfo.sql](./spec/agent_cfo.sql) para crear las funciones
     de consulta de solo lectura del agente CFO.
     Si ya se había aplicado una versión anterior, vuelve a ejecutar el archivo
     actualizado para añadir la búsqueda PDF filtrada por título y página.
   - Crea el bucket privado `waveStorageTest` en Supabase Storage.

5. Entra en `backend`, crea y activa el entorno virtual e instala las dependencias:

   ```powershell
   Set-Location backend
   py -3.12 -m venv venv
   .\venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. Inicia la API desde la carpeta `backend`, con el entorno virtual activo:

   ```powershell
   python -m uvicorn main:app --reload --reload-dir ./app
   ```

   Si Python 3.12 ya está instalado, se puede omitir `py install 3.12`.
   Ejecutar Uvicorn con `python -m` asegura que se use el paquete instalado en
   el entorno virtual activo. `--reload-dir ./app` limita la recarga automática
   a los cambios en el código de la aplicación.

   La API estará disponible en `http://127.0.0.1:8000`. La documentación
   interactiva de FastAPI se encuentra en `http://127.0.0.1:8000/docs`.

## Ingesta de documentos

El endpoint `POST /api/documents/ingest` recibe un PDF como `multipart/form-data`
junto con los campos `titulo`, `tipo_documento`, `departamento_origen`,
`fecha_emision` (formato `YYYY-MM-DD`) y, opcionalmente, `resumen_ejecutivo`.
El servicio almacena el PDF, extrae texto por página, lo fragmenta y guarda los
embeddings junto con los metadatos.

## Agente CFO

El endpoint `POST /api/agent_cfo` recibe un JSON con la propiedad `question`.
El agente puede combinar búsqueda semántica sobre los PDF con informes de solo
lectura y consultas limitadas a todas las tablas de negocio definidas en
`spec/database.sql`. Las consultas directas a tablas (incluido el catálogo de
productos) se paginan hasta 50 filas; las consultas de stock se paginan hasta 50
ubicaciones. Si hay más resultados, la respuesta indica que la lista está
incompleta. Las preguntas de conteo usan una RPC de conteo exacto y no cuentan
filas de muestra. Para agregados se usan informes específicos. Devuelve una
respuesta en español que termina
indicando el modelo utilizado; también devuelve el identificador del modelo en
`model`. `consulted_sources` indica las tablas o documentos consultados aunque no
se encuentren filas y `sources` contiene las evidencias recuperadas. Las consultas
SQL se limitan a funciones RPC predefinidas en
`spec/agent_cfo.sql`; no se ejecuta SQL generado por el modelo ni se permiten
escrituras. Los recuentos de tablas y rankings de intervenciones por
establecimiento se calculan sobre todas las filas antes de limitar la respuesta.
Cuando se especifica un título o página del PDF, esos filtros se aplican durante
la recuperación de fragmentos. Para habilitar la lectura de todas las tablas,
aplica de nuevo el SQL actualizado de
`spec/agent_cfo.sql` en Supabase.

El endpoint utiliza la clave de servicio de Supabase. En este proyecto se asume
que la autenticación y protección de acceso se aplican fuera del backend.
Cada consulta se registra en `chat_logs` con el modelo, prompt, respuesta, uso
de tokens, IP del cliente y `api = "2 FastAPI"`; las consultas fallidas también
se registran con una respuesta genérica de error. La tabla debe existir en
Supabase antes de utilizar el endpoint.

## Configuración para producción

El CORS actual permite peticiones desde cualquier origen para facilitar el
desarrollo. Antes de desplegar, limita `allow_origins` en `backend/main.py` a los
dominios del frontend.
