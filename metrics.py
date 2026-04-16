import matplotlib.pyplot as plt 


def write_to_file(text, env):
    with open('results.txt', mode='a') as f:
        f.write(f'\n{round(env.now, 3)}: {text}')


class Metrics:
    def __init__(self, env, num_nodes):
        self.processed_entries: int = 0
        self.num_nodes: int = num_nodes
        self.common_outages: int = 0
        self.outages: list = [0] * self.num_nodes
        self.elected_leaders_amount = [0] * self.num_nodes
        self.syn_requests: list = [0] * self.num_nodes
        self.shutdown_time: list = [0] * self.num_nodes
        self.env = env
        self.election_start_time: float = 0
        self.election_lasting: float = 0

    def get_accuracy(self, served_entries) -> None:
        write_to_file(f'\nЗафиксировано/Издано: {served_entries / self.processed_entries }\n', self.env)

    def get_common_outages(self) -> None:
        write_to_file(f'Общее количество отключений: {self.common_outages}\n', self.env)

    def get_elected_nodes(self) -> None:
        write_to_file(f'Количество избраний лидером каждого узла:\n', self.env)
        for i in range(self.num_nodes):
            write_to_file(f'Узел {i}: {self.elected_leaders_amount[i]}', self.env)
        write_to_file('\n', self.env)

    def get_outages(self) -> None:
        write_to_file(f'Количество отключений каждого узла:\n', self.env)
        for i in range(self.num_nodes):
            write_to_file(f'Узел {i}: {self.outages[i]}', self.env)
        write_to_file('\n', self.env)

    def get_syn_requests(self) -> None:
        write_to_file(f'Количество запросов на синхронизацию каждого узла:\n', self.env)
        for i in range(self.num_nodes):
            write_to_file(f'Узел {i}: {self.syn_requests[i]}', self.env)
        write_to_file('\n', self.env)

    def get_shutdown_time(self) -> None:
        write_to_file(f'Продолжительность отключения каждого узла:\n', self.env)
        for i in range(self.num_nodes):
            write_to_file(f'Узел {i}: {self.shutdown_time[i]}', self.env)
        write_to_file('\n', self.env)

    def get_election_time(self) -> None:
        write_to_file(f'Продолжительность выборов: {self.common_outages}\n', self.env)

    def build_request_time_graph(self, time, processed_entries, common_entries) -> None:  # график запросы-время
        ...

    def calculate_metrics(self, served_entries) -> None:
        self.get_accuracy(served_entries=served_entries)
        self.get_common_outages()
        self.get_elected_nodes()
        self.get_outages()
        self.get_syn_requests()
        self.get_shutdown_time()
        self.get_election_time()
