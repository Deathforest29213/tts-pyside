# Especificacion GUI PySide para md2audio

## 1. Objetivo

Construir una interfaz grafica moderna y oscura con PySide6 + QML/Qt Quick para usar `md2audio` de forma comoda, sin depender de comandos en terminal para el flujo diario.

La GUI debe permitir:

- convertir archivos Markdown sueltos a MP3;
- convertir carpetas completas con varios `.md`;
- usar Kokoro como motor TTS principal;
- administrar y descargar modelos Kokoro;
- revisar archivos detectados, progreso, logs y resultados;
- abrir carpetas y archivos generados desde la interfaz.

La CLI existente debe seguir funcionando.

## 2. Alcance MVP

La primera version de la GUI debe incluir:

- selector de archivo `.md`;
- selector de carpeta;
- salida fija en la carpeta `output/` del proyecto;
- selector de voz Kokoro;
- controles de velocidad y max chunk;
- tabla de archivos detectados;
- barra de progreso global;
- log interno;
- boton convertir;
- boton cancelar;
- boton abrir input;
- boton abrir output;
- boton abrir MP3 generado;
- boton abrir manifest/log del archivo seleccionado;
- persistencia de configuracion;
- boton para descargar modelos Kokoro;
- modal de estado de modelos.

No se implementa todavia:

- motor Edge en GUI;
- selector de modelos externos avanzados;
- empaquetado a `.exe`;
- editor visual de Markdown;
- reproductor de audio integrado.

## 3. Motor TTS inicial

La GUI usara solo Kokoro en la primera version.

Valores por defecto:

```text
engine: kokoro
voice: em_santa
language: es
speed: 1.0
max_chars: 900
```

Voces espanolas Kokoro disponibles:

```text
ef_dora
em_alex
em_santa
```

La voz por defecto debe ser:

```text
em_santa
```

## 4. Flujo ideal de usuario

1. Abrir la app.
2. Seleccionar archivo o carpeta.
3. La app detecta los `.md` y los muestra en una tabla.
4. El usuario revisa voz, velocidad y max chunk.
5. El usuario presiona `Convertir`.
6. La app muestra progreso global y logs.
7. Al terminar, la tabla marca cada archivo como listo o error.
8. El usuario puede abrir el MP3, el manifest o la carpeta output.

## 5. Boceto ASCII

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ md2audio - Kokoro TTS                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ Entrada                                                                      │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ C:\...\md2audio\input\Hidrosalino                                       │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│ [Seleccionar archivo]  [Seleccionar carpeta]  [Abrir input]                 │
│                                                                              │
│ Salida                                                                       │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ C:\...\md2audio\output\Hidrosalino                                      │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│ [Abrir output]                                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ Configuracion Kokoro                                                         │
│ ┌────────────────────────┐ ┌──────────────────────┐ ┌─────────────────────┐ │
│ │ Voz                    │ │ Velocidad            │ │ Max chunk           │ │
│ │ [ em_santa        v ]  │ │ [ 1.00 ] ─────●────  │ │ [ 900          ]   │ │
│ └────────────────────────┘ └──────────────────────┘ └─────────────────────┘ │
│                                                                              │
│ Modelos                                                                      │
│ Kokoro: instalado                                                            │
│ [Administrar modelos]                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ Archivos detectados                                                          │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ Estado      Archivo                                      Salida          │ │
│ │ Pendiente   Unidad_1_Hidrosalino_I.md                   .mp3            │ │
│ │ Pendiente   Unidad_2_Hidrosalino_II.md                  .mp3            │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│ 2 archivos detectados                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ Progreso                                                                     │
│ ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 45%                       │
│ Archivo actual: Unidad_2_Hidrosalino_II.md                                   │
│ Tiempo: 2m 12s                                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ Log                                                                          │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ 12:30:11 Kokoro listo. Voz: em_santa                                    │ │
│ │ 12:30:12 Detectados 2 archivos Markdown                                 │ │
│ │ 12:30:20 Generando Unidad_1_Hidrosalino_I.md                            │ │
│ │ 12:36:44 MP3 generado correctamente                                     │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│ [Actualizar lista] [Convertir] [Cancelar] [Abrir MP3] [Abrir manifest]       │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 6. Modal de modelos

