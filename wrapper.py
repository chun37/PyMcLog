import datetime
import subprocess
from dataclasses import dataclass

from rx import operators as ops
from rx.subject import Subject


@dataclass
class Log:
    time: datetime.time
    level: str
    message: str


class LogStream(Subject):
    def __init__(self) -> None:
        super().__init__()
        self.member = []
        self.working = False
        self.log = self.pipe(
            ops.filter(lambda text: self.is_parsable(text)),
            ops.map(lambda text: self.log_parse(text))
        )
        self._on_ready = self.log.pipe(
            ops.filter(lambda log: self.working is False),
            ops.filter(lambda log: "Done" in log.message)
        ).subscribe(self.on_ready)
        self._on_join = self.log.pipe(
            ops.filter(lambda log: "logged in" in log.message)
        ).subscribe(self.on_join)
        self.user_activity = self.log.pipe(
            ops.filter(lambda log: self.is_joined_member(log)),
            ops.filter(lambda log: "lost connection:" not in log.message),
            ops.filter(lambda log: "logged in" not in log.message)
        )
        self._on_leave = self.user_activity.pipe(
            ops.filter(lambda log: "left the game" in log.message)
        ).subscribe(self.on_leave)
        self._on_died = self.user_activity.pipe(
            ops.filter(lambda log: "left the game" not in log.message)
        ).subscribe(self.on_died)

    def is_parsable(self, text: str) -> bool:
        return len(text.split(": ", maxsplit=1)) == 2

    def is_joined_member(self, log: Log) -> bool:
        return log.message.split()[0] in self.member

    def log_parse(self, text: str) -> Log:
        data, message = text.split(": ", maxsplit=1)
        time, level = data.split(maxsplit=1)
        time = map(int, time[1: -1].split(":"))
        return Log(datetime.time(*time), level[1: -1], message)

    def on_ready(self, log: Log) -> None:
        print("[start]", log)

    def on_join(self, log: Log) -> None:
        print("[join]", log.message)
        self.member.append(log.message.split("[", maxsplit=1)[0])

    def on_died(self, log: Log) -> None:
        print("[died]", log.message)

    def on_leave(self, log: Log) -> None:
        print("[leave]", log.message)
        self.member.remove(log.message.split()[0])


class Minecraft:
    def __init__(self, cmd: str) -> None:
        self.minecraft = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
        self.stream = LogStream()

    def add_event(self, text: str) -> None:
        self.stream.on_next(text)

    def send_input(self, text: str) -> None:
        self.minecraft.stdin.write(f"{text}\n".encode())
        self.minecraft.stdin.flush()

    def run(self) -> None:
        try:
            for line in iter(self.minecraft.stdout.readline, ""):
                line = line.decode().rstrip()
                if not line:
                    continue
                self.add_event(line)
        except KeyboardInterrupt as e:
            self.send_input("stop")
            print("stop")


if __name__ == "__main__":
    cmd = "java -jar spigot-1.14.4.jar"
    minecraft = Minecraft(cmd)
    minecraft.run()
