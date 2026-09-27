"""Windows tray icon on its own message window, so it survives the Tk window."""

from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

# These calls return pointers. Without a restype, ctypes keeps 32 bits and
# RegisterClassW faults on a 64-bit address.
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_CONTEXTMENU = 0x007B
WM_NULL = 0x0000
WM_TRAY = 0x0400 + 20
NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2
NIF_MESSAGE = 1
NIF_ICON = 2
NIF_TIP = 4
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
MF_STRING = 0
MF_OWNERDRAW = 0x0100
MF_CHECKED = 0x0008
MF_POPUP = 0x0010
MF_SEPARATOR = 0x0800
WM_MEASUREITEM = 0x002C
WM_DRAWITEM = 0x002B
ODT_MENU = 1
ODS_SELECTED = 0x0001
ODS_GRAYED = 0x0002
ODS_DISABLED = 0x0004
ODS_CHECKED = 0x0008
TRANSPARENT = 1
DT_LEFT = 0
DT_VCENTER = 4
DT_SINGLELINE = 0x20
# COLORREF is 0x00BBGGRR. These match the dark window.
MENU_BG = 0x0018140E
MENU_HOT = 0x0056463A
MENU_INK = 0x00F8F7F4
MENU_MUTED = 0x00BBAF9A
MENU_LINE = 0x00524531
TPM_RIGHTALIGN = 0x0008
TPM_BOTTOMALIGN = 0x0020
TPM_RIGHTBUTTON = 0x0002
WS_POPUP = 0x80000000

user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, ctypes.c_size_t]
user32.AppendMenuW.restype = wintypes.BOOL
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.DestroyMenu.argtypes = [wintypes.HMENU]
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.LoadImageW.restype = wintypes.HANDLE
user32.RegisterClassW.argtypes = [ctypes.c_void_p]
user32.RegisterClassW.restype = wintypes.ATOM
user32.GetMessageW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = [ctypes.c_void_p]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.c_void_p]
user32.DispatchMessageW.restype = LRESULT
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
user32.PostQuitMessage.argtypes = [ctypes.c_int]
shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.c_void_p]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.c_void_p]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, ctypes.c_void_p,
]
user32.TrackPopupMenu.restype = wintypes.BOOL


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HANDLE),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HANDLE),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MEASUREITEMSTRUCT(ctypes.Structure):
    _fields_ = [
        ("CtlType", wintypes.UINT),
        ("CtlID", wintypes.UINT),
        ("itemID", wintypes.UINT),
        ("itemWidth", wintypes.UINT),
        ("itemHeight", wintypes.UINT),
        ("itemData", ctypes.c_size_t),
    ]


class DRAWITEMSTRUCT(ctypes.Structure):
    _fields_ = [
        ("CtlType", wintypes.UINT),
        ("CtlID", wintypes.UINT),
        ("itemID", wintypes.UINT),
        ("itemAction", wintypes.UINT),
        ("itemState", wintypes.UINT),
        ("hwndItem", wintypes.HWND),
        ("hDC", wintypes.HDC),
        ("rcItem", RECT),
        ("itemData", ctypes.c_size_t),
    ]


class MENUINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", wintypes.DWORD),
        ("dwStyle", wintypes.DWORD),
        ("cyMax", wintypes.UINT),
        ("hbrBack", wintypes.HBRUSH),
        ("dwContextHelpID", wintypes.DWORD),
        ("dwMenuData", ctypes.c_size_t),
    ]


user32.SetMenuInfo.argtypes = [wintypes.HMENU, ctypes.POINTER(MENUINFO)]
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(RECT), wintypes.HBRUSH]
user32.DrawTextW.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(RECT), wintypes.UINT]
gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
gdi32.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.COLORREF]
gdi32.CreatePen.restype = wintypes.HPEN
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
gdi32.GetTextExtentPoint32W.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(SIZE)]
gdi32.MoveToEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
gdi32.LineTo.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]


