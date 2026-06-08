import QtQuick
import QtQuick.Controls
import md2audio.style

Button {
    id: control
    property color normalColor: Theme.accent
    property color pressedColor: Theme.accentDark
    property color disabledColor: "#3a404b"
    font.pixelSize: 13
    font.weight: Font.DemiBold
    padding: 10

    contentItem: Text {
        text: control.text
        color: control.enabled ? "#ffffff" : Theme.muted
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        font: control.font
    }

    background: Rectangle {
        radius: 6
        color: !control.enabled ? control.disabledColor : control.down ? control.pressedColor : control.normalColor
        border.color: Qt.lighter(color, 1.15)
        border.width: control.hovered && control.enabled ? 1 : 0
    }
}
