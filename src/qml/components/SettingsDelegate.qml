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
    property bool isSelected: index === (targetListView ? targetListView.currentIndex : -1)
    
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
                        delegateRoot.requestPage(pageURL);
                        //update selected index
                        if (delegateRoot.targetListView) {
                            delegateRoot.targetListView.currentIndex = delegateRoot.index;
                        }
                    }
                }
            }
        }
        // selection border: anchored to the listItem but with a smaller bottom margin
        Rectangle {
            id: selectionBorder
            anchors.margins: -Kirigami.Units.smallSpacing / 2
            //anchors.fill: listItem
            //anchors.centerIn: listItem
            width: parent.width
            height: parent.height + Kirigami.Units.smallSpacing * 1.5

            color: "transparent"
            border.color: isSelected ? Kirigami.Theme.highlightColor : Qt.transparent
            border.width: isSelected ? 2 : 0
            radius: Kirigami.Units.smallSpacing
            visible: isSelected
        }
    }
}
