import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Page{
    id: fastfetchPage
    title: qsTr("Fastfetch Settings")

    background: Rectangle {
        color: "transparent"
    }

    // Model for Fastfetch configurations
    ListModel {
        id: fastfetchModel
        ListElement {
            config_path: "config_path"
            config_image: "config_image"
            template_image_folder: "~/templates/fastfetch"
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: Kirigami.Units.smallSpacing

        Rectangle {
            id: leftPaneFastfetch
            color: Kirigami.Theme.backgroundColor
            Layout.preferredWidth: 360
            Layout.fillHeight: true
            radius: 0
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing
                Text {
                    text: qsTr("Fastfetch settings will go here.")
                    color: Kirigami.Theme.textColor
                }
            }
        }

        Rectangle {
            id: rightPaneFastfetch
            color: Kirigami.Theme.backgroundColor
            Layout.fillWidth: true
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing
                RowLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Text {
                        text: qsTr("Fastfetch Preview")
                        font.bold: true
                        color: Kirigami.Theme.textColor
                    }
                    Image {
                        source: "qrc:/images/kwal.png"
                        width: 24
                        height: 24
                        fillMode: Image.PreserveAspectFit
                    }
                }
            }
        }
    }
}