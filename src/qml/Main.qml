import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Window
import md2audio.style
import "components" as Components

ApplicationWindow {
    id: window
    visible: true
    width: bridge.windowWidth
    y: Screen.desktopAvailableY
    height: Math.max(minimumHeight, Screen.desktopAvailableHeight)
    minimumWidth: 1040
    minimumHeight: 760
    title: "md2audio - Kokoro TTS"
    color: Theme.bg

    property int currentSection: 0

    Material.theme: Material.Dark
    Material.accent: Theme.accent

    onClosing: bridge.saveWindowSize(width, height)

    Components.ModelManagerDialog {
        id: modelDialog
        anchors.centerIn: Overlay.overlay
    }

    ListModel {
        id: navModel
        ListElement { title: "Preparar"; detail: "Entrada, salida y archivos" }
        ListElement { title: "Configuracion"; detail: "Voz, lectura y modelos" }
        ListElement { title: "Seguimiento"; detail: "Progreso y registro" }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 184
            color: "#141821"
            border.color: Theme.border
            radius: 8

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    Text {
                        text: "md2audio"
                        color: Theme.text
                        font.pixelSize: 24
                        font.weight: Font.Bold
                    }

                    Text {
                        text: "Kokoro TTS"
                        color: Theme.muted
                        font.pixelSize: 12
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 30
                    radius: 15
                    color: bridge.modelsReady ? "#173324" : "#3b2d16"
                    border.color: bridge.modelsReady ? Theme.success : Theme.warning

                    Text {
                        anchors.centerIn: parent
                        color: bridge.modelsReady ? Theme.success : Theme.warning
                        text: "Kokoro: " + bridge.modelStatusText
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.border
                }

                Repeater {
                    model: navModel

                    delegate: Rectangle {
                        required property int index
                        required property string title
                        required property string detail

                        Layout.fillWidth: true
                        height: 64
                        radius: 7
                        color: window.currentSection === index ? "#253246" : "transparent"
                        border.color: window.currentSection === index ? Theme.accent : "transparent"
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 2

                            Item { Layout.fillHeight: true }

                            Text {
                                text: title
                                color: window.currentSection === index ? Theme.text : Theme.muted
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Text {
                                text: detail
                                color: Theme.muted
                                font.pixelSize: 10
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Item { Layout.fillHeight: true }
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: window.currentSection = index
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: bridge.selectedFileCount + " de " + bridge.fileCount + " archivos"
                        color: Theme.text
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    Text {
                        text: bridge.ffmpegReady ? "FFmpeg detectado" : "FFmpeg no detectado"
                        color: bridge.ffmpegReady ? Theme.success : Theme.warning
                        font.pixelSize: 11
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: navModel.get(window.currentSection).title
                        color: Theme.text
                        font.pixelSize: 22
                        font.weight: Font.Bold
                    }

                    Text {
                        text: sectionSubtitle()
                        color: Theme.muted
                        font.pixelSize: 12
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }

                Rectangle {
                    height: 30
                    width: 170
                    radius: 15
                    color: "#151821"
                    border.color: Theme.border

                    Text {
                        anchors.centerIn: parent
                        text: "Voz: " + bridge.selectedVoice
                        color: Theme.text
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }
                }
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: window.currentSection

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Components.PathPicker {
                                title: "Entrada"
                                path: bridge.inputPath
                                Layout.fillWidth: true
                                onFileRequested: bridge.selectFile()
                                onFolderRequested: bridge.selectFolder()
                                onOpenRequested: bridge.openInput()
                            }

                            Components.PathPicker {
                                title: "Salida"
                                path: bridge.outputPath
                                Layout.fillWidth: true
                                onOpenRequested: bridge.openOutput()
                            }
                        }

                        Components.FileTable {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            files: bridge.files
                            selectedIndex: bridge.selectedIndex
                            onRowSelected: bridge.selectFileRow(index)
                            onToggleFileRequested: bridge.toggleFileForConversion(index)
                            onToggleAllRequested: bridge.toggleAllFiles()
                            onOpenMp3Requested: bridge.openSelectedMp3()
                            onOpenManifestRequested: bridge.openSelectedManifest()
                            onOpenOutputRequested: bridge.openOutput()
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 342
                            color: Theme.panel
                            border.color: Theme.border
                            radius: 8

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 16

                                Text {
                                    text: "Configuracion Kokoro"
                                    color: Theme.text
                                    font.pixelSize: 16
                                    font.weight: Font.DemiBold
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 18

                                    ColumnLayout {
                                        Layout.preferredWidth: 280
                                        spacing: 8

                                        Text { text: "Preset"; color: Theme.muted; font.pixelSize: 12 }

                                        ComboBox {
                                            Layout.fillWidth: true
                                            model: bridge.presets
                                            currentIndex: Math.max(0, bridge.presets.indexOf(bridge.selectedPreset))
                                            onActivated: bridge.applyPreset(currentText)
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.preferredWidth: 180
                                        spacing: 8

                                        Text { text: "Max chunk"; color: Theme.muted; font.pixelSize: 12 }

                                        SpinBox {
                                            Layout.fillWidth: true
                                            from: 300
                                            to: 2500
                                            stepSize: 50
                                            value: bridge.maxChars
                                            onValueModified: bridge.setMaxChars(value)
                                        }
                                    }

                                    Item { Layout.fillWidth: true }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 18

                                    ColumnLayout {
                                        Layout.preferredWidth: 280
                                        spacing: 8

                                        Text { text: "Voz"; color: Theme.muted; font.pixelSize: 12 }

                                        ComboBox {
                                            Layout.fillWidth: true
                                            model: bridge.voices
                                            currentIndex: Math.max(0, bridge.voices.indexOf(bridge.selectedVoice))
                                            onActivated: bridge.setVoice(currentText)
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        Text {
                                            text: "Velocidad: " + (speedSlider.value / 100).toFixed(2)
                                            color: Theme.muted
                                            font.pixelSize: 12
                                        }

                                        Slider {
                                            id: speedSlider
                                            Layout.fillWidth: true
                                            from: 75
                                            to: 125
                                            stepSize: 1
                                            value: bridge.speed * 100
                                            onMoved: bridge.setSpeed(value / 100)
                                        }
                                    }

                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 22

                                    CheckBox {
                                        text: "Incluir subcarpetas"
                                        checked: bridge.recursive
                                        onToggled: bridge.setRecursive(checked)
                                    }

                                    CheckBox {
                                        text: "Forzar regeneracion"
                                        checked: bridge.force
                                        onToggled: bridge.setForce(checked)
                                    }

                                    CheckBox {
                                        text: "Normalizar volumen"
                                        checked: bridge.normalizeLoudness
                                        onToggled: bridge.setNormalizeLoudness(checked)
                                    }

                                    CheckBox {
                                        text: "Limpiar chunks"
                                        checked: bridge.cleanTemp
                                        onToggled: bridge.setCleanTemp(checked)
                                    }

                                    Item { Layout.fillWidth: true }

                                    Components.PrimaryButton {
                                        text: bridge.isPreviewing ? "Probando..." : "Probar voz"
                                        enabled: !bridge.isPreviewing && bridge.modelsReady && bridge.ffmpegReady
                                        normalColor: "#3e4653"
                                        onClicked: bridge.previewVoice()
                                    }

                                    Components.PrimaryButton {
                                        text: "Abrir prueba"
                                        enabled: bridge.previewReady
                                        normalColor: "#3e4653"
                                        onClicked: bridge.openPreview()
                                    }

                                    Components.PrimaryButton {
                                        text: "Administrar modelos"
                                        normalColor: "#3e4653"
                                        onClicked: modelDialog.open()
                                    }
                                }

                                Text {
                                    text: "Los presets son puntos de partida; puedes ajustar voz, velocidad y chunks despues de aplicarlos."
                                    color: Theme.muted
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: Theme.panel
                            border.color: Theme.border
                            radius: 8

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 14

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    Text {
                                        text: "Modelos Kokoro"
                                        color: Theme.text
                                        font.pixelSize: 16
                                        font.weight: Font.DemiBold
                                    }

                                    Item { Layout.fillWidth: true }

                                    Text {
                                        text: bridge.modelStatusText
                                        color: bridge.modelsReady ? Theme.success : Theme.warning
                                        font.pixelSize: 12
                                        font.weight: Font.DemiBold
                                    }
                                }

                                Text {
                                    text: bridge.modelDir
                                    color: Theme.muted
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    elide: Text.ElideMiddle
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    color: "#10131a"
                                    border.color: Theme.border
                                    radius: 8

                                    ListView {
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        clip: true
                                        spacing: 8
                                        model: bridge.models

                                        delegate: Rectangle {
                                            required property var modelData
                                            width: ListView.view.width
                                            height: 54
                                            radius: 6
                                            color: Theme.panelAlt
                                            border.color: Theme.border

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: 10
                                                anchors.rightMargin: 10
                                                spacing: 12

                                                Text {
                                                    text: modelData.status
                                                    color: modelData.installed ? Theme.success : Theme.warning
                                                    Layout.preferredWidth: 90
                                                    font.weight: Font.DemiBold
                                                }

                                                Text {
                                                    text: modelData.name
                                                    color: Theme.text
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideMiddle
                                                }

                                                Text {
                                                    text: modelData.sizeText
                                                    color: Theme.muted
                                                    Layout.preferredWidth: 90
                                                }
                                            }
                                        }
                                    }
                                }

                                ProgressBar {
                                    Layout.fillWidth: true
                                    from: 0
                                    to: 100
                                    value: bridge.downloadProgress
                                }

                                Text {
                                    text: bridge.downloadStatusText
                                    color: Theme.muted
                                    font.pixelSize: 12
                                    visible: text !== ""
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Components.PrimaryButton {
                                        text: "Descargar faltantes"
                                        enabled: !bridge.modelsReady
                                        onClicked: bridge.downloadMissingModels()
                                    }

                                    Components.PrimaryButton {
                                        text: "Abrir carpeta modelos"
                                        normalColor: "#3e4653"
                                        onClicked: bridge.openModelFolder()
                                    }

                                    Item { Layout.fillWidth: true }
                                }
                            }
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 124
                            color: Theme.panel
                            border.color: Theme.border
                            radius: 8

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 10

                                RowLayout {
                                    Layout.fillWidth: true

                                    Text {
                                        text: "Progreso"
                                        color: Theme.text
                                        font.pixelSize: 16
                                        font.weight: Font.DemiBold
                                    }

                                    Item { Layout.fillWidth: true }

                                    Text {
                                        text: bridge.progress + "%"
                                        color: Theme.muted
                                        font.pixelSize: 12
                                    }
                                }

                                ProgressBar {
                                    Layout.fillWidth: true
                                    from: 0
                                    to: 100
                                    value: bridge.progress
                                }

                                Text {
                                    text: bridge.currentFile === "" ? "Sin conversion activa" : "Archivo actual: " + bridge.currentFile + " | Tiempo: " + bridge.elapsedText
                                    color: Theme.muted
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    elide: Text.ElideMiddle
                                }
                            }
                        }

                        Components.LogPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            logText: bridge.logText
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 60
                color: Theme.panel
                border.color: Theme.border
                radius: 8

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 8

                    Components.PrimaryButton {
                        text: "Actualizar lista"
                        normalColor: "#3e4653"
                        enabled: !bridge.isConverting
                        onClicked: bridge.scanInput()
                    }

                    Components.PrimaryButton {
                        text: "Preparar"
                        normalColor: "#3e4653"
                        onClicked: window.currentSection = 0
                    }

                    Item { Layout.fillWidth: true }

                    Text {
                        text: bridge.progress + "%"
                        color: Theme.muted
                        font.pixelSize: 12
                    }

                    ProgressBar {
                        Layout.preferredWidth: 180
                        from: 0
                        to: 100
                        value: bridge.progress
                    }

                    Components.PrimaryButton {
                        text: "Convertir (" + bridge.selectedFileCount + ")"
                        enabled: !bridge.isConverting && bridge.modelsReady && bridge.ffmpegReady && bridge.selectedFileCount > 0
                        onClicked: bridge.startConversion()
                    }

                    Components.PrimaryButton {
                        text: "Cancelar"
                        normalColor: Theme.warning
                        enabled: bridge.isConverting
                        onClicked: bridge.cancelConversion()
                    }

                    Components.PrimaryButton {
                        text: "Abrir output"
                        normalColor: "#3e4653"
                        onClicked: bridge.openOutput()
                    }
                }
            }
        }
    }

    function sectionSubtitle() {
        if (window.currentSection === 0) return "Selecciona entrada/salida y marca los archivos que entraran en la conversion."
        if (window.currentSection === 1) return "Ajusta voz, velocidad, chunks y verifica los modelos locales de Kokoro."
        return "Revisa el avance global y el registro completo de actividad."
    }
}
