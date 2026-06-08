import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import md2audio.style
import "." as Components

Rectangle {
    id: root
    property var files: []
    property int selectedIndex: -1
    readonly property var selectedFile: selectedIndex >= 0 && selectedIndex < files.length ? files[selectedIndex] : null
    signal rowSelected(int index)
    signal toggleFileRequested(int index)
    signal toggleAllRequested()
    signal openMp3Requested()
    signal openManifestRequested()
    signal openOutputRequested()

    color: Theme.panel
    border.color: Theme.border
    radius: 8

    function statusColor(status) {
        if (status === "Listo") return Theme.success
        if (status === "Generando") return Theme.accent
        if (status === "Error") return Theme.error
        if (status === "Cancelado") return Theme.warning
        return Theme.pending
    }

    function shortTitle(path) {
        const normalized = String(path || "").replace(/\\/g, "/")
        const name = normalized.split("/").pop() || "archivo"
        return name.replace(/\.md$/i, "")
    }

    function statusLabel(file) {
        if (!file) return "Selecciona un archivo"
        if (file.time && file.time !== "") return file.status + " · " + file.time
        return file.status || "Pendiente"
    }

    function includedCount() {
        let count = 0
        for (let index = 0; index < root.files.length; index += 1) {
            if (root.files[index].included) count += 1
        }
        return count
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "Archivos detectados"
                color: Theme.text
                font.pixelSize: 15
                font.weight: Font.DemiBold
            }
            Item { Layout.fillWidth: true }
            Text {
                text: root.includedCount() + " seleccionados / " + root.files.length + " archivos"
                color: Theme.muted
                font.pixelSize: 12
            }
        }

        GridView {
            id: grid
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            cellWidth: Math.max(168, Math.floor(width / Math.max(1, Math.floor(width / 184))))
            cellHeight: 92
            model: root.files
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}

            delegate: Rectangle {
                required property int index
                required property var modelData
                width: grid.cellWidth - 8
                height: 82
                radius: 8
                color: index === root.selectedIndex ? "#253246" : modelData.included ? "#19212a" : "#151821"
                border.color: index === root.selectedIndex ? Theme.accent : Theme.border
                border.width: index === root.selectedIndex ? 2 : 1
                opacity: modelData.included ? 1 : 0.72

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 6

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            color: root.statusColor(modelData.status)
                            Layout.alignment: Qt.AlignVCenter
                        }

                        Text {
                            text: modelData.status || "Pendiente"
                            color: root.statusColor(modelData.status)
                            Layout.fillWidth: true
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        Rectangle {
                            width: 18
                            height: 18
                            radius: 4
                            color: modelData.included ? Theme.accent : "transparent"
                            border.color: modelData.included ? Theme.accent : Theme.border

                            Text {
                                anchors.centerIn: parent
                                text: modelData.included ? "✓" : ""
                                color: "#ffffff"
                                font.pixelSize: 12
                                font.weight: Font.Bold
                            }
                        }
                    }

                    Text {
                        text: root.shortTitle(modelData.relativePath)
                        color: Theme.text
                        Layout.fillWidth: true
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                        maximumLineCount: 1
                    }

                    Text {
                        text: modelData.message && modelData.message !== "" ? modelData.message : (modelData.time || "Sin procesar")
                        color: Theme.muted
                        Layout.fillWidth: true
                        font.pixelSize: 11
                        elide: Text.ElideRight
                        maximumLineCount: 1
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        root.rowSelected(index)
                        root.toggleFileRequested(index)
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 58
            radius: 7
            color: "#151821"
            border.color: Theme.border

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 10
                spacing: 10

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: root.selectedFile ? "Seleccionado: " + root.shortTitle(root.selectedFile.relativePath) : "Selecciona un archivo"
                        color: Theme.text
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        Layout.fillWidth: true
                        elide: Text.ElideMiddle
                    }

                    Text {
                        text: root.selectedFile ? root.statusLabel(root.selectedFile) : "Las acciones se habilitan al elegir una tarjeta"
                        color: root.selectedFile ? root.statusColor(root.selectedFile.status) : Theme.muted
                        font.pixelSize: 11
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }

                Components.PrimaryButton {
                    text: root.files.length > 0 && root.includedCount() === root.files.length ? "Deseleccionar todo" : "Agregar todo"
                    normalColor: "#3e4653"
                    enabled: root.files.length > 0
                    onClicked: root.toggleAllRequested()
                }

                Components.PrimaryButton {
                    text: "Abrir MP3"
                    normalColor: "#3e4653"
                    enabled: root.selectedFile !== null
                    onClicked: root.openMp3Requested()
                }

                Components.PrimaryButton {
                    text: "Abrir manifest"
                    normalColor: "#3e4653"
                    enabled: root.selectedFile !== null
                    onClicked: root.openManifestRequested()
                }

                Components.PrimaryButton {
                    text: "Abrir carpeta"
                    normalColor: "#3e4653"
                    onClicked: root.openOutputRequested()
                }
            }
        }
    }
}
