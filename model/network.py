import simpy
import random
from metrics.metrics import write_to_file
from typing import Generator, List
from logs.logs_setup import get_logger
import networkx as nx
import json


class NetworkManager:
    def __init__(self, env: simpy.Environment, num_nodes: int, min_delay: float = 0.001, max_delay: float = 3.0):
        self.logger = get_logger('Сетевая задержка')
        self.env = env
        self.num_nodes = num_nodes
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.delays = [[None for _ in range(self.num_nodes)] for _ in range(self.num_nodes)]
        for i in range(self.num_nodes):
            self.delays[i][i] = 0.0


        self.graph = nx.Graph()
        # with open('desktop/topologies/topology_2026-05-15_13-47-38.json') as f:
        #     data = json.load(f)
        #self.fill_delays()
        #self.set_topology(data)
        self.active_graph = nx.Graph()
        self.set_topology()
        print(self.delays)

    def set_topology(self, data: json = None):
        self.graph = nx.Graph()
        if data is None:
            with open('desktop/topologies/topology_2026-05-15_13-47-38.json') as f:
                data = json.load(f)
        for node in data['nodes']:
            self.graph.add_node(
                node['id'],
                enabled=node.get('enabled', True)
            )
        for edge in data['edges']:
            self.graph.add_edge(
                edge['source'],
                edge['target'],
                delay=edge['delay']
            )
        self.num_nodes = self.graph.number_of_nodes()
        self.fill_delays()
        

    def refresh_delays(self):
        self.delays = [[None for _ in range(self.num_nodes)] for _ in range(self.num_nodes)]
        for i in range(self.num_nodes):
            self.delays[i][i] = 0.0
        self.fill_delays()

    def fill_delays(self):
            # for i in range(self.num_nodes):
            #     for j in range(i + 1):
            #         self.delays[i][j] = self.delays[j][i]
            #     for j in range(i + 1, self.num_nodes):
            #         self.delays[i][j] = random.uniform(self.min_delay, self.max_delay)
        self.delays = [
            [None for _ in range(self.num_nodes)]
            for _ in range(self.num_nodes)
        ]

        for i in range(self.num_nodes):
            self.delays[i][i] = 0.0

        for src, dst, attrs in self.graph.edges(data=True):
            if src >= self.num_nodes or dst >= self.num_nodes:
                raise ValueError(
                    f'Edge {src}->{dst} выходит за пределы num_nodes={self.num_nodes}'
                )

            delay = attrs['delay']
            self.delays[src][dst] = delay
            self.delays[dst][src] = delay
        print(self.delays)



    def check_nodes(self, i: int, j: int) -> bool:
        if i >= 0 and j >= 0 and i <= self.num_nodes - 1 and j <= self.num_nodes - 1 and i != j:
            return True
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
            self.logger.info(f'Отправка {i}->{j}, {delay} с.')
            self.env.process(self._deliver(delay, env=self.env, callback=callback))

    def _deliver(self, time, env, callback: None) -> Generator:
        yield env.timeout(time)
        if callback is not None:
            callback()

    def build_active_graph(self):
        active_graph = self.graph.copy()
        disabled_nodes = [
            n
            for n, attrs in active_graph.nodes(data=True)
            if not attrs.get('enabled', True)
        ]
        active_graph.remove_nodes_from(disabled_nodes)
        return active_graph

    def get_next_hop(self, src, dst):
        if self.check_nodes(src, dst):
            self.active_graph = self.build_active_graph()
            try:
                path = nx.shortest_path(
                    self.active_graph,
                    source=src,
                    target=dst,
                    weight='delay'
                )
                if len(path) < 2:
                    return None
                return path[1]
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return None

    def enable_node(self, node_id: int):
        if node_id in self.graph.nodes:
            self.graph.nodes[node_id]['enabled'] = True

    def disable_node(self, node_id: int):
        if node_id in self.graph.nodes:
            self.graph.nodes[node_id]['enabled'] = False
