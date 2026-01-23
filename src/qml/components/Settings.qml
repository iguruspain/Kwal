pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Page {
    id: settingsAltRoot
    background: Rectangle {
        color: Kirigami.Theme.backgroundColor
        opacity: 0.8 
    }
    
    // El título cambia dinámicamente según la pestaña seleccionada
    title: {
        const item = controller.settingsAppModel.get(tabBar.currentIndex);
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
                    model: controller.settingsAppModel
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
            model: controller.settingsAppModel
            delegate: Loader {
                required property string qmlpage
                required property int index
                
                // Solo carga la página si es la actual o la adyacente para fluidez
                active: SwipeView.isCurrentItem || SwipeView.isNextItem || SwipeView.isPreviousItem
                source: qmlpage
                
                // Evita que las páginas no visibles intercepten eventos o consuman CPU
                visible: SwipeView.isCurrentItem
            }
        }
    }
}