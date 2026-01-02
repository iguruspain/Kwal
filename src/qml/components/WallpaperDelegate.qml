import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.AbstractCard {
    id: card
    Layout.fillWidth: true
    // Visually indicate selection by comparing the folder path with controller.selectedFolder
    property bool isSelected: path === pyController.selectedFolder

    // Selection border
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: Kirigami.Theme.highlightColor
        border.width: card.isSelected ? 2 : 0
        radius: Kirigami.Units.smallSpacing
        visible: card.isSelected
    }

    contentItem: Item {
        implicitHeight: delegateLayout.implicitHeight

        MouseArea {
            anchors.fill: parent
            onClicked: pyController.selectFolder(index)
            cursorShape: Qt.PointingHandCursor
        }

        RowLayout {
            id: delegateLayout
            anchors.fill: parent
            spacing: Kirigami.Units.smallSpacing

            Label {
                text: name
                font.bold: true
                Layout.fillWidth: true
                verticalAlignment: Text.AlignVCenter
                Layout.alignment: Qt.AlignVCenter
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
                    pyController.removeFolder(index)
                }
                hoverEnabled: true
                ToolTip.text: qsTr("Remove this folder")
                ToolTip.visible: hovered
                ToolTip.delay: Kirigami.Units.toolTipDelay
            }
        }
    }
}
