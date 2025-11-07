# module/websocket.py
import asyncio
import threading
from PySide6.QtCore import QObject, Signal
from websockets import serve

class WebSocket(QObject):
    is_start = Signal(bool)

    def __init__(self, host: str, port: int,recv:list=[]):
        super().__init__()
        self.host = host
        self.port = port
        self._thread = None
        self._loop = None
        self._server = None
        self.is_running = False
        self.recv = recv

    def start(self):
        """在背景執行緒啟動 websocket server"""
        if self.is_running:
            print("[WebSocket] 已在執行中")
            return

        self._thread = threading.Thread(target=self._run_loop_in_thread, daemon=True)
        self._thread.start()
        self.is_running = True

    def stop(self):
        """安全關閉 server 與 event loop"""
        if not self.is_running:
            return

        try:
            if self._loop:
                future = asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)
                future.result(timeout=5)
        except Exception as e:
            print(f"[WebSocket] stop error: {e}")
        finally:
            self.is_running = False
            self._thread = None
            print("[WebSocket] 已關閉")
            self.is_start.emit(False)

    def wait_stop(self):
        """等待背景 thread 結束（避免 Task destroyed 錯誤）"""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run_loop_in_thread(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._main())
        except Exception as e:
            print(f"[WebSocket] background loop error: {e}")
        finally:
            try:
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            except Exception:
                print(f"[WebSocket] asyncgen shutdown error: {e}")
            self._loop.close()
            # print("[WebSocket] event loop closed")

    async def _main(self):
        try:
            async with serve(self._echo, self.host, self.port) as server:
                self._server = server
                print(f"[WebSocket] serving on ws://{self.host}:{self.port}")
                self.is_start.emit(True)
                await server.wait_closed()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[WebSocket] _main error: {e}")

    async def _shutdown(self):
        """安全地關閉 server 與 loop"""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        tasks = [t for t in asyncio.all_tasks(self._loop) if t is not asyncio.current_task(self._loop)]
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._loop.stop()
    async def _echo(self, websocket):
        """簡單 echo handler"""
        try:
            async for message in websocket:
                print(f"[WebSocket] IP:{websocket.remote_address} Message: {message}")
                # print(f"[WebSocket] IP:{websocket.local_address} Message: {message}")
                await websocket.send("hi")
        except Exception as e:
            print(f"[WebSocket] connection handler error: {e}")

    def setting(self,config):
        if self.is_running:
            self.stop()
            self.wait_stop()
        self.host = config['host']
        self.port = config['port']
        self.recv = config['recivers']