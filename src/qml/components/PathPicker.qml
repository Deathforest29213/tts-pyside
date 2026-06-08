import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import md2audio.style

Rectangle {
    id: root
    property string title: ""
    property string path: ""
    signal fileRequested()
    signal folderRequested()
    signal openRequested()

    color: Theme.panel
    border.color: Theme.border
    radius: 8
    implicitHeight: 112

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        Text {
            text: root.title
            color: Theme.text
            font.pixelSize: 14
            font.weight: Font.DemiBold
        }

        Rectangle {
            Layout.fillWidth: true
            height: 34
            color: Theme.panelAlt
            radius: 6
            border.color: Theme.border

            Text {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                color: Theme.text
                text: root.path
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideMiddle
                font.pixelSize: 12
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            PrimaryButton {
                text: "Seleccionar archivo"
                visible: root.title === "Entrada"
                onClicked: root.fileRequested()
            }

            PrimaryButton {
                text: root.title === "Entrada" ? "Seleccionar carpeta" : "Cambiar"
                visible: root.title === "Entrada"
                normalColor: "#3e4653"
                onClicked: root.folderRequested()
            }

            Item { Layout.fillWidth: true }

            PrimaryButton {
                text: root.title === "Entrada" ? "Abrir input" : "Abrir output"
                normalColor: "#3e4653"
                onClicked: root.openRequested()
            }
        }
    }
}