class WinTray:
    def __init__(self, icon_path: str, on_show, on_command, items=None):
        self.icon_path = icon_path
        self.on_show = on_show
        self.on_command = on_command
        self.items = items or _default_items
        self._ids: dict[int, str] = {}
        self._owner: dict[int, dict] = {}
        self._next_id = 1
        self._menu_brush = None
        self.hwnd = None
        self.hicon = None
        self.ok = False
        self.error = ""
        self._proc = WNDPROC(self._wnd)
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, name="grok-tray", daemon=True)

    def start(self) -> bool:
        self._thread.start()
        self._ready.wait(timeout=3)
        return self.ok

    def stop(self) -> None:
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)

    def set_tip(self, text: str) -> None:
        if not self.hwnd:
            return
        data = self._data(text[:127])
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(data))

    def _data(self, tip: str) -> NOTIFYICONDATAW:
        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        data.hWnd = self.hwnd
        data.uID = 1
        data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        data.uCallbackMessage = WM_TRAY
        data.hIcon = self.hicon
        data.szTip = tip or "Grok Assistant"
        return data

    def _run(self) -> None:
        class_name = "GrokAssistantTray"
        window_class = WNDCLASSW()
        window_class.lpfnWndProc = self._proc
        window_class.hInstance = kernel32.GetModuleHandleW(None)
        window_class.lpszClassName = class_name
        atom = user32.RegisterClassW(ctypes.byref(window_class))
        if not atom and kernel32.GetLastError() not in (0, 1410):
            self.error = f"RegisterClass {kernel32.GetLastError()}"
            self._ready.set()
            return
        # A real hidden window. A message-only window drops the right-click.
        self.hwnd = user32.CreateWindowExW(
            0, class_name, "Grok Assistant", WS_POPUP,
            0, 0, 0, 0, None, None, window_class.hInstance, None,
        )
        if not self.hwnd:
            self.error = f"CreateWindow {kernel32.GetLastError()}"
            self._ready.set()
            return
        self.hicon = user32.LoadImageW(None, self.icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
        if not self.hicon:
            self.error = f"LoadImage {kernel32.GetLastError()}"
            self._ready.set()
            return
        added = shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._data("Grok Assistant")))
        if not added:
            self.error = f"Shell_NotifyIcon {kernel32.GetLastError()}"
            self._ready.set()
            return
        self.ok = True
        self._ready.set()
        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))

    def _wnd(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY:
            event = int(lparam) & 0xFFFF
            if event in (WM_RBUTTONUP, WM_CONTEXTMENU):
                self._menu(hwnd)
            elif event in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                self.on_show()
            return 0
        if msg == WM_MEASUREITEM:
            measure = ctypes.cast(lparam, ctypes.POINTER(MEASUREITEMSTRUCT)).contents
            info = self._owner.get(int(measure.itemData))
            if info is None:
                return 0
            measure.itemHeight = 10 if info.get("sep") else 30
            measure.itemWidth = info["width"]
            return 1
        if msg == WM_DRAWITEM:
            draw = ctypes.cast(lparam, ctypes.POINTER(DRAWITEMSTRUCT)).contents
            if draw.CtlType == ODT_MENU:
                self._paint_item(draw)
                return 1
            return 0
        if msg == WM_COMMAND:
            key = self._ids.get(int(wparam) & 0xFFFF)
            if key and self.on_command:
                self.on_command(key)
            return 0
        if msg == WM_CLOSE:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._data("")))
            user32.DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _menu(self, hwnd) -> None:
        self._ids = {}
        self._owner = {}
        self._next_id = 1
        if self._menu_brush:
            gdi32.DeleteObject(self._menu_brush)
        self._menu_brush = gdi32.CreateSolidBrush(MENU_BG)
        menu, owned = self._build(self.items())
        point = POINT()
        user32.GetCursorPos(ctypes.byref(point))
        user32.SetForegroundWindow(hwnd)
        user32.TrackPopupMenu(
            menu,
            TPM_RIGHTALIGN | TPM_BOTTOMALIGN | TPM_RIGHTBUTTON,
            point.x, point.y, 0, hwnd, None,
        )
        user32.PostMessageW(hwnd, WM_NULL, 0, 0)
        user32.PostMessageW(hwnd, WM_NULL, 0, 0)
        for handle in owned:
            user32.DestroyMenu(handle)

    def _text_width(self, text: str) -> int:
        dc = user32.GetDC(self.hwnd)
        size = SIZE()
        gdi32.GetTextExtentPoint32W(dc, text, len(text), ctypes.byref(size))
        user32.ReleaseDC(self.hwnd, dc)
        return int(size.cx)

    def _remember(self, text: str, *, popup: bool = False, checked: bool = False, disabled: bool = False, sep: bool = False) -> int:
        number = self._next_id
        self._next_id += 1
        width = 48 if sep else self._text_width(text) + 64
        self._owner[number] = {
            "text": text,
            "popup": popup,
            "checked": checked,
            "disabled": disabled,
            "sep": sep,
            "width": width,
        }
        return number

    def _paint_item(self, draw: DRAWITEMSTRUCT) -> None:
        info = self._owner.get(int(draw.itemData))
        if info is None:
            return
        rect = draw.rcItem
        hot = bool(draw.itemState & ODS_SELECTED) and not info.get("sep")
        brush = gdi32.CreateSolidBrush(MENU_HOT if hot else MENU_BG)
        user32.FillRect(draw.hDC, ctypes.byref(rect), brush)
        gdi32.DeleteObject(brush)
        if info.get("sep"):
            pen = gdi32.CreatePen(0, 1, MENU_LINE)
            old = gdi32.SelectObject(draw.hDC, pen)
            mid = (rect.top + rect.bottom) // 2
            gdi32.MoveToEx(draw.hDC, rect.left + 12, mid, None)
            gdi32.LineTo(draw.hDC, rect.right - 12, mid)
            gdi32.SelectObject(draw.hDC, old)
            gdi32.DeleteObject(pen)
            return
        disabled = bool(draw.itemState & (ODS_GRAYED | ODS_DISABLED)) or info.get("disabled")
        color = MENU_MUTED if disabled else MENU_INK
        gdi32.SetBkMode(draw.hDC, TRANSPARENT)
        gdi32.SetTextColor(draw.hDC, color)
        checked = bool(draw.itemState & ODS_CHECKED) or info.get("checked")
        if checked:
            self._mark(draw.hDC, rect, MENU_INK)
        text_rect = RECT(rect.left + 28, rect.top, rect.right - 28, rect.bottom)
        user32.DrawTextW(
            draw.hDC, info["text"], -1, ctypes.byref(text_rect),
            DT_LEFT | DT_VCENTER | DT_SINGLELINE,
        )
        if info.get("popup"):
            self._arrow(draw.hDC, rect)

    def _arrow(self, dc, rect: RECT) -> None:
        pen = gdi32.CreatePen(0, 2, 0x00FFFFFF)
        old = gdi32.SelectObject(dc, pen)
        mid = (rect.top + rect.bottom) // 2
        x = rect.right - 18
        gdi32.MoveToEx(dc, x, mid - 5, None)
        gdi32.LineTo(dc, x + 6, mid)
        gdi32.LineTo(dc, x, mid + 5)
        gdi32.SelectObject(dc, old)
        gdi32.DeleteObject(pen)

    def _mark(self, dc, rect: RECT, color: int) -> None:
        pen = gdi32.CreatePen(0, 2, color)
        old = gdi32.SelectObject(dc, pen)
        x = rect.left + 10
        mid = (rect.top + rect.bottom) // 2
        gdi32.MoveToEx(dc, x, mid, None)
        gdi32.LineTo(dc, x + 4, mid + 4)
        gdi32.LineTo(dc, x + 11, mid - 5)
        gdi32.SelectObject(dc, old)
        gdi32.DeleteObject(pen)

    def _dark_menu(self, menu) -> None:
        info = MENUINFO()
        info.cbSize = ctypes.sizeof(MENUINFO)
        info.fMask = 0x00000002 | 0x80000000
        info.hbrBack = self._menu_brush
        user32.SetMenuInfo(menu, ctypes.byref(info))

    def _build(self, items: list) -> tuple:
        menu = user32.CreatePopupMenu()
        self._dark_menu(menu)
        owned = [menu]
        for item in items:
            kind = item[0]
            if kind == "sep":
                number = self._remember("", sep=True)
                user32.AppendMenuW(menu, MF_OWNERDRAW, number, number)
                continue
            if kind == "sub":
                child, nested = self._build(item[2])
                owned.extend(nested)
                number = self._remember(item[1], popup=True)
                user32.AppendMenuW(
                    menu, MF_OWNERDRAW | MF_POPUP,
                    ctypes.cast(child, ctypes.c_void_p).value or 0, number,
                )
                continue
            number = self._next_id
            self._next_id += 1
            self._ids[number] = item[2]
            self._remember_id(number, item[1], checked=bool(item[3]), disabled=item[2] == "noop")
            flags = MF_OWNERDRAW
            if item[3]:
                flags |= MF_CHECKED
            if item[2] == "noop":
                flags |= 0x0001
            user32.AppendMenuW(menu, flags, number, number)
        return menu, owned

    def _remember_id(self, number: int, text: str, *, checked: bool, disabled: bool) -> None:
        self._owner[number] = {
            "text": text,
            "popup": False,
            "checked": checked,
            "disabled": disabled,
            "sep": False,
            "width": self._text_width(text) + 64,
        }


