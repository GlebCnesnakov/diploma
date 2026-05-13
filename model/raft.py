import simpy
import random
from typing import Union, NoReturn, List, Generator
from metrics.metrics import Metrics, write_to_file
from model.network import NetworkManager
import datetime
from logs.logs_setup import get_logger, setup_logging



FOLLOWER = 'follower'
CANDIDATE = 'candidate'
LEADER = 'leader'

    # election_timeout = 6
    # voting_timeout = 2
    # heartbeat = 5
    # election_min = heartbeat + 0.5
    # election_max = election_min + 1

 # self.lambda_request = 0.1
        # self.expo_time = 1
        # self.uniform_time = 0

        # self.uniform_request_a = 1
        # self.uniform_request_b = 2

        # self.sleeping_time_min = 4
        # self.sleeping_time_max = 8

        # self.expo_request_time = 1
        # self.uniform_request_time = 0

        # self.expo_shutdown_time = 0
        # self.uniform_shutdown_a = 16
        # self.uniform_shutdown_b = 20
        # self.uniform_shutdown_time = 1
        # self.lambda_shutdown = 0.1

class RaftNode:
    processed_entries: int = 0
    network_manager: NetworkManager
    timestamp: datetime.datetime

    election_timeout = 6
    voting_timeout = 2
    heartbeat = 5
    sleeping_time_min = 4
    sleeping_time_max = 8
    election_min = heartbeat + 0.5
    election_max = election_min + 1

    def __init__(self, env: simpy.Environment, name: str, cluster: List, metrics: Metrics, num_nodes: int, settings: dict):
        self.lambda_request = None
        self.uniform_request_a = None
        self.uniform_request_b = None
        self.expo_request_time = None
        self.uniform_request_time = None
        self.manual_request_time = None
        self.settings = settings
        self.expo_shutdown_time = None
        self.uniform_shutdown_a = None
        self.uniform_shutdown_b = None
        self.uniform_shutdown_time = None
        self.lambda_shutdown = None
        self.manual_shutdown_time = None
        

        if settings['request_time']['type'] == 'exponential':
            self.lambda_request = settings['request_time']['lambda']
            self.expo_request_time = 1
        elif settings['request_time']['type'] == 'random':
            self.uniform_request_a = settings['request_time']['a']
            self.uniform_request_b = settings['request_time']['b']
            self.uniform_request_time = 1
        else:
            self.manual_request_time = 1

        if settings['shutdown_time']['type'] == 'exponential':
            self.lambda_shutdown = settings['shutdown_time']['lambda']
            self.expo_shutdown_time = 1
        elif settings['shutdown_time']['type'] == 'random':
            self.uniform_shutdown_a = settings['shutdown_time']['a']
            self.uniform_shutdown_b = settings['shutdown_time']['b']
            self.uniform_shutdown_time = 1
        else:
            self.manual_shutdown_time = 1

        self.env: simpy.Environment = env
        self.name: str = name
        self.cluster: List = cluster
        self.node_number: int = num_nodes
        self.metrics: Metrics = metrics
        self.logger = get_logger(self.name)
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
        self.election_timeout: float = self.get_election_time()
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

    def get_sleeping_time(self) -> float:
        return random.uniform(RaftNode.sleeping_time_min, RaftNode.sleeping_time_max)

    def get_election_time(self) -> float:
        return random.uniform(RaftNode.election_min, RaftNode.election_max)

    def get_next_request_time(self) -> Union[NoReturn, float]:
        if self.expo_request_time:
            return random.expovariate(lambd=self.lambda_request)
        if self.uniform_request_time:
            return random.uniform(self.uniform_request_a, self.uniform_request_b)
        if self.manual_request_time:
            return self.settings['request_time']['value']
        raise ValueError("time error")

    def get_next_shutdown_time(self) -> Union[float, NoReturn]:
        if self.expo_shutdown_time:
            return random.expovariate(lambd=self.lambda_shutdown)
        if self.uniform_shutdown_time:
            return random.uniform(self.uniform_shutdown_a, self.uniform_shutdown_b)
        if self.manual_shutdown_time:
            return self.settings['shutdown_time']['value']
        raise ValueError("Next shutdown error")

    def run(self) -> Generator:
        while True:
            if not self.is_shutdown:
                if self.state == FOLLOWER:
                    #write_to_file(f'{self.name} фоловер', self.env, RaftNode.timestamp)
                    self.logger.info(f'{self.env.now} Фоловер')
                    self.set_new_timeout_event()
                    result = yield self.env.any_of([self.timeout_proc, self.ack_log_event, self.commit_log_event, self.requested_vote_event]) #возвращает словарь с тригер событиями?
                elif self.state == CANDIDATE:  # передать кандидата в ивент
                    if not self.elections:
                        self.set_new_voted_timeout_event()
                        self.term += 1
                        #write_to_file(f'{self.name} кандидат',  self.env, RaftNode.timestamp)
                        self.logger.info(f'{self.env.now} Кандидат')
                        self.request_votes() # запрашиваем голоса
                    result = yield self.env.any_of([self.nodes_voted_timeout_event, self.ack_log_event, self.requested_vote_event])  #  ждём таймаут выборов, или когда проснется лидер, или когда(возможно) к нам постучаться проголосовать 
                elif self.state == LEADER:
                    #write_to_file(f'{self.name} лидер', self.env, RaftNode.timestamp)
                    self.logger.info(f'{self.env.now} Лидер')
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
            shutdown_time = self.get_next_shutdown_time()
            #write_to_file(f'{self.name} ждёт перед выключением: {shutdown_time}', self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Ждёт перед выключением: {shutdown_time}')
            yield self.env.timeout(shutdown_time)

            sl = self.get_sleeping_time()
            #write_to_file(f'{self.name} заснул на {sl}', self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Заснул на {sl}')
            self.is_shutdown = True
            self.metrics.common_outages += 1
            self.metrics.outages[self.node_number] += 1
            self.metrics.shutdown_time[self.node_number] += sl
            yield self.env.timeout(sl)

            self.is_shutdown = False
            #write_to_file(f'{self.name} проснулся', self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Проснулся')

            if self.state == LEADER:
                self.set_new_heartbit_event(0)

    def heartbit_callback(self) -> None:
        if not self.is_shutdown:
            #write_to_file(f'{self.name} посылает heartbit',  self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Посылает heartbit')
            if self.entries > 0:
                self.sending_num = self.entries
            for i in self.cluster:
                if i != self:
                    self.network_manager.send(self.node_number, i.node_number, callback=lambda i=i: i.ack_log_event.succeed(value=self), timestamp=RaftNode.timestamp)
            self.env.process(self._process_ack())

    def _process_ack(self):
        if not self.is_shutdown:
            yield self.env.timeout(2.01) # ждём ответа узлов max_delay * 2?
            #write_to_file(f'Лидер {self.name}, запросов:{self.entries} подтверждений: {self.ack_count}', self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Лидер {self.name}, запросов:{self.entries} подтверждений: {self.ack_count}')
            if self.sending_num > 0:
                if self.ack_count >= len(self.cluster) // 2:  # подтвердило большинство
                    #write_to_file(f'{self.name} посылает комиты',  self.env, RaftNode.timestamp)
                    self.logger.info(f'{self.env.now} Посылает комиты')
                    self.index += self.sending_num  # лидер фиксирует запись у себя
                    self.metrics.add_values_committed(self.sending_num)
                    self.metrics.times_committed.append(self.env.now)
                    for i in self.cluster:
                        if i != self:
                            self.network_manager.send(self.node_number, i.node_number, callback=lambda i=i: i.commit_log_event.succeed(value=self), timestamp=RaftNode.timestamp)
                    RaftNode.processed_entries += self.sending_num  # считаем запрос закомиченым
                    self.entries -= self.sending_num
                else:
                    #write_to_file('Запись не подтвердилась большинством', self.env, RaftNode.timestamp)
                    self.logger.info('{self.env.now} Запись не подтвердилась большинством')
            #write_to_file(f'Зафиксированных записей: {RaftNode.processed_entries}', self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Зафиксированных записей: {RaftNode.processed_entries}')
            #write_to_file(f'Общее количество записей: {self.metrics.processed_entries}', self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Общее количество записей: {self.metrics.processed_entries}')
            self.sending_num = 0
        self.ack_count = 0

    def entry_callback(self, leader) -> None:
        leader.entries += 1
        
        #write_to_file(f'Лидер {leader.name} принял запрос, необработанных записей: {self.entries}',  leader.env, RaftNode.timestamp)
        self.logger.info(f'{self.env.now} Лидер принял запрос, необработанных записей: {self.entries}')
        self.metrics.add_values_requested()
        self.metrics.times_requested.append(self.env.now)
        self.metrics.processed_entries += 1

    def nodes_voted_timeout_callback(self, event) -> None:
        #write_to_file(f'{self.name} проверка результатов выборов',  self.env, RaftNode.timestamp)
        self.logger.info(f'{self.env.now} Проверка результатов выборов')
        if self.vote_count > len(self.cluster) // 2:
            #write_to_file(f'{self.name} стал лидером',  self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Стал лидером')
            self.state = LEADER
            self.metrics.elected_leaders_amount[self.node_number] += 1
            self.interrupt_timeout_event()  # прервать таймаут избранного лидера
            self.set_new_heartbit_event()
            self.set_new_entry_event(self)
            self.metrics.election_lasting += self.env.now - self.metrics.election_start_time
            self.metrics.election_start_time = 0
            #write_to_file(f'ВРЕМЯ ВЫБОРОВ ПРОШЛО {self.metrics.election_lasting}', self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} ВРЕМЯ ВЫБОРОВ ПРОШЛО {self.metrics.election_lasting}')
        else:
            self.state = FOLLOWER
            #write_to_file(f'{self.name} проиграл выборы и стал фоловером',  self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Проиграл выборы и стал фоловером')
            if self.metrics.election_start_time != 0:           
                self.metrics.election_lasting += self.env.now - self.metrics.election_start_time
                self.metrics.election_start_time = 0
                #write_to_file(f'ВРЕМЯ ВЫБОРОВ ПРОШЛО {self.metrics.election_lasting}', self.env, RaftNode.timestamp)
                self.logger.info(f'{self.env.now} ВРЕМЯ ВЫБОРОВ ПРОШЛО {self.metrics.election_lasting}')
        self.vote_count = 0
        self.elections = False

    def timeout_callback(self, event=None) -> None:
        if not self.is_shutdown and self.state != LEADER and not self.voted:
            #write_to_file(f'{self.name} таймаут колбек. Последний хартбит от лидера: {self.last_heard_from_leader}', self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Таймаут колбек. Последний хартбит от лидера: {self.last_heard_from_leader}')
            #write_to_file(f"{self.name} не получил ответа и переходит в состояние кандидата.", self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Не получил ответа и переходит в состояние кандидата.')
            self.state = CANDIDATE
            if self.metrics.election_start_time == 0:
                self.metrics.election_start_time = self.env.now
                #write_to_file('ФИКСАЦИЯ ВРЕМЕНИ', self.env, RaftNode.timestamp)
                self.logger.info('{self.env.now} ФИКСАЦИЯ ВРЕМЕНИ')

    def ack_log_callback(self, event) -> None:
        #write_to_file(f'К {self.name} пришел запрос ack', self.env, RaftNode.timestamp)
        self.logger.info(f'{self.env.now} Пришел запрос ack')
        self.leader = event.value
        if self.state == CANDIDATE and self.term < self.leader.term:
            self.state = FOLLOWER
            self.metrics.election_lasting += (self.env.now - self.metrics.election_start_time)
            self.metrics.election_start_time = 0
            #write_to_file(f'ВРЕМЯ ВЫБОРОВ ПРОШЛО {self.metrics.election_lasting}', self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} ВРЕМЯ ВЫБОРОВ ПРОШЛО {self.metrics.election_lasting}')
        if not self.is_shutdown and not self.leader.is_shutdown and self.term <= self.leader.term:
            if self.state == LEADER:
                self.entries = 0
                if self.leader.term >= self.term:
                    if self.heartbit_proc.is_alive:
                        self.heartbit_proc.interrupt()
                        #write_to_file(f'Прерывание хартбита у {self.name}', self.env, RaftNode.timestamp)
                        self.logger.info(f'{self.env.now} Прерывание хартбита')
                    else:
                        #write_to_file(f'Хартбита нет у {self.name}', self.env, RaftNode.timestamp)
                        self.logger.info(f'{self.env.now} Хартбита нет')
                    if self.entry_proc.is_alive:
                        self.entry_proc.interrupt()
                        #write_to_file(f'Прерывание Entry у {self.name}', self.env, RaftNode.timestamp)
                        self.logger.info(f'{self.env.now} Прерывание Entry')
                    else:
                        #write_to_file(f'Entry нет у {self.name}', self.env, RaftNode.timestamp)
                        self.logger.info(f'{self.env.now} Entry нет')
                    
                    self.metrics.election_lasting += self.env.now - self.metrics.election_start_time
                    self.metrics.election_start_time = 0
                    #write_to_file(f'ВРЕМЯ ВЫБОРОВ ПРОШЛО {self.metrics.election_lasting}', self.env, RaftNode.timestamp)
                    self.logger.info(f'{self.env.now} ВРЕМЯ ВЫБОРОВ ПРОШЛО {self.metrics.election_lasting}')

            self.state = FOLLOWER
            if self.leader.sending_num > 0 and self.index != self.leader.index:  # фоловер не синхронизирован
                #write_to_file(f'{self.name} не синхронизирован с {self.leader.name}, терм лидера {self.leader.term}, индекс лидера {self.leader.index}, терм узла {self.term} индекс узла {self.index}',  self.env, RaftNode.timestamp)
                self.logger.info(f'{self.env.now} Не синхронизирован с {self.leader.name}, терм лидера {self.leader.term}, индекс лидера {self.leader.index}, терм узла {self.term} индекс узла {self.index}')

                def syn_index():
                    self.index = self.leader.index
                    self.metrics.syn_requests[self.node_number] += 1
                    #write_to_file(f'синхронизация {self.name}', self.env, RaftNode.timestamp)
                    self.logger.info(f'{self.env.now} Cинхронизация')

                #double = True, 2 сетевых взаимодействия - уведомление о синхронизации и нужные данные от лидера
                self.network_manager.send(self.leader.node_number, self.node_number, callback=syn_index, double=True, timestamp=RaftNode.timestamp)
            if self.leader.sending_num > 0:  # если это не простой хартбит

                def ack():
                    self.leader.ack_count += 1
                    self.voted = False  # после выборов нужно установить в False
                    self.vote_count = 0
                    #write_to_file(f'{self.name} подтвердил запрос {self.leader.name}, терм лидера {self.leader.term}, индекс лидера {self.leader.index}, терм узла {self.term} индекс узла {self.index}',  self.env, RaftNode.timestamp)
                    self.logger.info(f'{self.env.now} Gодтвердил запрос {self.leader.name}, терм лидера {self.leader.term}, индекс лидера {self.leader.index}, терм узла {self.term} индекс узла {self.index}')
                self.network_manager.send(self.node_number, self.leader.node_number, callback=ack, timestamp=RaftNode.timestamp)
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
            #write_to_file(f'{self.name} закоммитил запрос {self.leader.name}, терм лидера {self.leader.term}, индекс лидера {self.leader.index}, терм {self.term} индекс {self.index}', self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Закоммитил запрос {self.leader.name}, терм лидера {self.leader.term}, индекс лидера {self.leader.index}, терм {self.term} индекс {self.index}')
        self.set_new_commit_event()

    def vote_callback(self, event) -> None:
        #candidate = event.value
        if not self.is_shutdown: 
            candidate = event
            # сразу создаём новое событие для следующего запроса
            self.set_new_vote_event()
            #write_to_file(f'{self.name} {self.voted} {self.state}', self.env, RaftNode.timestamp)
            #self.logger.info(f'{self.name} {self.voted} {self.state}')

            if not self.voted and self.state != LEADER:
                #write_to_file(f'{self.name} голосует',  self.env, RaftNode.timestamp)
                self.logger.info(f'{self.env.now} Голосует')
                if (candidate.term == self.term and candidate.index >= self.index) or candidate.term > self.term:
                    def vote():
                        if not self.voted:
                            if candidate.term > self.term:
                                self.term += 1
                                #write_to_file(f'{self.name} увеличил терм из-за кандидата',  self.env, RaftNode.timestamp)
                                self.logger.info(f'{self.env.now} Увеличил терм из-за кандидата')
                            candidate.vote_count += 1
                            self.voted = True
                            #write_to_file(f'{self.name} проголосовал за {candidate.name}',  self.env, RaftNode.timestamp)
                            self.logger.info(f'{self.env.now} Проголосовал за {candidate.name}')
                    # вызываем через сеть
                    self.network_manager.send(self.node_number, candidate.node_number, callback=vote, timestamp=RaftNode.timestamp)

    def request_votes(self) -> None:
        self.elections = True
        #write_to_file(f'{self.name} начал собирать голоса', self.env, RaftNode.timestamp)
        self.logger.info(f'{self.env.now} Начал собирать голоса')
        self.vote_count = 1  # голосуем за себя
        self.voted = True
        for node in self.cluster:  # посылаем запросы
            if node != self:
                self.network_manager.send(self.node_number, node.node_number, callback=lambda n=node: n.vote_callback(event=self), timestamp=RaftNode.timestamp)

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

    def heartbit_process(self, time=None):
        if time is None:
            time = RaftNode.heartbeat
        try:
            yield self.env.timeout(time)
            self.heartbit_callback()
        except simpy.Interrupt:
            #write_to_file(f'{self.name} хартбит прерван', self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Хартбит прерван')

    def entry_process(self, leader):
        try:
            yield self.env.timeout(self.get_next_request_time())
            self.entry_callback(leader)
        except simpy.Interrupt:
            #write_to_file(f'{self.name} entry прерван', self.env, RaftNode.timestamp)
            self.logger.info(f'{self.env.now} Входящий запрос прерван')

    def set_new_timeout_event(self):
        self.election_timeout = self.get_election_time()
        #write_to_file(f'{self.name} следующий таймаут: {self.env.now + self.election_timeout}', self.env, RaftNode.timestamp)
        self.logger.info(f'{self.env.now} Следующий таймаут: {self.env.now + self.election_timeout}')
        if self.timeout_proc is not None and self.timeout_proc.is_alive:
            self.timeout_proc.interrupt()
        self.timeout_proc = self.env.process(self.timeout_process())

    def interrupt_timeout_event(self):
        if self.timeout_proc is not None and self.timeout_proc.is_alive:
            self.timeout_proc.interrupt()

    def set_new_voted_timeout_event(self):
        self.nodes_voted_timeout_event = self.env.timeout(RaftNode.voting_timeout)
        self.nodes_voted_timeout_event.callbacks.append(self.nodes_voted_timeout_callback)

    def set_new_heartbit_event(self, time=None):
        if time is None:
            time = RaftNode.heartbeat
        if self.heartbit_proc is not None and self.heartbit_proc.is_alive:
            self.heartbit_proc.interrupt()
        self.heartbit_proc = self.env.process(self.heartbit_process(time=time))

    def set_new_entry_event(self, leader):
        if self.entry_proc is not None and self.entry_proc.is_alive and self.entry_proc != self.env.active_process:
            self.entry_proc.interrupt()
        self.entry_proc = self.env.process(self.entry_process(leader))


