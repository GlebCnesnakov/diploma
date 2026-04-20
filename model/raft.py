import simpy
import random
from typing import Union, NoReturn, List, Generator
from metrics.metrics import Metrics, write_to_file
from model.network import NetworkManager


FOLLOWER = 'follower'
CANDIDATE = 'candidate'
LEADER = 'leader'
ELECTION_TIMEOUT = 5
VOTING_TIMEOUT = 2
NODE_PROBABILITY_FAILURE = 0.05
HEARTBIT = 5
LAMBDA_REQUEST = 0.1
EXPO_TIME = 1
UNIFORM_TIME = 0
UNIFORM_REQUEST_A = 1
UNIFORM_REQUEST_B = 2
ELECTION_MIN = HEARTBIT
ELECTION_MAX = ELECTION_MIN + 1
SLEEPING_TIME_MIN = 4
SLEEPING_TIME_MAX = 8
EXPO_REQUEST_TIME = 1
UNIFORM_REQUEST_TIME = 0
EXPO_SHUTDOWN_TIME = 0
UNIFORM_SHUTDOWN_A = 16
UNIFORM_SHUTDOWN_B = 20
UNIFORM_SHUTDOWN_TIME = 1
LAMBDA_SHUTDOWN = 0.1


def get_sleeping_time() -> float:
    return random.uniform(SLEEPING_TIME_MIN, SLEEPING_TIME_MAX)


def get_election_time() -> float:
    return random.uniform(ELECTION_MIN, ELECTION_MAX)


def get_next_request_time() -> Union[NoReturn, float]:
    if EXPO_REQUEST_TIME:
        return random.expovariate(lambd=LAMBDA_REQUEST)
    if UNIFORM_REQUEST_TIME:
        return random.uniform(UNIFORM_REQUEST_A, UNIFORM_REQUEST_B)
    raise ValueError("Time error")


def get_next_shutdown_time() -> Union[float, NoReturn]:
    if EXPO_SHUTDOWN_TIME:
        return random.expovariate(lambd=LAMBDA_SHUTDOWN)
    if UNIFORM_SHUTDOWN_TIME:
        return random.uniform(UNIFORM_SHUTDOWN_A, UNIFORM_SHUTDOWN_B)
    raise ValueError("Next shutdown error")


