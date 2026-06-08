import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import md2audio.style

Rectangle {
    id: root
    property var files: []
    property int selectedIndex: -1
    signal rowSelected(int index)

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

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Text { text: "Archivos detectados"; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold }
            Item { Layout.fillWidth: true }
            Text { text: root.files.length + " archivos"; color: Theme.muted; font.pixelSize: 12 }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 28
            color: "#151821"
            radius: 5
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 12
                Text { text: "Estado"; color: Theme.muted; Layout.preferredWidth: 92; font.pixelSize: 12 }
                Text { text: "Archivo"; color: Theme.muted; Layout.fillWidth: true; font.pixelSize: 12 }
                Text { text: "Tiempo"; color: Theme.muted; Layout.preferredWidth: 90; font.pixelSize: 12 }
                Text { text: "Mensaje"; color: Theme.muted; Layout.preferredWidth: 180; font.pixelSize: 12 }
            }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 6
            model: root.files

            delegate: Rectangle {
                required property int index
                required property var modelData
                width: list.width
                height: 42
                radius: 6
                color: index === root.selectedIndex ? "#253246" : Theme.panelAlt
                border.color: index === root.selectedIndex ? Theme.accent : Theme.border

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 12

                    Text {
                        text: modelData.status
                        color: root.statusColor(modelData.status)
                        Layout.preferredWidth: 92
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        text: modelData.relativePath
                        color: Theme.text
                        Layout.fillWidth: true
                        font.pixelSize: 12
                        elide: Text.ElideMiddle
                    }

                    Text {
                        text: modelData.time
                        color: Theme.muted
                        Layout.preferredWidth: 90
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }

                    Text {
                        text: modelData.message
                        color: Theme.muted
                        Layout.preferredWidth: 180
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: root.rowSelected(index)
                }
            }
        }
    }
}
