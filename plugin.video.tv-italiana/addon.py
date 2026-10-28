# -*- coding: utf-8 -*-
"""Menu essenziale per aprire le dirette Rai tramite l'add-on Rai Play."""

import sys

import xbmc
import xbmcgui
import xbmcplugin


HANDLE = int(sys.argv[1])
RAIPLAY_LIVE_TV = "plugin://plugin.video.raitv/?mode=live_tv"


def show_categories():
    item = xbmcgui.ListItem(label="Canali Rai")
    item.setArt({
        "icon": "DefaultTVShows.png",
        "thumb": "DefaultTVShows.png",
    })

    xbmcplugin.addDirectoryItem(
        handle=HANDLE,
        url=RAIPLAY_LIVE_TV,
        listitem=item,
        isFolder=True,
    )
    xbmcplugin.endOfDirectory(HANDLE)


def main():
    if not xbmc.getCondVisibility("System.HasAddon(plugin.video.raitv)"):
        xbmcgui.Dialog().notification(
            "Nonno Stream",
            "Installa prima l'add-on Rai Play da Kodi.",
            xbmcgui.NOTIFICATION_WARNING,
            5000,
        )
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    show_categories()


if __name__ == "__main__":
    main()