class RaftNode:
    processed_entries: int = 0
    network_manager: NetworkManager

    def __init__(self, env: simpy.Environment, name: str, cluster: List, metrics: Metrics, num_nodes):
        self.env: simpy.Environment = env
        self.name: str = name
        self.cluster: List = cluster
        self.node_number: int = num_nodes
        self.metrics: Metrics = metrics

        self.state: str = FOLLOWER
        self.is_shutdown: bool = False
        self.vote_count: int = 0
        self.voted: bool = False
        self.term: int = 0
        self.index: int = 0
        self.entries: int = 0
        self.sending_num: int = 0
        self.ack_count: int = 0
        self.commited_count: int = 0
        self.leader: RaftNode = None
        self.election_timeout: float = get_election_time()
        self.last_heard_from_leader: float = env.now

        self.requested_vote_event: simpy.Event = self.env.event()
        self.requested_vote_event.callbacks.append(self.vote_callback)
        self.ack_log_event: simpy.Event = self.env.event()
        self.ack_log_event.callbacks.append(self.ack_log_callback)
        self.commit_log_event: simpy.Event = self.env.event()
        self.commit_log_event.callbacks.append(self.commit_log_callback)

        self.timeout_proc: simpy.Process = None
        self.heartbit_proc: simpy.Process = None
        self.entry_proc: simpy.Process = None

        self.elections: bool = False

        env.process(self.run())
        env.process(self.shutdown_loop())

    def run(self) -> Generator:
        while True:
            if not self.is_shutdown:
                if self.state == FOLLOWER:
                    write_to_file(f'{self.name} фоловер', self.env)
                    self.set_new_timeout_event()
                    result = yield self.env.any_of([self.timeout_proc, self.ack_log_event, self.commit_log_event, self.requested_vote_event]) #возвращает словарь с тригер событиями?
                elif self.state == CANDIDATE:  # передать кандидата в ивент
                    if not self.elections:
                        self.set_new_voted_timeout_event()
                        self.term += 1
                        write_to_file(f'{self.name} кандидат',  self.env)
                        self.request_votes() # запрашиваем голоса
                    result = yield self.env.any_of([self.nodes_voted_timeout_event, self.ack_log_event, self.requested_vote_event])  #  ждём таймаут выборов, или когда проснется лидер, или когда(возможно) к нам постучаться проголосовать 
                elif self.state == LEADER:
                    write_to_file(f'{self.name} лидер', self.env)
                    result = yield self.env.any_of([self.heartbit_proc, self.entry_proc, self.ack_log_event])  # ждем либо когда будем посылать хартбит, либо когда придёт запрос, либо чужой хартбит от вохможного лидера
                    for event in result:
                        if event == self.heartbit_proc:
                            self.set_new_heartbit_event()
                        elif event == self.entry_proc:
                            self.set_new_entry_event(self)
            else:
                yield self.env.timeout(0.001)

    def shutdown_loop(self):
        while True:
            shutdown_time = get_next_shutdown_time()
            write_to_file(f'{self.name} ждёт перед выключением: {shutdown_time}', self.env)
            yield self.env.timeout(shutdown_time)

            sl = get_sleeping_time()
            write_to_file(f'{self.name} заснул на {sl}', self.env)
            self.is_shutdown = True
            self.metrics.common_outages += 1
            self.metrics.outages[self.node_number] += 1
            self.metrics.shutdown_time[self.node_number] += sl
            yield self.env.timeout(sl)

            self.is_shutdown = False
            write_to_file(f'{self.name} проснулся', self.env)

            if self.state == LEADER:
                self.set_new_heartbit_event(0)

    def heartbit_callback(self) -> None:
        if not self.is_shutdown:
            write_to_file(f'{self.name} посылает heartbit',  self.env)
            if self.entries > 0:
                self.sending_num = self.entries
            for i in self.cluster:
                if i != self:
                    self.network_manager.send(self.node_number, i.node_number, callback=lambda i=i: i.ack_log_event.succeed(value=self))
            self.env.process(self._process_ack())

    def _process_ack(self):
        if not self.is_shutdown:
            yield self.env.timeout(2.01) # ждём ответа узлов max_delay * 2?
            write_to_file(f'Лидер {self.name}, запросов:{self.entries} подтверждений: {self.ack_count}', self.env)
            if self.sending_num > 0:
                if self.ack_count >= len(self.cluster) // 2:  # подтвердило большинство
                    write_to_file(f'{self.name} посылает комиты',  self.env)
                    self.index += self.sending_num  # лидер фиксирует запись у себя
                    for i in self.cluster:
                        if i != self:
                            self.network_manager.send(self.node_number, i.node_number, callback=lambda i=i: i.commit_log_event.succeed(value=self))
                    RaftNode.processed_entries += self.sending_num  # считаем запрос закомиченым
                    self.entries -= self.sending_num
                else:
                    write_to_file('Запись не подтвердилась большинством', self.env)
            write_to_file(f'Зафиксированных записей: {RaftNode.processed_entries}', self.env)
            write_to_file(f'Общее количество записей: {self.metrics.processed_entries}', self.env)
            self.sending_num = 0
        self.ack_count = 0

    def entry_callback(self, leader) -> None:
        leader.entries += 1
        write_to_file(f'Лидер {leader.name} принял запрос, необработанных записей: {self.entries}',  leader.env)
        self.metrics.processed_entries += 1

    def nodes_voted_timeout_callback(self, event) -> None:
        write_to_file(f'{self.name} проверка результатов выборов',  self.env)
        if self.vote_count > len(self.cluster) // 2:
            write_to_file(f'{self.name} стал лидером',  self.env)
            self.state = LEADER
            self.metrics.elected_leaders_amount[self.node_number] += 1
            self.interrupt_timeout_event()  # прервать таймаут избранного лидера
            self.set_new_heartbit_event()
            self.set_new_entry_event(self)
        else:
            self.state = FOLLOWER
            write_to_file(f'{self.name} проиграл выборы и стал фоловером',  self.env)
        self.vote_count = 0
        self.elections = False

    def timeout_callback(self, event=None) -> None:
        if not self.is_shutdown and self.state != LEADER and not self.voted:
            write_to_file(f'{self.name} таймаут колбек. Последний хартбит от лидера: {self.last_heard_from_leader}', self.env)
            write_to_file(f"{self.name} не получил ответа и переходит в состояние кандидата.", self.env)
            self.state = CANDIDATE
        if self.metrics.election_start_time != 0:
            self.metrics.election_start_time = self.env.now

    def ack_log_callback(self, event) -> None:
        write_to_file(f'К {self.name} пришел запрос ack', self.env)
        self.leader = event.value
        if self.state == CANDIDATE and self.term < self.leader.term:
            self.state = FOLLOWER
        if not self.is_shutdown and not self.leader.is_shutdown and self.term <= self.leader.term:
            if self.state == LEADER:
                self.entries = 0
                if self.leader.term >= self.term:
                    if self.heartbit_proc.is_alive:
                        self.heartbit_proc.interrupt()
                        write_to_file(f'Прерывание хартбита у {self.name}', self.env)
                    else:
                        write_to_file(f'Хартбита нет у {self.name}', self.env)
                    if self.entry_proc.is_alive:
                        self.entry_proc.interrupt()
                        write_to_file(f'Прерывание Entry у {self.name}', self.env)
                    else:
                        write_to_file(f'Entry нет у {self.name}', self.env)
                    
                    self.metrics.election_lasting += self.env.now - self.metrics.election_start_time
                    self.metrics.election_start_time = 0

            self.state = FOLLOWER
            if self.leader.sending_num > 0 and self.index != self.leader.index:  # фоловер не синхронизирован
                write_to_file(f'{self.name} не синхронизирован с {self.leader.name}, терм лидера {self.leader.term}, индекс лидера {self.leader.index}, терм узла {self.term} индекс узла {self.index}',  self.env)

                def syn_index():
                    self.index = self.leader.index
                    self.metrics.syn_requests[self.node_number] += 1
                    write_to_file(f'синхронизация {self.name}', self.env)

                #double = True, 2 сетевых взаимодействия - уведомление о синхронизации и нужные данные от лидера
                self.network_manager.send(self.leader.node_number, self.node_number, callback=syn_index, double=True)
            if self.leader.sending_num > 0:  # если это не простой хартбит

                def ack():
                    self.leader.ack_count += 1
                    self.voted = False  # после выборов нужно установить в False
                    self.vote_count = 0
                    write_to_file(f'{self.name} подтвердил запрос {self.leader.name}, терм лидера {self.leader.term}, индекс лидера {self.leader.index}, терм узла {self.term} индекс узла {self.index}',  self.env)
                self.network_manager.send(self.node_number, self.leader.node_number, callback=ack)
            self.voted = False  # после выборов нужно установить в False
            self.vote_count = 0
        self.last_heard_from_leader = self.env.now
        self.term = self.leader.term
        self.set_new_ack_event()

    def commit_log_callback(self, event) -> None:
        if not self.is_shutdown and self.term <= self.leader.term: # and self.index + 1 == self.leader.index ?
            self.leader.commited_count += 1
            self.index = self.leader.index  # не += 1, т.к. если обновится терм, то индекс должен слететь на 0
            #self.index += 1
            write_to_file(f'{self.name} закоммитил запрос {self.leader.name}, терм лидера {self.leader.term}, индекс лидера {self.leader.index}, терм {self.term} индекс {self.index}', self.env)

        self.set_new_commit_event()

    def vote_callback(self, event) -> None:
        #candidate = event.value
        candidate = event
        # сразу создаём новое событие для следующего запроса
        self.set_new_vote_event()
        write_to_file(f'{self.name} {self.voted} {self.state}', self.env)

        if not self.voted and self.state != LEADER:
            write_to_file(f'{self.name} голосует',  self.env)
            if (candidate.term == self.term and candidate.index >= self.index) or candidate.term > self.term:
                def vote():
                    if not self.voted:
                        if candidate.term > self.term:
                            self.term += 1
                            write_to_file(f'{self.name} увеличил терм из-за кандидата',  self.env)
                        candidate.vote_count += 1
                        self.voted = True
                        write_to_file(f'{self.name} проголосовал за {candidate.name}',  self.env)
                # вызываем через сеть
                self.network_manager.send(self.node_number, candidate.node_number, callback=vote)

    def request_votes(self) -> None:
        self.elections = True
        write_to_file(f'{self.name} начал собирать голоса', self.env)
        self.vote_count = 1  # голосуем за себя
        self.voted = True
        for node in self.cluster:  # посылаем запросы
            if node != self and not node.is_shutdown:
                self.network_manager.send(self.node_number, node.node_number, callback=lambda n=node: n.vote_callback(event=self))

    def set_new_ack_event(self):
        self.ack_log_event = self.env.event()
        self.ack_log_event.callbacks.append(self.ack_log_callback)

    def set_new_commit_event(self):
        self.commit_log_event = self.env.event()
        self.commit_log_event.callbacks.append(self.commit_log_callback)

    def set_new_vote_event(self):
        self.requested_vote_event = self.env.event()
        self.requested_vote_event.callbacks.append(self.vote_callback)

    def timeout_process(self):  # процесс для таймаута, т.к. Timeout все равно сработает в any_of после отмены
        try:
            yield self.env.timeout(self.election_timeout)
            self.timeout_callback()
        except simpy.Interrupt:
            ...

    def heartbit_process(self, time=HEARTBIT):
        try:
            yield self.env.timeout(time)
            self.heartbit_callback()
        except simpy.Interrupt:
            write_to_file(f'{self.name} хартбит прерван', self.env)

    def entry_process(self, leader):
        try:
            yield self.env.timeout(get_next_request_time())
            self.entry_callback(leader)
        except simpy.Interrupt:
            write_to_file(f'{self.name} entry прерван', self.env)

    def set_new_timeout_event(self):
        self.election_timeout = get_election_time()
        write_to_file(f'{self.name} следующий таймаут: {self.env.now + self.election_timeout}', self.env)
        if self.timeout_proc is not None and self.timeout_proc.is_alive:
            self.timeout_proc.interrupt()
        self.timeout_proc = self.env.process(self.timeout_process())

    def interrupt_timeout_event(self):
        if self.timeout_proc is not None and self.timeout_proc.is_alive:
            self.timeout_proc.interrupt()

    def set_new_voted_timeout_event(self):
        self.nodes_voted_timeout_event = self.env.timeout(VOTING_TIMEOUT)
        self.nodes_voted_timeout_event.callbacks.append(self.nodes_voted_timeout_callback)

    def set_new_heartbit_event(self, time=HEARTBIT):
        if self.heartbit_proc is not None and self.heartbit_proc.is_alive:
            self.heartbit_proc.interrupt()
        self.heartbit_proc = self.env.process(self.heartbit_process(time=time))

    def set_new_entry_event(self, leader):
        if self.entry_proc is not None and self.entry_proc.is_alive and self.entry_proc != self.env.active_process:
            self.entry_proc.interrupt()
        self.entry_proc = self.env.process(self.entry_process(leader))


def run_simulation():
    env = simpy.Environment()
    num_nodes = 4
    metrics = Metrics(env, num_nodes=num_nodes)
    network_mamanger = NetworkManager(env, num_nodes=num_nodes, max_delay=0.5)
    RaftNode.network_manager = network_mamanger
    leader_node = 0
    cluster = [RaftNode(env, f"Узел {i}", [], metrics, i) for i in range(metrics.num_nodes)]
    cluster[leader_node].state = LEADER
    cluster[leader_node].set_new_entry_event(cluster[0])
    cluster[leader_node].set_new_heartbit_event()

    for node in cluster:
        node.cluster = cluster
        node.leader = cluster[leader_node]
    env.run(until=300)
    metrics.calculate_metrics(RaftNode.processed_entries)
    clear_file()


def clear_file():
    input('Enter:')
    with open('results.txt', 'w') as f:
        f.write('')


run_simulation()