Boton:

```text
Administrar modelos
```

Al presionarlo se abre un modal:

```text
┌────────────────────────────────────────────────────────────┐
│ Modelos Kokoro                                             │
├────────────────────────────────────────────────────────────┤
│ Estado      Archivo              Tamano       Accion       │
│ Instalado   kokoro-v1.0.onnx     325 MB       [Revisar]    │
│ Instalado   voices-v1.0.bin       28 MB       [Revisar]    │
│                                                            │
│ Ruta: C:\...\md2audio\models\kokoro                       │
├────────────────────────────────────────────────────────────┤
│ [Descargar faltantes] [Abrir carpeta modelos] [Cerrar]     │
└────────────────────────────────────────────────────────────┘
```

Comportamiento:

- si ambos archivos existen, mostrar `Instalado`;
- si falta uno, mostrar `Falta`;
- `Descargar faltantes` descarga solo archivos ausentes;
- mostrar progreso de descarga;
- deshabilitar conversion si faltan modelos;
- por ahora solo se administra Kokoro.

Archivos requeridos:

```text
models/kokoro/kokoro-v1.0.onnx
models/kokoro/voices-v1.0.bin
```

URLs:

```text
https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

## 7. Controles visibles

### Voz

Lista desplegable con voces Kokoro disponibles.

Valor inicial:

```text
em_santa
```

### Velocidad

Control numerico o slider.

Rango recomendado:

```text
0.75 a 1.25
```

Valor inicial:

```text
1.0
```

Significado:

- menor que `1.0`: lectura mas lenta;
- `1.0`: velocidad normal;
- mayor que `1.0`: lectura mas rapida.

### Max chunk

Input numerico.

Valor inicial:

```text
900
```

Significado:

`Max chunk` controla cuantos caracteres como maximo se envian al motor TTS por bloque.

Impacto:

- chunks mas pequenos: menos riesgo de cortes raros y mejor estabilidad;
- chunks mas grandes: menos archivos temporales y menos uniones, pero mayor probabilidad de pausas o entonacion menos natural;
- para Kokoro se recomienda `900` como valor inicial.

## 8. Opciones no visibles en MVP y que significan

Estas opciones existen en la CLI. En la GUI inicial no se muestran como controles principales, salvo que se decida exponerlas luego en una seccion avanzada.

### Recursive

CLI:

```powershell
--recursive
```

Convierte tambien archivos `.md` dentro de subcarpetas.

Ejemplo:

```text
input\Libro\Capitulo_1\parte_1.md
input\Libro\Capitulo_2\parte_1.md
```

Sin `recursive`, solo toma `.md` directamente dentro de la carpeta seleccionada.

En GUI:

- puede implementarse como checkbox `Incluir subcarpetas`;
- no es obligatorio en el primer flujo si se quiere mantener la UI limpia;
- recomendado agregarlo en una seccion de opciones.

### Force

CLI:

```powershell
--force
```

Regenera audio aunque ya existan chunks temporales reutilizables.

Uso:

- cuando cambiaste texto;
- cuando cambiaste voz;
- cuando cambiaste velocidad;
- cuando quieres limpiar resultados anteriores.

En GUI:

- se puede representar como `Forzar regeneracion`;
- usar con cuidado porque Kokoro tarda mas.

### Clean temp

CLI:

```powershell
--clean-temp
```

Elimina chunks temporales despues de generar el MP3 final.

Ventaja:

- ahorra espacio.

Desventaja:

- no permite reusar chunks;
- si vuelves a convertir, genera todo desde cero.

En GUI:

- puede quedar como opcion avanzada.

### FFmpeg path

CLI:

```powershell
--ffmpeg "C:\ruta\a\ffmpeg.exe"
```

Permite indicar manualmente la ruta de `ffmpeg.exe`.

Uso:

- si la app no detecta `ffmpeg`;
- si el usuario tiene varias instalaciones.

En GUI:

- en MVP solo mostrar estado detectado;
- en version posterior, agregar selector manual en ajustes avanzados.

## 9. Tabla de archivos

Columnas requeridas:

```text
Estado
Archivo
Salida
Tiempo
Mensaje
```

Estados:

```text
Pendiente
Generando
Listo
Cancelado
Error
```

Comportamiento:

- al seleccionar archivo o carpeta, la tabla se actualiza;
- si se selecciona archivo, muestra una fila;
- si se selecciona carpeta, muestra un archivo por fila;
- si no hay `.md`, mostrar aviso claro;
- al terminar conversion, permitir abrir MP3 de la fila seleccionada.

## 10. Progreso

Primera version:

- una barra global;
- texto de archivo actual;
- tiempo transcurrido.

No se requiere progreso exacto por chunk en la UI inicial, pero el log debe mostrar mensajes por archivo/chunk si estan disponibles.

## 11. Log interno

Debe mostrar mensajes similares al CLI:

```text
Motor: kokoro
Voz: em_santa
Idioma: es
FFmpeg detectado
Detectados 2 archivos Markdown
Generando archivo 1/2
MP3 generado correctamente
Tiempo total del lote
```

El log debe ser de solo lectura.

Componente QML sugerido:

```text
ScrollView + TextArea
```

## 12. Cancelacion

Debe existir boton:

```text
Cancelar
```

Comportamiento esperado:

- detener la conversion en curso;
- marcar archivos restantes como `Cancelado`;
- eliminar progreso parcial de la conversion cancelada;
- dejar logs explicando que se cancelo;
- desbloquear botones de seleccion y conversion.

Nota tecnica:

Kokoro corre en CPU y puede no detenerse instantaneamente en medio de una inferencia. La cancelacion debe aplicarse de forma segura entre chunks o entre archivos.

## 13. Persistencia de configuracion

La GUI debe recordar:

- ultima ruta de entrada;
- ultima ruta de salida;
- voz seleccionada;
- velocidad;
- max chunk;
- tamano/posicion de ventana;
- opcion de incluir subcarpetas si se implementa.

Archivo sugerido:

```text
config/gui_settings.json
```

Este archivo no debe contener informacion sensible.

## 14. Arquitectura sugerida

```text
src/
├── cli.py
├── gui/
│   ├── __init__.py
│   ├── app.py
│   ├── bridge.py
│   ├── workers.py
│   ├── model_manager.py
│   ├── settings.py
│   └── file_scanner.py
├── qml/
│   ├── Main.qml
│   ├── components/
│   │   ├── PathPicker.qml
│   │   ├── FileTable.qml
│   │   ├── ModelManagerDialog.qml
│   │   ├── LogPanel.qml
│   │   └── PrimaryButton.qml
│   └── style/
│       ├── Theme.qml
│       └── qmldir
└── engines/
    ├── base.py
    ├── edge.py
    └── kokoro.py
