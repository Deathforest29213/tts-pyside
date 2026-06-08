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

    Material.theme: Material.Dark
    Material.accent: Theme.accent

    onClosing: bridge.saveWindowSize(width, height)

    Components.ModelManagerDialog {
        id: modelDialog
        anchors.centerIn: Overlay.overlay
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Text {
                    text: "md2audio"
                    color: Theme.text
                    font.pixelSize: 24
                    font.weight: Font.Bold
                }
                Text {
                    text: "Conversor TTS local con Kokoro"
                    color: Theme.muted
                    font.pixelSize: 13
                }
            }

            Rectangle {
                radius: 14
                color: bridge.modelsReady ? "#173324" : "#3b2d16"
                border.color: bridge.modelsReady ? Theme.success : Theme.warning
                height: 30
                width: 180
                Text {
                    anchors.centerIn: parent
                    color: bridge.modelsReady ? Theme.success : Theme.warning
                    text: "Kokoro: " + bridge.modelStatusText
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                }
            }
        }

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

        Rectangle {
            Layout.fillWidth: true
            height: 134
            color: Theme.panel
            radius: 8
            border.color: Theme.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10

                Text {
                    text: "Configuracion Kokoro"
                    color: Theme.text
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    ColumnLayout {
                        Layout.preferredWidth: 220
                        Text { text: "Voz"; color: Theme.muted; font.pixelSize: 12 }
                        ComboBox {
                            id: voiceCombo
                            Layout.fillWidth: true
                            model: bridge.voices
                            currentIndex: Math.max(0, bridge.voices.indexOf(bridge.selectedVoice))
                            onActivated: bridge.setVoice(currentText)
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "Velocidad: " + (speedSlider.value / 100).toFixed(2); color: Theme.muted; font.pixelSize: 12 }
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

                    ColumnLayout {
                        Layout.preferredWidth: 150
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

                    ColumnLayout {
                        Layout.preferredWidth: 210
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
                    }

                    Components.PrimaryButton {
                        text: "Administrar modelos"
                        normalColor: "#3e4653"
                        onClicked: modelDialog.open()
                    }
                }
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

        Rectangle {
            Layout.fillWidth: true
            height: 94
            color: Theme.panel
            border.color: Theme.border
            radius: 8

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "Progreso"
                        color: Theme.text
                        font.pixelSize: 15
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
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                }
            }
        }

        Components.LogPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 180
            logText: bridge.logText
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Components.PrimaryButton {
                text: "Actualizar lista"
                normalColor: "#3e4653"
                enabled: !bridge.isConverting
                onClicked: bridge.scanInput()
            }

            Item { Layout.fillWidth: true }

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