def _default_items() -> list:
    return [
        ("cmd", "Mostrar", "show", False),
        ("cmd", "Pausar o seguir", "pause", False),
        ("sep",),
        ("cmd", "Salir", "quit", False),
    ]


# Windows draws the cascade glyph itself, in black, after Tk has painted the
# dark item. Cover that glyph with a white chevron. The tray menu already
# draws its own white chevron; this is for the window menus.
_arrow_procs: list = []


def install_white_submenu_arrows() -> None:
    if getattr(install_white_submenu_arrows, "on", False):
        return
    install_white_submenu_arrows.on = True
    threading.Thread(target=_watch_menu_arrows, name="menu-arrows", daemon=True).start()


def _arrow_apis():
    user = ctypes.WinDLL("user32", use_last_error=True)
    gdi = ctypes.WinDLL("gdi32", use_last_error=True)
    kern = ctypes.WinDLL("kernel32", use_last_error=True)

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long), ("top", ctypes.c_long),
            ("right", ctypes.c_long), ("bottom", ctypes.c_long),
        ]

    class MENUITEMINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("fMask", wintypes.UINT),
            ("fType", wintypes.UINT),
            ("fState", wintypes.UINT),
            ("wID", wintypes.UINT),
            ("hSubMenu", wintypes.HMENU),
            ("hbmpChecked", wintypes.HBITMAP),
            ("hbmpUnchecked", wintypes.HBITMAP),
            ("dwItemData", ctypes.c_void_p),
            ("dwTypeData", wintypes.LPWSTR),
            ("cch", wintypes.UINT),
            ("hbmpItem", wintypes.HBITMAP),
        ]

    user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.IsWindow.argtypes = [wintypes.HWND]
    user.IsWindow.restype = wintypes.BOOL
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.IsWindowVisible.restype = wintypes.BOOL
    user.GetMenuItemCount.argtypes = [wintypes.HMENU]
    user.GetMenuItemCount.restype = ctypes.c_int
    user.GetMenuItemInfoW.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.BOOL, ctypes.POINTER(MENUITEMINFOW)]
    user.GetMenuItemInfoW.restype = wintypes.BOOL
    user.GetMenuItemRect.argtypes = [wintypes.HWND, wintypes.HMENU, wintypes.UINT, ctypes.POINTER(RECT)]
    user.GetMenuItemRect.restype = wintypes.BOOL
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
    user.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user.SendMessageW.restype = ctypes.c_void_p
    user.GetWindowDC.argtypes = [wintypes.HWND]
    user.GetWindowDC.restype = wintypes.HDC
    user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(RECT), wintypes.HBRUSH]
    user.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
    gdi.CreateSolidBrush.argtypes = [wintypes.COLORREF]
    gdi.CreateSolidBrush.restype = wintypes.HBRUSH
    gdi.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.COLORREF]
    gdi.CreatePen.restype = wintypes.HPEN
    gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi.SelectObject.restype = wintypes.HGDIOBJ
    gdi.MoveToEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
    gdi.LineTo.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi.GetPixel.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi.GetPixel.restype = wintypes.COLORREF
    kern.GetCurrentProcessId.restype = wintypes.DWORD
    return user, gdi, kern, RECT, MENUITEMINFOW


