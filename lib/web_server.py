"""
Web Server — KiCanvas 本地預覽伺服器

提供：
- 靜態檔案服務 (output/ 資料夾)
- KiCanvas 嵌入式 PCB 2D/3D 瀏覽器
- 自動在瀏覽器開啟預覽頁面
"""

import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path


DEFAULT_PORT = 8000
OUTPUT_DIR = Path("output")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """安靜版 HTTP handler（減少 console 噪音）"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(OUTPUT_DIR), **kwargs)

    def log_message(self, format, *args):
        # 只記錄錯誤
        if args and isinstance(args[0], str) and args[0].startswith("4"):
            super().log_message(format, *args)


def start_preview_server(port: int = DEFAULT_PORT, open_browser: bool = True) -> None:
    """啟動本地預覽伺服器

    Args:
        port: 監聽埠號
        open_browser: 是否自動開啟瀏覽器
    """
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True)

    # 確認 index.html 存在
    index = OUTPUT_DIR / "index.html"
    if not index.exists():
        print(f"⚠️  找不到 {index}，請先執行 Orchestrator 產出檔案")
        return

    with socketserver.TCPServer(("", port), QuietHandler) as httpd:
        url = f"http://localhost:{port}"
        print(f"🌐 預覽伺服器已啟動：{url}")

        if open_browser:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 伺服器已停止")


def start_preview_server_background(port: int = DEFAULT_PORT) -> threading.Thread:
    """在背景執行緒啟動預覽伺服器（非阻塞）"""
    thread = threading.Thread(
        target=start_preview_server,
        args=(port, True),
        daemon=True,
    )
    thread.start()
    return thread


if __name__ == "__main__":
    start_preview_server()
