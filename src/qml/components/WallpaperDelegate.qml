import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.AbstractCard {
    id: card
    Layout.fillWidth: true

    contentItem: RowLayout {
        id: delegateLayout
        spacing: Kirigami.Units.smallSpacing

        Label {
            text: name
            font.bold: true
            Layout.fillWidth: true
            verticalAlignment: Text.AlignVCenter
            Layout.alignment: Qt.AlignVCenter
            // Make the label itself clickable to select the folder
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    pyController.selectFolder(index)
                }
            }
        }
        ToolButton {
            id: removeFolderButton
            icon.name: "edit-delete"
            icon.width: Kirigami.Units.gridUnit
            icon.height: Kirigami.Units.gridUnit
            Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
            // Disable removal for the built-in Local folder
            enabled: name !== "Local"
            onClicked: {
                if (!enabled) return
                console.log("DEBUG remove clicked - index:", index, "typeof:", typeof index, "name:", name, "path:", path)
                pyController.removeFolder(index)
            }
        }
    }

    
}
