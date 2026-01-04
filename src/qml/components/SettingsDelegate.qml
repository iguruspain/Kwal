import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    id: delegateRoot
    
    required property string title
    required property string qmlpage
    required property int index
    
    property ListView targetListView: ListView.view
    
    signal requestPage(string pageUrl)

    width: targetListView ? targetListView.width - targetListView.leftMargin - targetListView.rightMargin : 0
    height: listItem.implicitHeight

    Kirigami.SwipeListItem {
        id: listItem
        
        width: delegateRoot.width
        
        contentItem: RowLayout {
            Kirigami.ListItemDragHandle {
                listItem: listItem
                listView: delegateRoot.targetListView
                onMoveRequested: (oldIndex, newIndex) => {
                    delegateRoot.targetListView.model.move(oldIndex, newIndex, 1)
                }
            }

            Label {
                id: itemLabel
                text: delegateRoot.title
                Layout.fillWidth: true
                
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        let pageURL = Qt.resolvedUrl(delegateRoot.qmlpage);
                        delegateRoot.requestPage(pageURL)
                    }
                }
            }
        }
    }
}
