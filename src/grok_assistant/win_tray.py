"""Windows tray icon on its own message window, so it survives the Tk window."""

from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
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
TPM_RIGHTALIGN = 0x0008
TPM_BOTTOMALIGN = 0x0020
HWND_MESSAGE = wintypes.HWND(-3)
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


class WinTray:
    def __init__(self, icon_path: str, on_show, on_pause, on_quit):
        self.icon_path = icon_path
        self.on_show = on_show
        self.on_pause = on_pause
        self.on_quit = on_quit
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
        self.hwnd = user32.CreateWindowExW(0, class_name, "Grok Assistant", 0, 0, 0, 0, 0, HWND_MESSAGE, None, window_class.hInstance, None)
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
            if lparam in (WM_LBUTTONUP, 0x0203):
                self.on_show()
            elif lparam == WM_RBUTTONUP:
                self._menu(hwnd)
            return 0
        if msg == WM_COMMAND:
            choice = wparam & 0xFFFF
            if choice == 1:
                self.on_show()
            elif choice == 2:
                self.on_pause()
            elif choice == 3:
                self.on_quit()
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
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, MF_STRING, 1, "Mostrar")
        user32.AppendMenuW(menu, MF_STRING, 2, "Pausar o seguir")
        user32.AppendMenuW(menu, MF_STRING, 3, "Salir")
        point = POINT()
        user32.GetCursorPos(ctypes.byref(point))
        user32.SetForegroundWindow(hwnd)
        user32.TrackPopupMenu(menu, TPM_RIGHTALIGN | TPM_BOTTOMALIGN, point.x, point.y, 0, hwnd, None)
        user32.PostMessageW(hwnd, WM_NULL, 0, 0)
        user32.DestroyMenu(menu)