def run(env, network_manager, settings, until=300):
    timestamp = setup_logging()
    general_settings = settings['general']
    nodes_settings = settings['nodes']
    RaftNode.heartbeat = general_settings['heartbeat']
    RaftNode.election_timeout = general_settings['election_timeout']
    RaftNode.sleeping_time_max = general_settings['sleeping_time_max']
    RaftNode.sleeping_time_min = general_settings['sleeping_time_min']
    #доделать voting timeout
    RaftNode.timestamp = timestamp
    RaftNode.processed_entries = 0
    env = env
    num_nodes = general_settings['num_nodes']
    print(num_nodes)
    metrics = Metrics(env, num_nodes=num_nodes, timestamp=RaftNode.timestamp)
    RaftNode.network_manager = network_manager
    leader_node = 0
    cluster = [RaftNode(env, f"Узел {i}", [], metrics, i, nodes_settings[i]) for i in range(num_nodes)]
    cluster[leader_node].state = LEADER
    cluster[leader_node].set_new_entry_event(cluster[0])
    cluster[leader_node].set_new_heartbit_event()

    for node in cluster:
        node.cluster = cluster
        node.leader = cluster[leader_node]
    env.run(until=until)
    return metrics.calculate_metrics(RaftNode.processed_entries, mode='text'), timestamp
