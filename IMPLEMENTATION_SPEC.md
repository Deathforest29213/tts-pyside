# Especificacion de mejoras md2audio

Este documento define las mejoras pendientes para robustecer md2audio como aplicacion TTS local con GUI QML y CLI.

## Objetivo

Mejorar confiabilidad, calidad de salida, mantenibilidad y experiencia de uso sin romper el flujo actual:

```powershell
python gui_main.py
python main.py convert .\input --out .\output
```

El motor principal sigue siendo Kokoro local/offline.

## Alcance funcional

### Prioridad alta

#### 1. Validar modelos por tamano y hash

Problema:

- Actualmente un modelo se considera instalado si el archivo existe.
- Un archivo incompleto o corrupto puede marcarse como valido y fallar despues al cargar Kokoro.

Requisitos:

- Cada modelo debe tener:
  - nombre;
  - URL;
  - tamano esperado;
  - hash esperado, preferentemente SHA256.
- La GUI debe mostrar estados diferenciados:
  - `Instalado`;
  - `Falta`;
  - `Incompleto`;
  - `Corrupto`;
  - `Verificando`.
- `modelsReady` solo debe ser verdadero si todos los modelos existen y pasan validacion.
- La descarga debe escribir a `.part`, validar tamano/hash y solo despues renombrar al archivo final.
- Si la validacion falla, debe eliminarse el `.part` o dejarse claramente marcado como invalido.

Criterios de aceptacion:

- Si falta un modelo, la GUI muestra `Falta`.
- Si el archivo existe pero pesa distinto, la GUI muestra `Incompleto`.
- Si el tamano coincide pero el hash no coincide, la GUI muestra `Corrupto`.
- Kokoro no intenta cargar modelos invalidos.

Archivos probables:

- `src/gui/model_manager.py`
- `src/gui/bridge.py`
- `src/qml/components/ModelManagerDialog.qml`
- `README.md`

#### 2. Cerrar correctamente el hilo de descarga en errores

Problema:

- Si falla una descarga, el worker emite `error`, pero el hilo puede quedar activo si no se emite `finished`.
- Esto bloquea nuevas descargas durante la sesion.

Requisitos:

- `ModelDownloadWorker` debe emitir `finished` siempre, incluso en error.
- El error debe quedar en el log.
- La GUI debe permitir reintentar descarga despues de un error.
- Si existe un archivo `.part`, debe eliminarse o reanudarse de forma explicita.

Criterios de aceptacion:

- Simular error de red no deja `_download_thread` bloqueado.
- Despues del error, el boton de descarga vuelve a funcionar.
- El log muestra causa del error.

Archivos probables:

- `src/gui/model_manager.py`
- `src/gui/bridge.py`

#### 3. Agregar estado `Omitido` para Markdown sin texto util

Problema:

- Si un `.md` queda sin contenido tras limpiar Markdown, la conversion puede fallar al intentar unir cero chunks.

Requisitos:

- Si `parse_markdown_file()` no devuelve parrafos, marcar archivo como `Omitido`.
- Si `chunk_paragraphs()` devuelve lista vacia, marcar archivo como `Omitido`.
- No debe generarse MP3 vacio.
- El progreso debe avanzar correctamente.
- El log debe explicar el motivo.

Criterios de aceptacion:

- Un `.md` con solo codigo o imagenes no rompe la conversion.
- La tarjeta del archivo muestra `Omitido`.
- El lote termina normalmente.

Archivos probables:

- `src/gui/workers.py`
- `src/cli.py`
- `src/gui/file_scanner.py`
- `src/qml/components/FileTable.qml`

#### 4. Unificar logica CLI/GUI en un servicio compartido

Problema:

- La GUI y el CLI duplican partes de la conversion.
- Esto aumenta riesgo de divergencias en manifests, chunks, cache y errores.

Requisitos:

- Crear un modulo compartido, por ejemplo:

```text
src/conversion.py
```

- Este modulo debe contener:
  - preparacion de archivo;
  - parseo;
  - chunking;
  - reuse de chunks;
  - escritura de manifest;
  - union de audio;
  - manejo de archivos omitidos;
  - estructura de resultado por archivo.
- CLI y GUI deben consumir el mismo servicio.
- La GUI puede seguir usando `ConversionWorker`, pero el worker debe delegar la conversion real al servicio comun.

Criterios de aceptacion:

- CLI y GUI generan manifests con la misma estructura.
- Cambiar cache/chunking se hace en un solo lugar.
- Tests unitarios pueden validar el servicio sin abrir QML.

Archivos probables:

- `src/conversion.py`
- `src/cli.py`
- `src/gui/workers.py`
- `src/gui/bridge.py`

#### 5. Agregar tests unitarios

Requisitos:

- Agregar `pytest` al entorno de desarrollo.
- Crear carpeta:

```text
tests/
```

- Cubrir al menos:
  - parser Markdown;
  - chunker;
  - validacion de modelos;
  - seleccion de archivos en bridge;
  - conversion de archivo omitido;
  - resolucion de output para carpetas dentro de `input`.

Criterios de aceptacion:

- `pytest` corre en el entorno `tts-pyside`.
- `pre-commit run --all-files` sigue pasando.
- Los tests no requieren descargar modelos reales.

Archivos probables:

- `requirements.txt`
- `environment.yml`
- `tests/test_parser.py`
- `tests/test_chunker.py`
- `tests/test_model_manager.py`
- `tests/test_file_selection.py`

## Prioridad media

