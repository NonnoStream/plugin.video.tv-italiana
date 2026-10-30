# -*- coding: utf-8 -*-
"""Nonno Stream: dirette Rai, radio e accesso ai cataloghi ufficiali."""

import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

import xbmc
import xbmcgui
import xbmcplugin


HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
RAI_TV_URL = "https://www.raiplay.it/dirette.json"
RAI_RADIO_URL = "https://www.raiplaysound.it/dirette.json"

# RadioMediaset pages publish their live audio players on these official pages.
RADIOMEDIASET = [
    ("Radio 105", "https://www.105.net/radio-onair/"),
    ("R101", "https://www.r101.it/radio-onair/"),
    ("Virgin Radio", "https://www.virginradio.it/radio-onair/"),
    ("Radio Monte Carlo", "https://www.radiomontecarlo.net/radio-onair/"),
]

RADIOMEDIASET_EXTRA = [
    ("Radio Subasio", "https://icy.unitedradio.it/Subasio.aac"),
    ("Radio Subasio +", "https://icy.unitedradio.it/SubasioPiu.aac"),
    ("Radio Subasio Disco Club", "https://icy.unitedradio.it/RadioSubasioDiscoCLUB.aac"),
    ("Radio Suby", "https://icecast.unitedradio.it/Suby.aac"),
    ("Subasio Collection", "https://icy.unitedradio.it/SubasioCollection.mp3"),
    ("Subasio Per Un'Ora D'Amore", "https://icy.unitedradio.it/SubasioPerUnOraDAmore.mp3"),
    ("Radio Festival", "https://icy.unitedradio.it/RadioFestival.mp3"),
    ("Radio Norba", "https://ad2.xdevel.com/radionorba"),
    ("Radio Norba Italiana", "https://icy.unitedradio.it/RN01.aac"),
    ("Radio Norba Amore", "https://icy.unitedradio.it/RN02.aac"),
    ("Radio Norba Battiti", "https://icy.unitedradio.it/RN03.aac"),
    ("Radio Norba Joy", "https://icy.unitedradio.it/RN04.aac"),
]

OFFICIAL_ADDONS = {
    "rai": ("plugin.video.raitv", "Rai Play"),
    "mediaset": ("plugin.video.videomediaset", "Mediaset Infinity"),
}


