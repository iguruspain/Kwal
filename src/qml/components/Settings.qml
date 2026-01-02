import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import org.kde.kirigami as Kirigami

Kirigami.Page {
    id: settingsPage
    title: qsTr("Settings")

    // Custom background to ensure content is opaque but header can be transparent
    background: Rectangle {
        color: Kirigami.Theme.backgroundColor
        opacity: 0.8 
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing

        // Label {
        //     text: qsTr("Settings will go here.")
        //     horizontalAlignment: Text.AlignHCenter
        //     Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
        // }
        
    }
}