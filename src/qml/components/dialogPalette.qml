pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Dialog {
    id: dialogPalette
    title: qsTr("Select Color Palette")
    // Define dialog
    
    
    //Model for color palettes will be implemeted in models.py
    ListModel {
        ListElement {
            target_item: "" //will be the item to be updated with the selected color (draft? state management?)
            currentWallpaperImage: "" // Path to wallpaper image
            selectedWallpaperImage: "" // Path to selected wallpaper image in wallpapers.qml
            extract_method: ["pywal16","material-you","imagemagick"] // Example extraction methods functions will be in color_utils.py, material you needs materialyoucolors module
            aux_parameters: {
                method: "pywal16", params: "none"
                method: "material-you", params: {image:"", mode: "", tone: "", etc} // Auxiliary parameters for material-you extraction
                method: "imagemagick", params: "none"               
            } // Auxiliary parameters for extraction methods if needed
            mode: ["light","dark"]
            colors: [] // Array of 16 colors
            accent_colors: [] // Undefined array of colors using special function to get accent colors, array length may vary depending on extraction method
        }
        // Additional info for imagemagick method accent extraction: bash script (its only an idea, for scoring best we can use other methods)
        // accent_hex=$(magick "$wallpaper_path" -resize 64x64 +dither -colors 8 -format "%c" histogram:info: \
        // | gawk '
        //     BEGIN{best_score=0; best=""}
        //     {
        //     if (match($0, /#([0-9A-Fa-f]{6})/, m)) {
        //         hex=tolower(m[1])
        //         r = strtonum("0x" substr(hex,1,2))
        //         g = strtonum("0x" substr(hex,3,2))
        //         b = strtonum("0x" substr(hex,5,2))
        //         r1=r/255; g1=g/255; b1=b/255
        //         mx = (r1>g1? (r1>b1? r1:b1) : (g1>b1? g1:b1))
        //         mn = (r1<g1? (r1<b1? r1:b1) : (g1<b1? g1:b1))
        //         v = mx
        //         d = mx - mn
        //         s = (mx==0? 0 : d/mx)
        //         if (s > 0.15 && v > 0.15 && v < 0.95) {
        //         score = s * v
        //         if (score > best_score) { best_score=score; best="#"hex }
        //         }
        //     }
        //     }
        //     END{
        //     if (best!="") print best
        //     exit(best==""?1:0)
        //     }' )
    }
    
    // Dialog content:
    // Select between current wallpaper or selected wallpaper
    // Preview of wallpaper
    // Extraction method selection (combobox) and Mode selection, dark or light (radiobuttons), extract (button). All in same row
    // Auxiliary parameters depending on extraction method, e.g. material-you sliders for to
    // Color palette preview (grid of color swatches (hex alpha), 2 rows 8 colors per row, tooltip with hex code on hover, allow highlight on click)
    // Accent colors preview (similar to color palette preview, rows of 8 colors per row, dynamic number of swatches), etc. Special behavior for material-you accent can be selectect with rigth click as seed_color for generating palette? and badge to indicate it.
    // Accept or cancel buttons, accept applies the selected color (highlighted) to the target control, e.g. colorPreview.color

}