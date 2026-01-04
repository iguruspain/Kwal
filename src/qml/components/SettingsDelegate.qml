import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.SwipeListItem {
    id: listItem
    
    required property string title
    required property string qmlpage
    
    signal requestPage(string pageUrl)

    contentItem: RowLayout {
        // Drag handle disabled for Python model compatibility for now
        // Kirigami.ListItemDragHandle {
        //     listItem: listItem
        //     listView: listItem.ListView.view
        //     onMoveRequested: (old, curr) => listItem.ListView.view.model.move(old, curr, 1)
        // }

        Label {
            id: itemLabel
            text: listItem.title
            Layout.fillWidth: true
            
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    // Resolve URL relative to this file? 
                    // The qmlpage path from python is "apps/ulauncher.qml".
                    // If this file is in src/qml/components/, then "apps/..." refers to src/qml/components/apps/...
                    // Which matches the structure.
                    let pageURL = Qt.resolvedUrl(listItem.qmlpage);
                    listItem.requestPage(pageURL)
                }
            }
        }
    }
}
