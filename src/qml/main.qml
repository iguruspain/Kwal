// experimental main.qml
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "components" as Components

Kirigami.ApplicationWindow {
    id: root
    visible: true
    width: 1000
    height: 700
    title: "Kwal"
    
    // Global Safe Overlay Color
    // Depends on the compositing state:
    // - Enabled: Semi-transparent (80%) for modern look.
    // - Disabled: Solid Alternate Background Color for readability fallback.
    readonly property color overlayBackgroundColor: controller.compositingEnabled 
        ? Qt.alpha(Kirigami.Theme.backgroundColor, 0.80)
        : Kirigami.Theme.backgroundColor

    function notifyClipboard(text) {
        root.showPassiveNotification(qsTr("Copied: %1").arg(text), "short")
    }
    function notifyOther(text) {
        root.showPassiveNotification(text, "short")
    }
    
    // Enable transparency for the main window
    color: "transparent"


    // Keyboard shortcut for quitting the application
    Shortcut {
        sequence: StandardKey.Quit
        onActivated: Qt.quit()
    }

    pageStack.initialPage: settingsAltRoot
    Kirigami.Page {
        id: settingsAltRoot
        // Shared index between custom header TabBar and SwipeView
        property int currentTabIndex: 0

        // Suppress Kirigami's native opaque toolbar so the custom header inherits transparency
        globalToolBarStyle: Kirigami.ApplicationHeaderStyle.None

        background: Rectangle {
            // Inherit global safe overlay color logic
            color: root.overlayBackgroundColor
        }

        title: "Kwal"

        // Custom header that inherits the same semi-transparent overlay color
        header: ToolBar {
            background: Rectangle {
                color: "transparent"//root.overlayBackgroundColor
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 0

                    // Hamburger menu button — opens the inline application menu
                    ToolButton {
                        id: menuButton
                        icon.name: "open-menu-symbolic"
                        onClicked: appMenu.open()

                        Menu {
                            id: appMenu
                            y: menuButton.height

                            MenuItem {
                                text: qsTr("Transparency Effects")
                                checkable: true
                                checked: controller.compositingEnabled
                                onTriggered: controller.toggleCompositing()
                            }
                            MenuItem {
                                text: qsTr("Simulate All Apps")
                                checkable: true
                                checked: controller.simulateAllApps
                                onTriggered: controller.toggleSimulateAllApps()
                            }
                            MenuItem {
                                text: qsTr("Show Extension Badge")
                                checkable: true
                                checked: controller.showExtensionBadge
                                onTriggered: controller.toggleExtensionBadge()
                            }
                            MenuSeparator {}
                            MenuItem {
                                text: qsTr("Quit")
                                icon.name: "application-exit"
                                onTriggered: Qt.quit()
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }

                    TabBar {
                        currentIndex: settingsAltRoot.currentTabIndex
                        onCurrentIndexChanged: settingsAltRoot.currentTabIndex = currentIndex

                        Repeater {
                            model: controller.settingsAppModel
                            delegate: TabButton {
                                required property string title
                                text: title
                                implicitWidth: Math.max(100, Kirigami.Units.gridUnit * 5)
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }

                    ToolButton {
                        icon.name: "color-picker"
                        ToolTip.text: qsTr("Open Color Palette")
                        ToolTip.visible: hovered
                        onClicked: globalPaletteDialog.open()
                    }
                }

                MenuSeparator {
                    Layout.fillWidth: true
                    Layout.topMargin: Kirigami.Units.smallSpacing
                    Layout.bottomMargin: Kirigami.Units.smallSpacing
                }
            }
        }
        SwipeView {
            id: swipeView
            anchors.fill: parent
            currentIndex: settingsAltRoot.currentTabIndex
            clip: true
            onCurrentIndexChanged: settingsAltRoot.currentTabIndex = currentIndex

            // Use a Repeater to preserve page state
            Repeater {
                model: controller.settingsAppModel
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
        visible: !controller.templatesInstalled()
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            // call the controller slot to install templates
            controller.installTemplates()
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
        target: controller
        function onNotification(message, type) {
            if (type === "error" && message !== "") {
                root.showPassiveNotification(message, "short")
            }
        }
    }

    // Generic Result Dialog (Global)
    Dialog {
        id: resultDialog
        visible: controller.resultDialogVisible
        modal: true
        title: qsTr("Notification") 
        standardButtons: Dialog.Ok
        onAccepted: controller.resultDialogVisible = false
        onRejected: controller.resultDialogVisible = false
        
        // Ensure close from X button also updates controller state
        onVisibleChanged: {
            if (!visible) controller.resultDialogVisible = false
        }

        contentItem: Label {
            text: controller.resultDialogText
            wrapMode: Text.WordWrap
            topPadding: Kirigami.Units.smallSpacing
            bottomPadding: Kirigami.Units.smallSpacing
            leftPadding: Kirigami.Units.smallSpacing
            rightPadding: Kirigami.Units.smallSpacing
        }
    }

    Components.DialogPalette {
        id: globalPaletteDialog
        // Can be opened from anywhere, doesn't need to apply to a specific field.
        // It's just a reference/generator tool globally.
        anchors.centerIn: parent
    }
}