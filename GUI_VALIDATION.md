# Validacion GUI PySide6 + QML

Fecha de validacion: 2026-06-08

## Resumen

Se implemento una GUI en PySide6 + QML/Qt Quick para `md2audio`, manteniendo la CLI existente.

Archivos principales:

```text
gui_main.py
src/gui/app.py
src/gui/bridge.py
src/gui/workers.py
src/gui/model_manager.py
src/gui/settings.py
src/gui/file_scanner.py
src/qml/Main.qml
src/qml/components/
src/qml/md2audio/style/
```

## Evidencia tecnica ejecutada

### Compilacion Python

Comando:

```powershell
.\.venv\Scripts\python -m compileall gui_main.py src
```

Resultado:

```text
OK
```

### Smoke test del bridge

Comando:

```powershell
.\.venv\Scripts\python -c "from src.gui.bridge import AppBridge; b=AppBridge(); print(b.modelsReady, b.selectedVoice, b.fileCount, b.ffmpegStatus)"
```

Resultado observado:

```text
True em_santa 7 C:\Program Files\Krita (x64)\bin\ffmpeg.exe
```

### Carga QML offscreen

Comando:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python <script de carga QQmlApplicationEngine>
```

Resultado observado:

```text
roots= 1
```

### Worker de conversion Kokoro

Prueba:

```text
input/ejemplo.md -> output/gui_worker_smoke/ejemplo.mp3
```

Resultado observado:

```text
LOG Motor: kokoro | Voz: em_santa | Speed: 1.0
LOG Generando archivo 1/1: ejemplo.md
LOG Chunk 1/1: generando...
LOG Chunk 1/1: ok (23.7s)
PROGRESS 100
FINISHED 0 ejemplo.mp3 23.7s
exists= True
```

La carpeta temporal `output/gui_worker_smoke` fue eliminada despues de la prueba.

### Cancelacion

Prueba:

```text
ConversionWorker.cancel() antes de run()
```

Resultado observado:

```text
cancelled= [(0, 'Cancelado')]
```

### Persistencia

Prueba:

```text
GuiSettings.set('speed', 1.0) y recarga de GuiSettings
```

Resultado observado:

```text
persisted_speed= 1.0
```

Archivo de settings:

```text
config/gui_settings.json
```

El archivo esta ignorado por Git:

```text
.gitignore: config/gui_settings.json
```

## Matriz contra la especificacion

| Requisito | Estado | Evidencia |
|---|---:|---|
| GUI con PySide6 + QML/Qt Quick | Cumplido | `gui_main.py`, `src/gui/app.py`, `src/qml/Main.qml` |
| CLI existente sigue funcionando | Cumplido | No se removio `main.py` ni `src/cli.py`; compilacion completa OK |
| Selector de archivo `.md` | Cumplido | `bridge.selectFile()`, boton en `PathPicker.qml` |
| Selector de carpeta | Cumplido | `bridge.selectFolder()`, boton en `PathPicker.qml` |
| Salida fija en `output/` | Cumplido | `GuiSettings` default `output_path`, `bridge.outputPath` |
| Crear carpeta espejo en output | Cumplido | `file_scanner.py` usa `output_root_for_input()` / `output_dir_for_markdown()` |
| Usar solo Kokoro en GUI | Cumplido | `ConversionWorker` usa `KokoroTTSEngine`; no hay selector Edge en QML |
| Voz por defecto `em_santa` | Cumplido | `GuiSettings` default y bridge smoke test |
| Lista desplegable de voces | Cumplido | `ComboBox` en `Main.qml`, `bridge.voices` |
| Control de velocidad | Cumplido | `Slider`, rango 0.75 a 1.25 |
| Control max chunk | Cumplido | `SpinBox`, default 900 |
| Tabla/lista de archivos | Cumplido | `FileTable.qml` con estado, archivo, tiempo y mensaje |
| Barra de progreso global | Cumplido | `ProgressBar` en `Main.qml`, `bridge.progress` |
| Log interno | Cumplido | `LogPanel.qml`, `bridge.logText` |
| Boton Convertir | Cumplido | `Main.qml`, `bridge.startConversion()` |
| Boton Cancelar | Cumplido | `Main.qml`, `bridge.cancelConversion()` |
| Cancelacion marca archivos como cancelados | Cumplido | Smoke test `cancelled= [(0, 'Cancelado')]` |
| Abrir input | Cumplido | `bridge.openInput()` |
| Abrir output | Cumplido | `bridge.openOutput()` |
| Abrir MP3 generado | Cumplido | `bridge.openSelectedMp3()` |
| Abrir manifest/log | Cumplido | `bridge.openSelectedManifest()` |
| Persistencia de configuracion | Cumplido | `src/gui/settings.py`, prueba `persisted_speed= 1.0` |
| Boton administrar modelos | Cumplido | `ModelManagerDialog.qml`, boton en `Main.qml` |
| Modal lista modelos instalados/faltantes | Cumplido | `bridge.models`, `model_manager.model_status()` |
| Descargar modelos faltantes | Cumplido | `ModelDownloadWorker`, `bridge.downloadMissingModels()` |
| Mostrar progreso de descarga | Cumplido | `bridge.downloadProgress`, `ProgressBar` del modal |
| Deshabilitar conversion si faltan modelos | Cumplido | boton Convertir requiere `bridge.modelsReady` |
| Deshabilitar conversion si falta ffmpeg | Cumplido | boton Convertir requiere `bridge.ffmpegReady` |
| Validar input inexistente / sin `.md` | Cumplido | `bridge.scanInput()` y `_validation_error()` |
| Evitar congelar UI | Cumplido | conversion y descarga usan `QThread` |
| Estilo moderno oscuro | Cumplido | `Theme.qml`, QML con paneles oscuros y estados por color |
| Uso con Python antes de build exe | Cumplido | `.\.venv\Scripts\python gui_main.py` |

## Pendientes o decisiones para iteraciones futuras

- El empaquetado `.exe` queda fuera del MVP por decision de especificacion.
- No se implemento motor Edge en GUI, tambien fuera del MVP.
- No hay reproductor integrado de audio; se abre el MP3 con la aplicacion del sistema.
- La cancelacion durante una inferencia Kokoro se aplica de forma segura al terminar el chunk actual, como se definio en la especificacion.