def _watch_menu_arrows() -> None:
    user, gdi, kern, RECT, MENUITEMINFOW = _arrow_apis()
    found: list = []

    def paint(hwnd) -> None:
        if not user.IsWindow(hwnd):
            return
        hmenu = user.SendMessageW(hwnd, 0x01E1, 0, 0)
        if not hmenu:
            return
        count = user.GetMenuItemCount(hmenu)
        if count <= 0:
            return
        window = RECT()
        user.GetWindowRect(hwnd, ctypes.byref(window))
        dc = user.GetWindowDC(hwnd)
        if not dc:
            return
        try:
            for index in range(count):
                info = MENUITEMINFOW()
                info.cbSize = ctypes.sizeof(MENUITEMINFOW)
                info.fMask = 0x00000004
                if not user.GetMenuItemInfoW(hmenu, index, True, ctypes.byref(info)) or not info.hSubMenu:
                    continue
                item = RECT()
                if not user.GetMenuItemRect(None, hmenu, index, ctypes.byref(item)):
                    continue
                left = item.left - window.left
                top = item.top - window.top
                right = item.right - window.left
                bottom = item.bottom - window.top
                mid = (top + bottom) // 2
                sample = gdi.GetPixel(dc, left + 10, mid)
                if int(sample) == 0xFFFFFFFF:
                    sample = MENU_BG
                brush = gdi.CreateSolidBrush(sample)
                user.FillRect(dc, ctypes.byref(RECT(right - 28, top + 2, right - 4, bottom - 2)), brush)
                gdi.DeleteObject(brush)
                pen = gdi.CreatePen(0, 2, 0x00FFFFFF)
                old_pen = gdi.SelectObject(dc, pen)
                x = right - 18
                gdi.MoveToEx(dc, x, mid - 5, None)
                gdi.LineTo(dc, x + 6, mid)
                gdi.LineTo(dc, x, mid + 5)
                gdi.SelectObject(dc, old_pen)
                gdi.DeleteObject(pen)
        finally:
            user.ReleaseDC(hwnd, dc)

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def enum(hwnd, _lparam):
        cls = ctypes.create_unicode_buffer(32)
        user.GetClassNameW(hwnd, cls, 32)
        if cls.value != "#32768" or not user.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value != kern.GetCurrentProcessId():
            return True
        rect = RECT()
        user.GetWindowRect(hwnd, ctypes.byref(rect))
        if rect.right - rect.left > 40 and rect.bottom - rect.top > 20:
            found.append(hwnd)
        return True

    _arrow_procs.append(enum)

    while True:
        try:
            found.clear()
            user.EnumWindows(ctypes.cast(enum, ctypes.c_void_p), 0)
            for hwnd in list(found):
                try:
                    paint(hwnd)
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(0.02 if found else 0.08)
