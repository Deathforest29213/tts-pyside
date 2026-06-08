# CONSTRUCTION.md

Guia para reconstruir y replicar `md2audio` en otro dispositivo.

## Objetivo del proyecto

`md2audio` convierte archivos Markdown (`.md`) en audios MP3 para estudio.

El motor principal es Kokoro local/offline y el motor alternativo es Edge TTS online.

## Requisitos del sistema

- Windows 10/11.
- Miniconda o Anaconda.
- Python 3.12 dentro del entorno Conda `tts-pyside`.
- Conexion a internet solo para instalacion inicial y descarga de modelos.
- `ffmpeg.exe` disponible en el sistema.
- Espacio libre recomendado: al menos 1 GB.

El proyecto ya detecta `ffmpeg` si esta en `PATH` o en rutas comunes como:

```text
C:\Program Files\Krita (x64)\bin\ffmpeg.exe
C:\ProgramData\chocolatey\bin\ffmpeg.exe
C:\ffmpeg\bin\ffmpeg.exe
```

Si no lo detecta, se puede pasar manualmente:

```powershell
python main.py convert .\input --ffmpeg "C:\ruta\a\ffmpeg.exe"
```

## Estructura esperada

```text
md2audio/
├── main.py
├── requirements.txt
├── README.md
├── CONSTRUCTION.md
├── input/
├── output/
├── models/
│   └── kokoro/
│       ├── kokoro-v1.0.onnx
│       └── voices-v1.0.bin
└── src/
    ├── cli.py
    ├── parser.py
    ├── chunker.py
    ├── normalizer.py
    ├── audio.py
    └── engines/
        ├── base.py
        ├── edge.py
        └── kokoro.py
```

## Dependencias Python

El archivo `requirements.txt` debe incluir:

```text
edge-tts==7.2.8
kokoro-onnx==0.5.0
mypy==1.17.1
pre-commit==4.3.0
PySide6==6.11.1
ruff==0.12.12
soundfile==0.14.0
```

Crear entorno Conda e instalar:

```powershell
cd C:\ruta\a\md2audio
conda env create -f environment.yml
conda activate tts-pyside
```

Si el entorno ya existe:

```powershell
conda activate tts-pyside
python -m pip install -r requirements.txt
```

Instalar hooks de calidad de codigo:

```powershell
pre-commit install
```

Ejecutar validacion completa manual:

```powershell
pre-commit run --all-files
```

## Modelos Kokoro

Kokoro necesita dos archivos locales:

```text
models/kokoro/kokoro-v1.0.onnx
models/kokoro/voices-v1.0.bin
```

Tamanos aproximados actuales:

```text
kokoro-v1.0.onnx  325 MB
voices-v1.0.bin    28 MB
```

Descarga manual con PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path .\models\kokoro | Out-Null

Invoke-WebRequest `
  -Uri "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx" `
  -OutFile ".\models\kokoro\kokoro-v1.0.onnx"

Invoke-WebRequest `
  -Uri "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" `
  -OutFile ".\models\kokoro\voices-v1.0.bin"
