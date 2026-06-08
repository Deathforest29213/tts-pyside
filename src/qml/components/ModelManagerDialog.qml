import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import md2audio.style

Dialog {
    id: dialog
    modal: true
    title: "Modelos Kokoro"
    standardButtons: Dialog.NoButton
    width: 720
    height: 420

    background: Rectangle {
        color: Theme.panel
        radius: 10
        border.color: Theme.border
    }

    contentItem: ColumnLayout {
        spacing: 12

        Text {
            text: "Estado de modelos locales"
            color: Theme.text
            font.pixelSize: 16
            font.weight: Font.DemiBold
        }

        Text {
            text: bridge.modelDir
            color: Theme.muted
            font.pixelSize: 12
            elide: Text.ElideMiddle
            Layout.fillWidth: true
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

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            PrimaryButton {
                text: "Descargar faltantes"
                enabled: !bridge.modelsReady
                onClicked: bridge.downloadMissingModels()
            }
            PrimaryButton {
                text: "Abrir carpeta modelos"
                normalColor: "#3e4653"
                onClicked: bridge.openModelFolder()
            }
            Item { Layout.fillWidth: true }
            PrimaryButton {
                text: "Cerrar"
                normalColor: "#3e4653"
                onClicked: dialog.close()
            }
        }
    }
}
