import asyncio
import sys
import signal
import platform

from datetime import datetime


async def stop_process(proc: asyncio.subprocess.Process):
    try:
        # Проверка платформы
        if platform.system() == "Windows":
            proc.terminate()
        else:
            proc.send_signal(signal.SIGINT)
    except ProcessLookupError:
        pass


async def main():

    print(f"Начало работы в {datetime.now().strftime('%H:%M')}")

    # Запуск сервера
    server = await asyncio.create_subprocess_exec(sys.executable, "server.py")
    # Запуск двух клиентов
    client1 = await asyncio.create_subprocess_exec(sys.executable, "client.py", "1")
    client2 = await asyncio.create_subprocess_exec(sys.executable, "client.py", "2")

    print("Сервер и два клиента запущены. Работаем 5 минут...")

    try:
        await asyncio.sleep(300)  # 5 минут
    except asyncio.CancelledError:
        pass

    print(f"{datetime.now().strftime('%H:%M')} - Timeout! Завершаем процессы...")

    for proc in [server, client1, client2]:
        await stop_process(proc)

    for proc in [server, client1, client2]:
        await proc.wait()

    print("Все процессы завершены.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"{datetime.now().strftime('%H:%M')} - Прервано вручную.")
