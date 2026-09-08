# title_monitor.py — Browser Window Title Monitor
# Monitors active browser windows for adult keywords in the page title.
# Uses pywin32 to enumerate all windows and check titles.

import re
import threading
import time
import win32gui
import win32process
import psutil
from blocklist import contains_adult_keyword, get_all_domains
from config import get_setting, is_whitelisted, get_whitelist

# Browser process names to monitor
BROWSER_PROCESSES = {
    "chrome.exe", "firefox.exe", "msedge.exe", "opera.exe",
    "brave.exe", "vivaldi.exe", "iexplore.exe", "browser.exe",
    "chromium.exe", "360chrome.exe", "kometa.exe", "yandexbrowser.exe",
    "waterfox.exe", "palemoon.exe", "tor.exe", "torbrowser.exe",
    "slimjet.exe", "maxthon.exe", "torch.exe", "epic.exe",
    "dragon.exe", "comodo.exe", "avant.exe", "seamonkey.exe",
    "uc_browser.exe",
}


# Adult domain name fragments for URL detection in titles
ADULT_DOMAIN_FRAGMENTS = [
    "okteve", "vivid red", "vivid-red", "vividred", "vivid touch", "vivid tv",
    "pornhub", "xvideos", "xhamster", "xnxx", "redtube", "youporn",
    "tube8", "spankbang", "chaturbate", "onlyfans", "brazzers",
    "nhentai", "rule34", "hentai", "e621", "gelbooru", "danbooru",
    "beeg", "txxx", "bravotube", "drtuber", "anyporn", "vporn",
    "fuckbook", "adultfriendfinder", "ashley madison", "fetlife",
    "naughtyamerica", "realitykings", "bangbros", "mofos",
    "livejasmin", "myfreecams", "bongacams", "stripchat",
    "blacked", "tushy", "vixen", "deeper.com", "manyvids", "fansly",
    "youjizz", "eporner", "pornmd", "motherless", "heavy-r",
    "nudevista", "met-art", "femjoy", "babes.com",
]


class TitleMonitor:
    def __init__(self, on_blocked_callback):
        """
        Initialize the title monitor.
        :param on_blocked_callback: Called with (window_title, matched_keyword) when adult content is detected.
        """
        self.on_blocked = on_blocked_callback
        self._running = False
        self._thread = None
        self._last_blocked_title = ""
        self._block_cooldown = {}   # title -> last_block_timestamp
        self._cooldown_seconds = 3  # seconds before re-triggering same title

    def start(self):
        """Start the monitoring thread."""
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the monitoring thread."""
        self._running = False

    def _get_all_browser_windows(self) -> list[tuple[int, str, str]]:
        """
        Enumerate all visible browser windows.
        Returns list of (hwnd, title, process_name).
        """
        results = []

        def enum_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                proc_name = proc.name().lower()

                if proc_name in BROWSER_PROCESSES:
                    results.append((hwnd, title, proc_name))
            except Exception:
                pass

        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception:
            pass
        return results

    def _is_adult_title(self, title: str) -> str | None:
        """
        Check if a window title contains adult content.
        Returns matched keyword/domain fragment, or None if clean.
        """
        title_lower = title.lower()

        # Check whitelist first: if title matches any whitelisted domain, do not block
        for domain in get_whitelist():
            if domain and domain.lower() in title_lower:
                return None

        # Check for adult domain fragments using word boundary matching
        for fragment in ADULT_DOMAIN_FRAGMENTS:
            pattern = r'\b' + re.escape(fragment) + r'\b'
            if re.search(pattern, title_lower):
                return fragment

        # Check for adult keywords
        matched = contains_adult_keyword(title)
        if matched:
            return matched

        return None

    def _should_trigger(self, title: str) -> bool:
        """Check if we should fire the callback (cooldown logic with memory cleanup)."""
        now = time.time()
        # Periodic memory cleanup for cooldown entries older than 60s
        if len(self._block_cooldown) > 100:
            self._block_cooldown = {k: v for k, v in self._block_cooldown.items() if now - v < 60}

        last = self._block_cooldown.get(title, 0)
        if now - last > self._cooldown_seconds:
            self._block_cooldown[title] = now
            return True
        return False

    def _monitor_loop(self):
        """Main monitoring loop — runs every 500ms."""
        while self._running:
            try:
                if get_setting("enabled") and get_setting("monitor_titles"):
                    windows = self._get_all_browser_windows()
                    for hwnd, title, proc_name in windows:
                        matched = self._is_adult_title(title)
                        if matched and self._should_trigger(title):
                            self.on_blocked(title, matched, hwnd)
            except Exception:
                pass
            time.sleep(0.5)
