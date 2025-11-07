# module/websocket.py
import asyncio
import threading
from websockets.asyncio.server import serve

class WebSocket():
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._thread = None
        self._loop = None
        self._server = None
        self._running = False

    def start(self):
        """在背景執行緒啟動 asyncio websocket server，避免阻塞主線程 (GUI)."""
        if self._running:
            print("WebSocket 已在執行中")
            return

        self._thread = threading.Thread(target=self._run_loop_in_thread, daemon=True)
        self._thread.start()
        self._running = True
        # print(f"websocket 開始 (background): ws://{self.host}:{self.port}")

    def stop(self):
        """嘗試停掉 server（非強制）。"""
        if not self._running:
            return
        # 安全關閉：叫 loop 停止
        try:
            if self._loop:
                # schedule shutdown coroutine
                asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)
        except Exception as e:
            print(f"[WebSocket] stop error: {e}")
        self._running = False

    def _run_loop_in_thread(self):
        """在新的執行緒內建立 asyncio event loop 並啟動 server。"""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._main())
            # loop will run forever until _main ends
        except Exception as e:
            print(f"[WebSocket] background loop error: {e}")

    async def _main(self):
        """建立 websocket server 並永遠提供服務 (直到被關閉)。"""
        async with serve(self._echo, self.host, self.port) as server:
            self._server = server
            # 印出簡單訊息
            print(f"[WebSocket] serving on ws://{self.host}:{self.port}")
            await server.wait_closed()

    async def _shutdown(self):
        """關閉 server 與 event loop（非同步在 background loop 呼叫）。"""
        try:
            if self._server:
                self._server.close()
                await self._server.wait_closed()
            # 停掉 loop
            self._loop.stop()
        except Exception as e:
            print(f"[WebSocket] shutdown error: {e}")

    async def _echo(self, websocket):
        """簡單 echo handler (websocket, path)。"""
        try:
            async for message in websocket:
                print(f"[WebSocket] Message:{message}")
                await websocket.send(message)
        except Exception as e:
            # 連線可能中斷
            print(f"[WebSocket] connection handler error: {e}")
