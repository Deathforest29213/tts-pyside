# md2audio

CLI simple para convertir apuntes Markdown en pistas MP3 de estudio.

## Instalacion

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Uso rapido

Coloca tus archivos `.md` en `input/` y ejecuta. El motor por defecto es Kokoro local:

```powershell
.\.venv\Scripts\python main.py convert
```

## GUI QML

Para abrir la interfaz grafica con PySide6 + QML:

```powershell
.\.venv\Scripts\python gui_main.py
```

Tambien puedes pasar un archivo o carpeta especifica:

```powershell
.\.venv\Scripts\python main.py convert .\input\clase1.md --out .\output
.\.venv\Scripts\python main.py convert .\input --recursive --speed 0.95
```

Si pasas una carpeta dentro de `input/`, el CLI crea la misma carpeta dentro de `output/` y genera un MP3 por cada Markdown:

```powershell
.\.venv\Scripts\python main.py convert .\input\Unidad_2 --out .\output
```

Resultado esperado:

```text
input\Unidad_2\tema_1.md -> output\Unidad_2\tema_1.mp3
input\Unidad_2\tema_2.md -> output\Unidad_2\tema_2.mp3
```

Para incluir subcarpetas:

```powershell
.\.venv\Scripts\python main.py convert .\input\Unidad_2 --out .\output --recursive
```

Para listar voces Kokoro en espanol:

```powershell
.\.venv\Scripts\python main.py voices --engine kokoro --locale es
```

Para usar Edge online:

```powershell
.\.venv\Scripts\python main.py convert .\input --engine edge --voice es-CL-LorenzoNeural
.\.venv\Scripts\python main.py voices --engine edge --locale es-CL
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
