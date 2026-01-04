import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Page{
    id: fastfetchPage
    title: qsTr("Fastfetch Settings")

    background: Rectangle {
        // color: Kirigami.Theme.backgroundColor
        // opacity: 0.8
        color: "transparent"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing

        Text {
            Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
            text: qsTr("Fastfetch settings will go here.")
            font.pointSize: 14
            color: Kirigami.Theme.textColor
        }
    }
    actions: [
        Kirigami.Action {
            icon.name: "go-previous"
            text: qsTr("Back")
            onTriggered: {
                    StackView.view.pop()
            }
        }
    ]
}