class NoRedirect(HTTPRedirectHandler):
    """Keep Rai's temporary redirect so Kodi can play its signed stream URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def notify(message, warning=False):
    level = xbmcgui.NOTIFICATION_WARNING if warning else xbmcgui.NOTIFICATION_INFO
    xbmcgui.Dialog().notification("Nonno Stream", message, level, 5000)


def request(url, accept="*/*", opener=None, rai=False):
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if rai:
        headers["Referer"] = "https://www.raiplay.it/"
        headers["Origin"] = "https://www.raiplay.it"
    req = Request(url, headers=headers)
    return (opener or build_opener()).open(req, timeout=20)


def fetch_json(url):
    with request(url, "application/json, text/javascript, */*") as response:
        return json.loads(response.read().decode("utf-8"))


def plugin_url(params):
    return BASE_URL + "?" + urlencode(params)


def add_folder(label, params, icon="DefaultFolder.png"):
    item = xbmcgui.ListItem(label=label)
    item.setArt({"icon": icon, "thumb": icon})
    xbmcplugin.addDirectoryItem(HANDLE, plugin_url(params), item, isFolder=True)


def add_playable(label, params, icon="DefaultTVShows.png"):
    item = xbmcgui.ListItem(label=label)
    item.setArt({"icon": icon, "thumb": icon})
    item.setProperty("IsPlayable", "true")
    xbmcplugin.addDirectoryItem(HANDLE, plugin_url(params), item, isFolder=False)


def add_addon_entry(label, addon_id, addon_name):
    if xbmc.getCondVisibility("System.HasAddon({})".format(addon_id)):
        add_folder(label, {"mode": "open_addon", "addon": addon_id})
    else:
        add_folder("{} (installa da Kodi)".format(label), {
            "mode": "install_addon", "addon": addon_id, "name": addon_name
        })


def show_root():
    add_folder("Canali TV Rai", {"mode": "rai_tv"}, "DefaultTVShows.png")
    add_folder("Radio Rai", {"mode": "rai_radio"}, "DefaultMusic.png")
    add_folder("RadioMediaset", {"mode": "mediaset_radio"}, "DefaultMusic.png")
    add_addon_entry("Film RaiPlay", OFFICIAL_ADDONS["rai"][0], OFFICIAL_ADDONS["rai"][1])
    add_addon_entry("Film e programmi Mediaset", OFFICIAL_ADDONS["mediaset"][0], OFFICIAL_ADDONS["mediaset"][1])
    xbmcplugin.endOfDirectory(HANDLE)


def show_rai_tv():
    try:
        channels = fetch_json(RAI_TV_URL).get("contents", [])
        count = 0
        for channel in channels:
            video = channel.get("video") or {}
            stream_page = video.get("content_url")
            name = channel.get("channel") or channel.get("name")
            if channel.get("is_live") and name and stream_page:
                add_playable(name, {"mode": "play_rai", "url": stream_page, "title": name}, "DefaultTVShows.png")
                count += 1
        if not count:
            raise ValueError("Nessun canale live nel catalogo Rai")
        xbmcplugin.endOfDirectory(HANDLE)
    except Exception as exc:
        xbmc.log("Nonno Stream Rai TV: {}".format(exc), xbmc.LOGERROR)
        notify("Non riesco a caricare i canali Rai. Riprova più tardi.", True)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)


def show_rai_radio():
    try:
        stations = fetch_json(RAI_RADIO_URL).get("contents", [])
        count = 0
        for station in stations:
            audio = station.get("audio") or {}
            stream_page = audio.get("url")
            name = station.get("title") or audio.get("title")
            if name and stream_page:
                add_playable(name, {"mode": "play_rai", "url": stream_page, "title": name}, "DefaultMusic.png")
                count += 1
        if not count:
            raise ValueError("Nessuna radio disponibile nel catalogo Rai")
        xbmcplugin.endOfDirectory(HANDLE)
    except Exception as exc:
        xbmc.log("Nonno Stream Rai Radio: {}".format(exc), xbmc.LOGERROR)
        notify("Non riesco a caricare le radio Rai. Riprova più tardi.", True)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)


def show_mediaset_radio():
    try:
        count = 0
        for name, page in RADIOMEDIASET:
            try:
                html = request(page, "text/html,application/xhtml+xml").read().decode("utf-8", "replace")
                match = re.search(r"<audio\b[^>]*?\bsrc=[\"']([^\"']+)", html, re.I)
                if match:
                    stream_url = match.group(1).replace("&amp;", "&")
                    add_playable(name, {"mode": "play", "url": stream_url, "title": name}, "DefaultMusic.png")
                    count += 1
            except Exception as exc:
                xbmc.log("Nonno Stream radio {}: {}".format(name, exc), xbmc.LOGWARNING)
        for name, stream_url in RADIOMEDIASET_EXTRA:
            add_playable(name, {"mode": "play", "url": stream_url, "title": name}, "DefaultMusic.png")
            count += 1
        if not count:
            raise ValueError("Nessuno stream RadioMediaset trovato")
        xbmcplugin.endOfDirectory(HANDLE)
    except Exception as exc:
        xbmc.log("Nonno Stream RadioMediaset: {}".format(exc), xbmc.LOGERROR)
        notify("Non riesco a caricare le radio Mediaset. Riprova più tardi.", True)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)


def play_rai(stream_page, title):
    try:
        opener = build_opener(NoRedirect())
        try:
            with request(stream_page, opener=opener, rai=True) as response:
                stream_url = response.geturl()
        except HTTPError as exc:
            if exc.code not in (301, 302, 303, 307, 308):
                raise
            stream_url = exc.headers.get("Location")
        if not stream_url:
            raise ValueError("Rai non ha restituito l'indirizzo dello stream")
        item = xbmcgui.ListItem(path=stream_url)
        item.setInfo("video", {"title": title})
        xbmcplugin.setResolvedUrl(HANDLE, True, item)
    except Exception as exc:
        xbmc.log("Nonno Stream riproduzione Rai {}: {}".format(title, exc), xbmc.LOGERROR)
        notify("La diretta non è disponibile in questo momento.", True)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def install_official_addon(addon_id, name):
    if xbmc.getCondVisibility("System.HasAddon({})".format(addon_id)):
        xbmc.executebuiltin("RunAddon({})".format(addon_id))
        xbmcplugin.endOfDirectory(HANDLE, succeeded=True)
        return
    xbmcgui.Dialog().ok(
        "Installa {}".format(name),
        "Kodi aprirà il catalogo ufficiale per installare {}. Dopo l'installazione, riapri questa voce.".format(name),
    )
    xbmc.executebuiltin("InstallAddon({})".format(addon_id))
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True)


def route():
    query = parse_qs(sys.argv[2][1:]) if len(sys.argv) > 2 and sys.argv[2] else {}
    mode = query.get("mode", [""])[0]
    if mode == "rai_tv":
        show_rai_tv()
    elif mode == "rai_radio":
        show_rai_radio()
    elif mode == "mediaset_radio":
        show_mediaset_radio()
    elif mode == "play_rai":
        play_rai(query.get("url", [""])[0], query.get("title", ["Nonno Stream"])[0])
    elif mode == "play":
        item = xbmcgui.ListItem(path=query.get("url", [""])[0])
        item.setInfo("music", {"title": query.get("title", ["Radio"])[0]})
        xbmcplugin.setResolvedUrl(HANDLE, True, item)
    elif mode == "install_addon":
        install_official_addon(query.get("addon", [""])[0], query.get("name", ["add-on"])[0])
    elif mode == "open_addon":
        xbmc.executebuiltin("RunAddon({})".format(query.get("addon", [""])[0]))
        xbmcplugin.endOfDirectory(HANDLE, succeeded=True)
    else:
        show_root()


if __name__ == "__main__":
    route()
