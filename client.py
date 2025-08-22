import asyncio
import random
import datetime
import logging
import sys


# Кастомный форматер для логов клиента
class ClientLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        date = getattr(record, "date", "")
        req_time = getattr(record, "req_time", "")
        req_text = getattr(record, "req_text", "")
        resp_time = getattr(record, "resp_time", "")
        resp_text = getattr(record, "resp_text", "")
        return f"{date};{req_time};{req_text};{resp_time};{resp_text}"


def setup_logger(log_file: str) -> logging.Logger:
    logger = logging.getLogger(log_file)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(ClientLogFormatter())
    logger.addHandler(handler)
    return logger


class Client:
    def __init__(self, client_no: int, logger: logging.Logger):
        self.client_no = client_no
        self.req_counter = 0
        self.logger = logger

    async def run(self):
        reader, writer = await asyncio.open_connection("127.0.0.1", 8888)
        asyncio.create_task(self.sender(writer))
        await self.receiver(reader)

    async def sender(self, writer: asyncio.StreamWriter):
        while True:
            # Случайный интервал от 300 до 3000 мс
            await asyncio.sleep(random.uniform(0.3, 3.0))
            req_id = self.req_counter
            self.req_counter += 1
            msg = f"[{req_id}] PING"
            send_time = datetime.datetime.now()

            writer.write((msg + "\n").encode("ascii"))
            await writer.drain()

            # Таймаут ожидания ответа
            try:
                resp_text, resp_time = await asyncio.wait_for(self.wait_response(), timeout=2.0)
                self.logger.info("", extra={
                    "date": send_time.date(),
                    "req_time": send_time.strftime("%H:%M:%S.%f")[:-3],
                    "req_text": msg,
                    "resp_time": resp_time.strftime("%H:%M:%S.%f")[:-3],
                    "resp_text": resp_text
                })
            except asyncio.TimeoutError:
                self.logger.info("", extra={
                    "date": send_time.date(),
                    "req_time": send_time.strftime("%H:%M:%S.%f")[:-3],
                    "req_text": msg,
                    "resp_time": "(таймаут)",
                    "resp_text": "(таймаут)"
                })

    async def wait_response(self):
        # Ответы принимаются через receiver, а тут только Future-заглушка
        future = asyncio.get_event_loop().create_future()
        self._current_future = future
        return await future

    async def receiver(self, reader: asyncio.StreamReader):
        while not reader.at_eof():
            line = await reader.readline()
            if not line:
                break
            resp_time = datetime.datetime.now()
            resp_text = line.decode("ascii").strip()

            if "keepalive" in resp_text:
                # Лог keepalive с пустыми полями запроса
                self.logger.info("", extra={
                    "date": resp_time.date(),
                    "req_time": "",
                    "req_text": "",
                    "resp_time": resp_time.strftime("%H:%M:%S.%f")[:-3],
                    "resp_text": resp_text
                })
            else:
                # Это PONG на последний запрос
                if hasattr(self, "_current_future") and not self._current_future.done():
                    self._current_future.set_result((resp_text, resp_time))


async def main():
    client_no = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    logger = setup_logger(f"client{client_no}.log")
    client = Client(client_no, logger)
    await client.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
