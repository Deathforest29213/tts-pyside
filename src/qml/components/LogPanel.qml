import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import md2audio.style

Rectangle {
    id: root
    property string logText: ""
    color: Theme.panel
    border.color: Theme.border
    radius: 8

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        Text {
            text: "Log"
            color: Theme.text
            font.pixelSize: 15
            font.weight: Font.DemiBold
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            TextArea {
                text: root.logText
                readOnly: true
                wrapMode: TextArea.Wrap
                color: Theme.text
                selectedTextColor: "#ffffff"
                selectionColor: Theme.accentDark
                font.family: "Consolas"
                font.pixelSize: 12
                background: Rectangle { color: "#10131a"; radius: 6 }
            }
        }
    }
}
