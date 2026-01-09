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
    width: 800
    height: 610
    title: "Kwal"
    
    // Enable transparency for the main window
    color: "transparent"

    pageStack.initialPage: settingsAltRoot
    Kirigami.Page {
        id: settingsAltRoot
        background: Rectangle {
            color: Kirigami.Theme.backgroundColor
            opacity: 0.8 
        }
        
        // El título cambia dinámicamente según la pestaña seleccionada
        title: {
            const item = pyController.settingsAppModel.get(tabBar.currentIndex);
            return item ? item.title : "Settings";
        }

        header: Pane {
            // Usamos un Pane para dar un fondo consistente al header
            background: Rectangle { color: "transparent" }
            topPadding: Kirigami.Units.smallSpacing
            bottomPadding: 0

            contentItem: RowLayout {
                width: parent.width

                // Espaciador izquierdo
                Item { Layout.fillWidth: true }

                TabBar {
                    id: tabBar
                    currentIndex: swipeView.currentIndex
                    
                    // Quitamos el fondo por defecto de la TabBar si quieres un look más limpio
                    background: Rectangle { color: "transparent" }

                    Repeater {
                        model: pyController.settingsAppModel
                        delegate: TabButton {
                            required property string title
                            text: title
                            
                            // Opcional: ajustar el ancho de los botones
                            implicitWidth: Math.max(100, Kirigami.Units.gridUnit * 5)
                        }
                    }
                }

                // Espaciador derecho
                Item { Layout.fillWidth: true }
            }
        }

        SwipeView {
            id: swipeView
            anchors.fill: parent
            currentIndex: tabBar.currentIndex
            clip: true

            // Implementación con Repeater para mantener el estado de las páginas
            Repeater {
                model: pyController.settingsAppModel
                delegate: Loader {
                    required property string qmlpage
                    required property int index
                    
                    // Solo carga la página si es la actual o la adyacente para fluidez
                    active: SwipeView.isCurrentItem || SwipeView.isNextItem || SwipeView.isPreviousItem
                    source: "components/" + qmlpage
                    
                    // Evita que las páginas no visibles intercepten eventos o consuman CPU
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
}