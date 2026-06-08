# md2audio

CLI simple para convertir apuntes Markdown en pistas MP3 de estudio.

## Instalacion

```powershell
conda env create -f environment.yml
conda activate tts-pyside
```

## Uso rapido

Coloca tus archivos `.md` en `input/` y ejecuta. El motor por defecto es Kokoro local:

```powershell
python main.py convert
```

## GUI QML

Para abrir la interfaz grafica con PySide6 + QML:

```powershell
python gui_main.py
```

## Calidad de codigo

El proyecto usa `pre-commit` con Ruff y mypy. Instala el hook una vez dentro del entorno Conda:

```powershell
conda activate tts-pyside
pre-commit install
```

Para ejecutar todas las validaciones manualmente:

```powershell
pre-commit run --all-files
```

Tambien puedes pasar un archivo o carpeta especifica:

```powershell
python main.py convert .\input\clase1.md --out .\output
python main.py convert .\input --recursive --speed 0.95
```

Si pasas una carpeta dentro de `input/`, el CLI crea la misma carpeta dentro de `output/` y genera un MP3 por cada Markdown:

```powershell
python main.py convert .\input\Unidad_2 --out .\output
```

Resultado esperado:

```text
input\Unidad_2\tema_1.md -> output\Unidad_2\tema_1.mp3
input\Unidad_2\tema_2.md -> output\Unidad_2\tema_2.mp3
```

Para incluir subcarpetas:

```powershell
python main.py convert .\input\Unidad_2 --out .\output --recursive
```

Para listar voces Kokoro en espanol:

```powershell
python main.py voices --engine kokoro --locale es
```

Para usar Edge online:

```powershell
python main.py convert .\input --engine edge --voice es-CL-LorenzoNeural
python main.py voices --engine edge --locale es-CL
```

## Notas

- Motor principal: `kokoro`, local/offline despues de descargar modelos.
- Motor alternativo: `edge`, online.
- Voz Kokoro por defecto: `em_santa`.
- Voz Edge sugerida: `es-CL-LorenzoNeural`.
- Modelos Kokoro locales esperados en `models/kokoro/`:
  - `kokoro-v1.0.onnx`
  - `voices-v1.0.bin`
- El CLI guarda chunks temporales en `output/.chunks/` para poder reusar trabajo ya generado.
- Si `ffmpeg` esta instalado, lo usa para unir MP3. Si no, usa una union binaria basica como fallback.
- Al terminar muestra tiempo por chunk, tiempo total por archivo y tiempo total del lote.