```

Punto de entrada sugerido:

```text
gui_main.py
```

O comando:

```powershell
.\.venv\Scripts\python gui_main.py
```

## 15. Stack GUI requerido

```text
PySide6
Qt Quick
QML
QQmlApplicationEngine
QObject bridge
Property
Signal / Slot
QThread
JSON propio para settings
```

La UI debe estar definida principalmente en archivos `.qml`.

Python debe encargarse de:

- escanear archivos `.md`;
- exponer datos a QML;
- lanzar conversiones;
- descargar modelos;
- emitir progreso/logs;
- persistir configuracion.

QML debe encargarse de:

- layout visual;
- controles;
- tabla/lista de archivos;
- dialogos;
- tema oscuro;
- interaccion del usuario.

## 15.1 Componentes QML sugeridos

```text
ApplicationWindow
Rectangle
ColumnLayout
RowLayout
GridLayout
Text
TextField
Button
ComboBox
SpinBox
Slider
CheckBox
ProgressBar
ListView
TableView
Dialog
ScrollView
TextArea
FileDialog
FolderDialog
```

Si `TableView` complica demasiado el MVP, se puede usar `ListView` con filas custom para representar la tabla de archivos.

## 15.2 Bridge Python-QML

Clase sugerida:

```text
AppBridge(QObject)
```

Responsabilidades:

- exponer rutas actuales;
- exponer lista de voces;
- exponer lista de archivos detectados;
- recibir acciones desde QML;
- iniciar/cancelar conversion;
- abrir carpetas/archivos;
- gestionar descarga de modelos;
- emitir senales de progreso y log.

Senales sugeridas:

```text
logAdded(str message)
progressChanged(int percent)
filesChanged()
modelsChanged()
conversionStarted()
conversionFinished()
conversionCancelled()
conversionError(str message)
settingsChanged()
```

Slots sugeridos:

```text
selectFile()
selectFolder()
openInput()
openOutput()
openSelectedMp3()
openSelectedManifest()
scanInput()
startConversion()
cancelConversion()
downloadMissingModels()
setVoice(str voice)
setSpeed(float speed)
setMaxChars(int maxChars)
```

## 16. Hilos y no congelar UI

La conversion TTS no debe ejecutarse en el hilo principal.

Debe usarse:

```text
QThread
```

o:

```text
QRunnable + QThreadPool
```

Recomendacion MVP:

```text
QThread + Worker QObject
```

El worker debe emitir senales conectadas al bridge Python-QML:

```text
log(message)
progress(percent)
file_started(path)
file_finished(path, output)
file_error(path, error)
finished()
cancelled()
```

## 17. Validaciones antes de convertir

La GUI debe bloquear conversion si:

- no existe la ruta de entrada;
- no hay archivos `.md`;
- faltan modelos Kokoro;
- no se detecta `ffmpeg`;
- no existe carpeta `output/` y no puede crearse;
- ya hay una conversion en curso.

Si ya existen audios, la GUI puede permitir sobrescribir solo si se activa `Forzar regeneracion` en opciones avanzadas.

## 18. Estilo visual

Preferencia:

```text
moderna y oscura
```

Guia:

- fondo oscuro sobrio;
- alto contraste;
- botones claros;
- tabla legible;
- componentes QML propios y consistentes;
- estados con color:
  - pendiente: gris;
  - generando: azul;
  - listo: verde;
  - error: rojo;
  - cancelado: amarillo/naranja;
- evitar decoracion excesiva;
- priorizar claridad de herramienta tecnica.

## 19. Build futuro

Por ahora se usara con Python:

```powershell
.\.venv\Scripts\python gui_main.py
```

Mas adelante se puede estudiar empaquetado con:

```text
PyInstaller
```

Consideraciones futuras:

- incluir binarios necesarios;
- incluir archivos QML;
- decidir si se empaquetan modelos Kokoro o se descargan desde la app;
- manejar rutas relativas en modo `.exe`;
- mantener `models/kokoro` externo para no crear instaladores enormes.

## 20. Criterios de aceptacion MVP

La GUI se considera lista cuando:

- abre sin errores;
- detecta modelos Kokoro instalados;
- permite descargar modelos faltantes;
- permite seleccionar archivo `.md`;
- permite seleccionar carpeta;
- lista archivos detectados en tabla;
- convierte al menos un archivo con Kokoro;
- convierte varios archivos de una carpeta;
- crea carpeta espejo en `output/`;
- muestra progreso global;
- muestra logs;
- permite cancelar;
- permite abrir output;
- permite abrir MP3 generado;
- recuerda configuracion basica al reiniciar.

## 21. Comandos CLI equivalentes

Archivo:

```powershell
.\.venv\Scripts\python main.py convert .\input\archivo.md --out .\output
```

Carpeta:

```powershell
.\.venv\Scripts\python main.py convert .\input\Carpeta --out .\output
```

Carpeta con subcarpetas:

```powershell
.\.venv\Scripts\python main.py convert .\input\Carpeta --out .\output --recursive
```

Kokoro explicito:

```powershell
.\.venv\Scripts\python main.py convert .\input\archivo.md --out .\output --engine kokoro --voice em_santa --lang es --speed 1.0
```
