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

    // Model example for Fastfetch configurations
    ListModel {
        id: fastfetchModel
        ListElement {
            config_path: "~/.config/fastfetch/config.jsonc" // Path to Fastfetch config file, will be obtained using config_readers.py functions
            config_image: "~/.config/fastfetch/chica-tinted.png" // Path to Fastfetch config image, will be obtained using config_readers.py functions
            template_image_folder: "~/.config/kwal/templates/fastfetch" // Path to Fastfetch template images folder, should be present by default (kwal installation)
            }
        }

    RowLayout {
        anchors.fill: parent
        spacing: Kirigami.Units.smallSpacing

        // Left Pane for Fastfetch settings
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
                }
            }
        }
    }
}