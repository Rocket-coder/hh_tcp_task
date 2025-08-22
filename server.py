import asyncio
import random
import datetime
import logging


# Кастомный форматер для логов сервера
class ServerLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        date = getattr(record, "date", "")
        req_time = getattr(record, "req_time", "")
        req_text = getattr(record, "req_text", "")
        resp_time = getattr(record, "resp_time", "")
        resp_text = getattr(record, "resp_text", "")
        return f"{date};{req_time};{req_text};{resp_time};{resp_text}"


def setup_logger(log_file: str) -> logging.Logger:
    logger = logging.getLogger("server")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(ServerLogFormatter())
    logger.addHandler(handler)
    return logger


class Server:
    def __init__(self, logger: logging.Logger):
        self.clients: dict[asyncio.StreamWriter, int] = {}
        self.next_client_id = 1
        self.response_counter = 0
        self.logger = logger

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        client_id = self.next_client_id
        self.next_client_id += 1
        self.clients[writer] = client_id
        peer = writer.get_extra_info("peername")
        print(f"Client {client_id} connected: {peer}")

        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break

                request_time = datetime.datetime.now()
                req_text = line.decode("ascii").strip()

                # 10% вероятность игнорирования
                if random.random() < 0.1:
                    self.logger.info("", extra={
                        "date": request_time.date(),
                        "req_time": request_time.strftime("%H:%M:%S.%f")[:-3],
                        "req_text": req_text,
                        "resp_time": "(проигнорировано)",
                        "resp_text": "(проигнорировано)"
                    })
                    continue

                # Ожидание от 100 до 1000 мс
                await asyncio.sleep(random.uniform(0.1, 1.0))

                resp_id = self.response_counter
                self.response_counter += 1
                req_num = req_text[1:req_text.find("]")]
                resp_text = f"[{resp_id}/{req_num}] PONG ({client_id})"

                writer.write((resp_text + "\n").encode("ascii"))
                await writer.drain()

                resp_time = datetime.datetime.now()
                self.logger.info("", extra={
                    "date": request_time.date(),
                    "req_time": request_time.strftime("%H:%M:%S.%f")[:-3],
                    "req_text": req_text,
                    "resp_time": resp_time.strftime("%H:%M:%S.%f")[:-3],
                    "resp_text": resp_text
                })
        finally:
            print(f"Client {client_id} disconnected")
            del self.clients[writer]
            writer.close()
            await writer.wait_closed()

    async def keepalive_task(self):
        while True:
            await asyncio.sleep(5)
            resp_id = self.response_counter
            self.response_counter += 1
            msg = f"[{resp_id}] keepalive\n"
            for w in list(self.clients.keys()):
                try:
                    w.write(msg.encode("ascii"))
                    await w.drain()
                except Exception:
                    pass


async def main():
    logger = setup_logger("server.log")
    server = Server(logger)
    srv = await asyncio.start_server(server.handle_client, "127.0.0.1", 8888)
    asyncio.create_task(server.keepalive_task())
    async with srv:
        await srv.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