### 6. Boton `Probar voz`

Requisitos:

- En la tab `Configuracion`, agregar boton `Probar voz`.
- Debe generar un audio corto con texto fijo o editable.
- Duracion objetivo: 5 a 10 segundos.
- Debe guardar salida temporal en `output/.preview/`.
- Debe permitir abrir/reproducir el MP3 generado.

Criterios de aceptacion:

- El usuario puede escuchar una voz antes de convertir un lote.
- No modifica los manifests de conversion principal.

Archivos probables:

- `src/gui/bridge.py`
- `src/gui/workers.py` o nuevo `preview_worker.py`
- `src/qml/Main.qml`

### 7. Presets de configuracion

Presets iniciales:

```text
Apuntes tecnicos
Libro narrativo
Rapido
Calidad alta
```

Requisitos:

- Cada preset define:
  - voz;
  - velocidad;
  - max chunk;
  - recursive;
  - force opcional.
- Seleccionar preset actualiza controles de GUI.
- Los valores siguen siendo editables despues de aplicar preset.

Criterios de aceptacion:

- Cambiar preset actualiza UI y configuracion persistida.
- Se documenta que los presets son puntos de partida.

Archivos probables:

- `src/gui/settings.py`
- `src/gui/bridge.py`
- `src/qml/Main.qml`

### 8. Guardar perfiles de configuracion por proyecto

Requisitos:

- Permitir guardar configuraciones con nombre.
- Un perfil puede incluir:
  - input path;
  - output path;
  - voz;
  - velocidad;
  - max chunk;
  - recursive;
  - clean temp;
  - force.
- Guardar en:

```text
config/profiles.json
```

- `profiles.json` debe estar ignorado o documentado segun se decida si es personal o compartible.

Criterios de aceptacion:

- Crear, cargar y sobrescribir perfil desde GUI.
- Reiniciar app mantiene perfiles.

Archivos probables:

- `src/gui/settings.py`
- `src/gui/bridge.py`
- `src/qml/Main.qml`
- `.gitignore`

### 9. Reintentar descarga y mostrar velocidad/MB

Requisitos:

- Mostrar progreso como:

```text
123 MB / 325 MB - 4.2 MB/s
```

- Agregar reintentos automaticos configurables, por ejemplo 3 intentos.
- Registrar en log cada intento.
- Si falla, dejar estado claro para reintentar manualmente.

Criterios de aceptacion:

- Una descarga fallida no bloquea la app.
- El usuario ve avance real y velocidad aproximada.

Archivos probables:

- `src/gui/model_manager.py`
- `src/gui/bridge.py`
- `src/qml/components/ModelManagerDialog.qml`

### 10. Validacion antes de convertir

Requisitos:

- Antes de iniciar conversion validar:
  - modelos instalados y validos;
  - ffmpeg detectado;
  - archivos seleccionados;
  - input existe;
  - output escribible;
  - espacio en disco suficiente.
- Mostrar errores en log y bloquear conversion si falta algo critico.

Criterios de aceptacion:

- Si falta espacio, la conversion no empieza.
- Si output no es escribible, se muestra error claro.

Archivos probables:

- `src/gui/bridge.py`
- `src/gui/workers.py`
- `src/conversion.py`
- `src/cli.py`

## Prioridad futura

### 11. Normalizacion de volumen/loudness

Requisitos:

- Agregar opcion para normalizar volumen final.
- Usar `ffmpeg` con filtros como `loudnorm` o alternativa equivalente.
- Guardar en manifest si se aplico normalizacion.

Criterios de aceptacion:

- Audios largos mantienen volumen mas consistente.
- La opcion puede desactivarse.

Archivos probables:

- `src/audio.py`
- `src/conversion.py`
- `src/cli.py`
- `src/gui/bridge.py`
- `src/qml/Main.qml`

### 12. Metadatos ID3

Requisitos:

- Escribir metadatos en MP3:
  - titulo;
  - autor;
  - album/proyecto;
  - capitulo;
  - fecha;
  - motor;
  - voz.
- Extraer titulo desde nombre de archivo o primer heading Markdown.
- Usar herramienta/libreria compatible, por ejemplo `mutagen`.

Criterios de aceptacion:

- Los reproductores muestran titulo y album.
- El manifest indica metadatos escritos.

Archivos probables:

- `requirements.txt`
- `environment.yml`
- `src/audio.py`
- `src/parser.py`
- `src/conversion.py`

## Requisitos no funcionales

- Mantener Kokoro como motor principal.
- Mantener compatibilidad CLI.
- No subir modelos, inputs ni outputs al repo.
- Mantener `pre-commit` obligatorio.
- Evitar bloquear la UI durante conversion o descarga.
- Los tests deben poder correr sin internet y sin modelos reales.

## Orden recomendado de implementacion

1. Corregir descarga de modelos en errores.
2. Validar modelos por tamano/hash.
3. Manejar archivos omitidos.
4. Crear tests para parser/chunker/modelos/seleccion.
5. Extraer `src/conversion.py`.
6. Agregar validacion previa robusta.
7. Agregar `Probar voz`.
8. Agregar presets.
9. Agregar perfiles por proyecto.
10. Mejorar descarga con reintentos/velocidad.
11. Normalizar volumen.
12. Escribir metadatos ID3.

## Comandos de validacion

```powershell
conda activate tts-pyside
pre-commit run --all-files
python main.py voices --engine kokoro --locale es
python gui_main.py
```

Cuando existan tests:

```powershell
pytest
```
