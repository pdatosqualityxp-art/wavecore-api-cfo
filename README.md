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
   dentro de `.env`. No compartas ni subas este archivo al repositorio.

4. Prepara Supabase:
   - Ejecuta el SQL de las tablas `documentos` y `document_chunks` que aparece
     en [AGENTS.md](./AGENTS.md).
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

## Configuración para producción

El CORS actual permite peticiones desde cualquier origen para facilitar el
desarrollo. Antes de desplegar, limita `allow_origins` en `backend/main.py` a los
dominios del frontend.
