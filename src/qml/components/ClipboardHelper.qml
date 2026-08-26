import QtQuick

// Invisible TextEdit used to copy text to the clipboard and notify the user.
TextEdit {
    id: _clipboard
    visible: false

    function copyToClipboard(text) {
        _clipboard.text = text
        _clipboard.selectAll()
        _clipboard.copy()
        if (applicationWindow())
            applicationWindow().showPassiveNotification(qsTr("Copied: %1").arg(text), "short")
    }
}
