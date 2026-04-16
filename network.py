import simpy
import random
from metrics import write_to_file
from typing import NoReturn, Generator, List


class NetworkManager:
    def __init__(self, env: simpy.Environment, num_nodes: int, min_delay: float = 0.001, max_delay: float = 3.0):
        self.env = env
        self.num_nodes = num_nodes
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.delays: List[List[float]] = [[0.0 for _ in range(self.num_nodes)] for _ in range(self.num_nodes)]
        self.fill_delays()
        data = '\n'.join([str(self.delays[i]) for i in range(self.num_nodes)])
        write_to_file(data, self.env)

    def fill_delays(self):
        for i in range(self.num_nodes):
            for j in range(i + 1):
                self.delays[i][j] = self.delays[j][i]
            for j in range(i + 1, self.num_nodes):
                self.delays[i][j] = random.uniform(self.min_delay, self.max_delay)

    def check_nodes(self, i: int, j: int) -> bool:
        if i >= 0 and j >= 0 and i <= self.num_nodes - 1 and j <= self.num_nodes - 1 and i != j:
            return True
        write_to_file(f'НЕВЕРНЫЙ МАРШРУТ {i} -> {j}', self.env)
        return False

    def set_delay(self, i: int, j: int, delay: float) -> None:
        if delay >= self.min_delay and delay <= self.max_delay and self.check_nodes(i, j):
            self.delays[i][j] = delay

    def get_delay(self, i: int, j: int) -> float:
        return self.delays[i][j]

    def send(self, i: int, j: int, callback=None, double=False) -> None:
        if self.check_nodes(i, j):
            delay = self.get_delay(i, j)
            if double:
                delay *= 2
            write_to_file(f'Отправка {i}->{j}, {delay} мс.', self.env)
            self.env.process(self._deliver(delay, env=self.env, callback=callback))

    def _deliver(self, time, env, callback: None) -> Generator:
        yield env.timeout(time)
        if callback is not None:
            callback()
