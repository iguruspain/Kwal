import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.AbstractCard {
    id: card
    Layout.fillWidth: true
    // Visually indicate selection by comparing the folder path with controller.selectedFolder
    property bool isSelected: path === pyController.selectedFolder
    property bool isHovered: mouseArea.containsMouse

    // Selection border
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: isHovered ? Kirigami.Theme.focusColor : (isSelected ? Kirigami.Theme.highlightColor : Qt.alpha(Kirigami.Theme.textColor, 0.1))
        border.width: isSelected ? 3 : 1
        radius: Kirigami.Units.smallSpacing
        visible: card.isSelected || card.isHovered
    }

    contentItem: Item {
        implicitHeight: delegateLayout.implicitHeight

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            onClicked: pyController.selectFolder(index)
            cursorShape: Qt.PointingHandCursor
        }
        
        GridLayout {
            id: delegateLayout
            anchors.fill: parent
            columns: 2
            columnSpacing: Kirigami.Units.smallSpacing
            rowSpacing: Kirigami.Units.smallSpacing
            ColumnLayout {
                Kirigami.Heading {
                    level: 2
                    text: name
                }
                Kirigami.Separator {
                    Layout.fillWidth: true
                }
                Label {
                    Layout.fillWidth: true
                    // wrapMode: Text.WordWrap
                    text: {
                        if (name !== "Local") {
                            return path.replace(pyController.homePath, "~\/")
                        } else {
                            return path
                        }
                    }
                    color: Kirigami.Theme.disabledTextColor
                    font.pixelSize: Kirigami.Units.smallSpacing * 3
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