```

Despues de esta descarga inicial, Kokoro puede generar audio sin internet.

## Motores TTS

### Kokoro

- Motor principal por defecto.
- Funciona offline despues de descargar modelos.
- Voz por defecto del proyecto: `em_santa`.
- Idioma por defecto: `es`.
- Parametro de velocidad: `--speed`.

Voces espanolas disponibles:

```text
ef_dora
em_alex
em_santa
```

Listar voces:

```powershell
python main.py voices --engine kokoro --locale es
```

### Edge TTS

- Motor alternativo online.
- Requiere internet.
- Voz sugerida: `es-CL-LorenzoNeural`.

Listar voces chilenas:

```powershell
python main.py voices --engine edge --locale es-CL
```

## Uso del CLI

### Convertir un archivo

```powershell
python main.py convert .\input\archivo.md --out .\output
```

Salida:

```text
output\archivo.mp3
```

### Convertir una carpeta dentro de input

```powershell
python main.py convert .\input\NombreCarpeta --out .\output
```

Salida esperada:

```text
input\NombreCarpeta\tema_1.md -> output\NombreCarpeta\tema_1.mp3
input\NombreCarpeta\tema_2.md -> output\NombreCarpeta\tema_2.mp3
```

### Convertir una carpeta con subcarpetas

```powershell
python main.py convert .\input\NombreCarpeta --out .\output --recursive
```

### Convertir todo input

```powershell
python main.py convert
```

### Forzar regeneracion

Usar cuando cambiaste voz, texto, velocidad, idioma o quieres rehacer todo:

```powershell
python main.py convert .\input\NombreCarpeta --out .\output --force
```

### Usar Edge online

```powershell
python main.py convert .\input\archivo.md --out .\output --engine edge --voice es-CL-LorenzoNeural
```

## Uso de la GUI QML

La interfaz grafica esta construida con PySide6 + QML/Qt Quick.

Ejecutar:

```powershell
python gui_main.py
```

La GUI permite:

- seleccionar archivo `.md`;
- seleccionar carpeta con varios `.md`;
- convertir con Kokoro offline;
- elegir voz Kokoro;
- ajustar velocidad;
- ajustar max chunk;
- administrar/descargar modelos Kokoro;
- ver progreso global;
- revisar logs;
- cancelar conversion;
- abrir output, MP3 y manifest.

## Calidad de codigo

El proyecto usa `pre-commit` con:

- `check-merge-conflict`;
- `end-of-file-fixer`;
- `trailing-whitespace`;
- `ruff check --fix`;
- `ruff format`;
- `mypy --config-file mypy.ini .`.

La configuracion vive en:

```text
.pre-commit-config.yaml
pyproject.toml
mypy.ini
```

Los hooks locales usan las herramientas instaladas en el entorno Conda `tts-pyside`.

## Valores por defecto del proyecto

```text
engine: kokoro
voice: em_santa
language: es
speed: 1.0
kokoro max chars: 900
edge max chars: 1800
```

## Funcionamiento interno

Pipeline:

```text
Markdown
-> limpieza de Markdown
-> normalizacion para lectura
-> chunking
-> motor TTS
-> chunks MP3 temporales
-> union final MP3
-> manifest JSON
```

Archivos temporales y manifest:

```text
output/.chunks/<archivo>/0001.mp3
output/.chunks/<archivo>/manifest.json
```

El manifest guarda:

- motor usado;
- voz;
- idioma;
- velocidad;
- hashes de chunks;
- tiempos por chunk;
- tiempo total;
- metodo de union de audio.

Si el texto y parametros no cambian, el CLI reutiliza chunks existentes.

## Replicar en otro dispositivo

1. Copiar la carpeta `md2audio/` al nuevo equipo.
2. Crear el entorno Conda desde `environment.yml`.
3. Activar el entorno `tts-pyside`.
4. Copiar o descargar los modelos Kokoro en `models/kokoro/`.
5. Verificar `ffmpeg`.
6. Ejecutar una prueba.

Comandos:

```powershell
cd C:\ruta\a\md2audio
conda env create -f environment.yml
conda activate tts-pyside
python main.py voices --engine kokoro --locale es
python main.py convert .\input\ejemplo.md --out .\output
```

## Prueba minima

Crear `input\ejemplo.md`:

```markdown
# Prueba

Este es un texto breve para probar la conversion local con Kokoro.
```

Ejecutar:

```powershell
python main.py convert .\input\ejemplo.md --out .\output --force
```

Resultado esperado:

```text
output\ejemplo.mp3
```

## Problemas comunes

### Falta edge-tts

```text
Falta edge-tts. Activa el entorno Conda e instala dependencias con: python -m pip install -r requirements.txt
```

Solucion:

```powershell
python -m pip install -r requirements.txt
```

### Faltan modelos Kokoro

```text
Faltan modelos Kokoro en models/kokoro.
```

Solucion: descargar o copiar:

```text
kokoro-v1.0.onnx
voices-v1.0.bin
```

### ffmpeg no detectado

Verificar:

```powershell
where.exe ffmpeg
```

O usar ruta manual:

```powershell
python main.py convert .\input --ffmpeg "C:\Program Files\Krita (x64)\bin\ffmpeg.exe"
```

### Kokoro tarda mucho

Es normal en CPU. En este proyecto Kokoro prioriza calidad offline sobre velocidad. Para generar rapido con internet, usar Edge:

```powershell
python main.py convert .\input --engine edge --voice es-CL-LorenzoNeural
```

## Archivos que conviene respaldar

Para replicar el proyecto completo:

```text
main.py
environment.yml
requirements.txt
README.md
CONSTRUCTION.md
pyproject.toml
mypy.ini
.pre-commit-config.yaml
src/
models/kokoro/
input/   opcional, si quieres llevar textos
output/  opcional, si quieres llevar audios generados
```

No hace falta respaldar:

```text
entornos Conda locales
__pycache__/
```
