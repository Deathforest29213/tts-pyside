# md2audio

Aplicacion Python para convertir textos Markdown (`.md`) en audios MP3 de estudio.

El motor principal es Kokoro local/offline. La GUI esta construida con PySide6 + QML y el CLI queda disponible para automatizar conversiones por archivo o carpeta.

## Requisitos

- Windows 10/11.
- Miniconda o Anaconda instalado.
- Git instalado.
- `ffmpeg` instalado y disponible en `PATH`.
- Internet solo para clonar, instalar dependencias y descargar modelos.

## 1. Clonar el repositorio

```powershell
git clone https://github.com/Deathforest29213/tts-pyside.git
cd tts-pyside
```

Si ya tienes el proyecto:

```powershell
cd C:\ruta\a\md2audio
git pull
```

## 2. Crear el entorno Conda

```powershell
conda env create -f environment.yml
conda activate tts-pyside
```

Si el entorno ya existe y solo quieres actualizar dependencias:

```powershell
conda activate tts-pyside
python -m pip install -r requirements.txt
```

## 3. Instalar ffmpeg

Verifica si ya esta disponible:

```powershell
where.exe ffmpeg
```

Si no aparece una ruta, instala ffmpeg. Opciones comunes:

```powershell
winget install Gyan.FFmpeg
```

o con Chocolatey:

```powershell
choco install ffmpeg
```

Cierra y abre de nuevo la terminal despues de instalarlo, y vuelve a probar:

```powershell
where.exe ffmpeg
```

## 4. Descargar modelos Kokoro

Kokoro necesita estos archivos:

```text
models/kokoro/kokoro-v1.0.onnx
models/kokoro/voices-v1.0.bin
```

Puedes descargarlos desde la GUI con el boton `Administrar modelos`.

Tambien puedes descargarlos manualmente:

```powershell
New-Item -ItemType Directory -Force .\models\kokoro

Invoke-WebRequest `
  -Uri "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx" `
  -OutFile ".\models\kokoro\kokoro-v1.0.onnx"

Invoke-WebRequest `
  -Uri "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" `
  -OutFile ".\models\kokoro\voices-v1.0.bin"
```

Los modelos no se suben a GitHub porque son archivos grandes.

## 5. Agregar textos de entrada

Coloca tus archivos Markdown dentro de `input/`.

Ejemplos:

```text
input/clase1.md
input/Hidrosalino/Unidad_1.md
input/Hidrosalino/Unidad_2.md
```

Los archivos dentro de `input/` no se suben al repo. Cada usuario debe poner sus propios textos.

## 6. Iniciar la app GUI

Con el entorno activo:

```powershell
conda activate tts-pyside
python gui_main.py
```

Desde la GUI puedes:

- seleccionar archivo o carpeta;
- elegir voz Kokoro;
- ajustar velocidad;
- ajustar max chunk;
- seleccionar que archivos convertir;
- convertir a MP3;
- abrir MP3, manifest u output;
- descargar modelos Kokoro.

## 7. Usar por terminal

Convertir todo `input/`:

```powershell
python main.py convert
```

Convertir un archivo:

```powershell
python main.py convert .\input\clase1.md --out .\output
```

Convertir una carpeta:

```powershell
python main.py convert .\input\Hidrosalino --out .\output
```

Convertir una carpeta con subcarpetas:

```powershell
python main.py convert .\input\Hidrosalino --out .\output --recursive
```

Forzar regeneracion:

```powershell
python main.py convert .\input\Hidrosalino --out .\output --force
```

Listar voces Kokoro en espanol:

```powershell
python main.py voices --engine kokoro --locale es
```

## 8. Calidad de codigo

El proyecto usa `pre-commit` con Ruff y mypy.

Instalar el hook una vez:

```powershell
conda activate tts-pyside
pre-commit install
```

Ejecutar validaciones manualmente:

```powershell
pre-commit run --all-files
```

## Archivos que no viajan en GitHub

Estos archivos/carpetas estan ignorados:

```text
.venv/
.mypy_cache/
.ruff_cache/
models/kokoro/*.onnx
models/kokoro/*.bin
input/*
output/*
config/gui_settings.json
```

Despues de clonar en otro computador, debes crear el entorno, instalar ffmpeg, descargar/copiar modelos Kokoro y agregar tus propios `.md` en `input/`.

## Comando minimo para empezar

```powershell
git clone https://github.com/Deathforest29213/tts-pyside.git
cd tts-pyside
conda env create -f environment.yml
conda activate tts-pyside
python gui_main.py
```

Si la GUI indica que faltan modelos, usa `Administrar modelos` para descargarlos.
