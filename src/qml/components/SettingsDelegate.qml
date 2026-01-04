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

    // Selection helpers: compare delegate index with the ListView currentIndex
    property bool isSelected: index === (targetListView ? targetListView.currentIndex : -1)
    
    signal requestPage(string pageUrl)

    width: targetListView ? targetListView.width - targetListView.leftMargin - targetListView.rightMargin : 0
    height: listItem.implicitHeight

    Kirigami.SwipeListItem {
        id: listItem
        anchors.fill: parent
        //width: delegateRoot.width
        // selection border: anchored to the listItem but with a smaller bottom margin
        Rectangle {
            id: selectionBorder
            anchors.margins: -Kirigami.Units.smallSpacing / 2
            //anchors.fill: listItem
            //anchors.centerIn: listItem
            width: listItem.width
            height: listItem.height + Kirigami.Units.smallSpacing * 1.5

            color: "transparent"
            border.color: isSelected ? Kirigami.Theme.highlightColor : Qt.transparent
            border.width: isSelected ? 2 : 0
            radius: Kirigami.Units.smallSpacing
            visible: isSelected
        }        
        contentItem: RowLayout {
            id: contentRow
            //anchors.fill: parent

            Kirigami.ListItemDragHandle {
                listItem: listItem
                listView: delegateRoot.targetListView
                onMoveRequested: (oldIndex, newIndex) => {
                    delegateRoot.targetListView.model.move(oldIndex, newIndex, 1)
                }
                onDropped: (oldIndex, newIndex) => {
                    console.log(">>>", oldIndex, newIndex)
                }
            }

            Label {
                id: itemLabel
                text: delegateRoot.title
                Layout.fillWidth: true
                // Full-area MouseArea to handle clicks and hover (keeps drag handle working)
                MouseArea {
                    id: itemMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        // update ListView selection so delegates can react via `isSelected`
                        if (delegateRoot.targetListView) {
                            delegateRoot.targetListView.currentIndex = index
                        }
                        let pageURL = Qt.resolvedUrl(delegateRoot.qmlpage)
                        delegateRoot.requestPage(pageURL)
                    }
                }                
            }
        }
    }
}
