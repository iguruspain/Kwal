// experimental main.qml
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
//import "components" as Components

Kirigami.ApplicationWindow {
    id: root
    visible: true
    width: 820
    height: 610
    title: "Kwal"
    
    // Global Safe Overlay Color
    // Depends on the compositing state:
    // - Enabled: Semi-transparent (80%) for modern look.
    // - Disabled: Solid Alternate Background Color for readability fallback.
    readonly property color overlayBackgroundColor: pyController.compositingEnabled 
        ? Qt.alpha(Kirigami.Theme.backgroundColor, 0.80)
        : Kirigami.Theme.backgroundColor
    
    // Enable transparency for the main window
    color: "transparent"


    // Global Drawer for Application Settings
    globalDrawer: Kirigami.GlobalDrawer {
        isMenu: true
        modal: true
        
        actions: [
            Kirigami.Action {
                text: qsTr("Application Settings")
                icon.name: "configure"
                // Group actions under a header
                Kirigami.Action {
                    text: qsTr("Transparency Effects")
                    checkable: true
                    checked: pyController.compositingEnabled
                    onToggled: pyController.toggleCompositing()
                    icon.name: "blur-on" 
                }
            },
            Kirigami.Action {
                text: qsTr("Quit")
                icon.name: "application-exit"
                shortcut: StandardKey.Quit
                onTriggered: Qt.quit()
            }
        ]
    }

    pageStack.initialPage: settingsAltRoot
    Kirigami.Page {
        id: settingsAltRoot
        background: Rectangle {
            // Inherit global safe overlay color logic
            color: root.overlayBackgroundColor
        }
        
        // The title updates dynamically based on the selected tab
        title: {
            const item = pyController.settingsAppModel.get(tabBar.currentIndex);
            return item ? item.title : "Settings";
        }

        header: Pane {
            // Use a Pane to give a consistent background to the header
            background: Rectangle { color: "transparent" }
            topPadding: Kirigami.Units.smallSpacing
            bottomPadding: 0

            contentItem: RowLayout {
                width: parent.width

                // Left spacer
                Item { Layout.fillWidth: true }

                TabBar {
                    id: tabBar
                    currentIndex: swipeView.currentIndex
                    
                    // Remove the TabBar default background for a cleaner look
                    background: Rectangle { color: "transparent" }

                    Repeater {
                        model: pyController.settingsAppModel
                        delegate: TabButton {
                            required property string title
                            text: title
                            
                            // Optional: adjust button widths
                            implicitWidth: Math.max(100, Kirigami.Units.gridUnit * 5)
                        }
                    }
                }

                // Right spacer
                Item { Layout.fillWidth: true }
            }
        }

        SwipeView {
            id: swipeView
            anchors.fill: parent
            currentIndex: tabBar.currentIndex
            clip: true

            // Use a Repeater to preserve page state
            Repeater {
                model: pyController.settingsAppModel
                delegate: Loader {
                    required property string qmlpage
                    required property int index
                    
                    // Only load the page if it's current or adjacent for smoothness
                    active: SwipeView.isCurrentItem || SwipeView.isNextItem || SwipeView.isPreviousItem
                    source: "components/" + qmlpage
                    
                    // Prevent non-visible pages from intercepting events or consuming CPU
                    visible: SwipeView.isCurrentItem
                }
            }
        }
    }
    // First-run dialog: offer to install packaged templates to the user's config
    Dialog {
        id: templatesDialog
        title: qsTr("Install templates")
        visible: !pyController.templatesInstalled()
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            // call the controller slot to install templates
            pyController.installTemplates()
            templatesDialog.visible = false
        }
        onRejected: {
            templatesDialog.visible = false
        }
        ColumnLayout {
            anchors.fill: parent
            Label { text: qsTr("Install default templates to your user configuration (~/.config/kwal/templates)?") }
        }
    }
    // Connect passive notifications from Python Controller
    Connections {
        target: pyController
        function onNotification(message, type) {
            if (type === "error" && message !== "") {
                root.showPassiveNotification(message, "short")
            }
        }
    }

    // Generic Result Dialog (Global)
    Dialog {
        id: resultDialog
        visible: pyController.resultDialogVisible
        modal: true
        title: qsTr("Notification") 
        standardButtons: Dialog.Ok
        onAccepted: pyController.resultDialogVisible = false
        onRejected: pyController.resultDialogVisible = false
        
        // Ensure close from X button also updates controller state
        onVisibleChanged: {
            if (!visible) pyController.resultDialogVisible = false
        }

        contentItem: Label {
            text: pyController.resultDialogText
            wrapMode: Text.WordWrap
            topPadding: Kirigami.Units.smallSpacing
            bottomPadding: Kirigami.Units.smallSpacing
            leftPadding: Kirigami.Units.smallSpacing
            rightPadding: Kirigami.Units.smallSpacing
        }
    }
}