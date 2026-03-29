import simpy
import random
from typing import Union, NoReturn, List, Generator
from metrics import Metrics


FOLLOWER = 'follower'
CANDIDATE = 'candidate'
LEADER = 'leader'
ELECTION_TIMEOUT = 5
VOTING_TIMEOUT = 2
NODE_PROBABILITY_FAILURE = 0.05
HEARTBIT = 5
LAMBDA = 0.1
EXPO_TIME = 1
UNIFORM_TIME = 0
UNIFORM_A = 1
UNIFORM_B = 2
ELECTION_MIN = HEARTBIT + 0.1
ELECTION_MAX = ELECTION_MIN + 1
SLEEPING_TIME_MIN = 4
SLEEPING_TIME_MAX = 7


PROCESSED_ENTRIES = 0


def get_sleeping_time() -> float:
    return random.uniform(SLEEPING_TIME_MIN, SLEEPING_TIME_MAX)


def get_election_time() -> float:
    return random.uniform(ELECTION_MIN, ELECTION_MAX)


def get_next_request_time() -> Union[NoReturn, float]:
    if EXPO_TIME:
        return random.expovariate(lambd=LAMBDA)
    if UNIFORM_TIME:
        return random.uniform(UNIFORM_A, UNIFORM_B)
    raise ValueError("Time error")


class RaftNode:
    processed_entries: int = 0  # обработанные запросы
    #leader: RaftNode

    def __init__(self, env: simpy.Environment, name: str, cluster: List, metrics: Metrics):
        env.process(self.run())
        self.metrics: Metrics = metrics
        self.timeout_proc: simpy.Process = None
        self.heartbit_proc: simpy.Process = None
        self.entry_proc: simpy.Process = None
        self.env: simpy.Environment = env
        self.name: str = name
        self.cluster: List = cluster

        self.state: str = FOLLOWER
        self.vote_count: int = 0
        self.election_timeout: float = get_election_time()
        self.last_heard_from_leader: float = env.now
        #self.election_process: simpy.Process = env.process(self.run())
        self.voted: bool = False
        self.index: int = 0
        self.term: int = 0
        
        self.timeout_event: simpy.Event
        self.requested_vote_event: simpy.Event = self.env.event()
        self.requested_vote_event.callbacks.append(self.vote_callback)
        #self.requested_vote_event.callbacks.append(self.set_new_timeout_event)  # новый таймаут когда проголосовал
        self.ack_log_event: simpy.Event = self.env.event()  # запрос индексации
        self.ack_log_event.callbacks.append(self.ack_log_callback)
        #self.ack_log_event.callbacks.append(self.set_new_timeout_event)  # новый таймаут когда принял запись
        self.commit_log_event: simpy.Event = self.env.event()  # запрос коммита
        self.commit_log_event.callbacks.append(self.commit_log_callback)
        #self.commit_log_event.callbacks.append(self.set_new_timeout_event)  # новый таймаут когда закомитил запись
        self.nodes_voted_timeout_event: simpy.Timeout
        self.heartbit_event: simpy.Timeout
        self.entry_event: simpy.Timeout
        self.is_shutdown: bool = False  # узел не раб
        self.ack_count: int = 0  # число узлов, подтвердивших запись
        self.commited_count: int = 0  # число узлов, закоммитивших запись
        self.leader: RaftNode

        self.entries = 0

    def run(self) -> Generator:
        while True:
            if random.random() <= NODE_PROBABILITY_FAILURE:
                sl = get_sleeping_time()
                write_to_file(f'{self.name} заснул на {sl}', self.env)
                self.is_shutdown = True
                sleeping_timeout = self.env.timeout(sl)
                # if self.state == LEADER:
                #     yield self.env.all_of([self.entry_event, sleeping_timeout]) # если приходит запрос лидер почему то просыпается
                # else:
                yield sleeping_timeout
                self.is_shutdown = False
            if self.state == FOLLOWER:
                write_to_file(f'{self.name} фоловер', self.env)
                self.set_new_timeout_event()
                # фоловер ждет какое то событие(добавить ли синхронизацию?)
                #write_to_file(f'{self.name} {self.election_timeout}', self.env)
                result = yield self.env.any_of([self.timeout_proc, self.ack_log_event, self.commit_log_event, self.requested_vote_event]) #возвращает словарь с тригер событиями?
            elif self.state == CANDIDATE:  # передать кандидата в ивент
                # узел становится кандидатом, отсылает запросы, те обновляют таймаут, таймаут должен обновлятся каждый раз
                # если не получил большинство, замолкает, выбирается другой кандидат, если не получил большинство замолкает
                # если получил половину, начинаем новый терм?
                self.set_new_voted_timeout_event()
                self.term += 1
                write_to_file(f'{self.name} кандидат',  self.env)
                # сделать события окончания голосования за кандидата. ждать any of с хартбитом от лидера, вдруг проснется.
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

    def heartbit_callback(self) -> None:
        if not self.is_shutdown:
            write_to_file(f'{self.name} посылает heartbit',  self.env)
            #if self.entries > 0:  # посылаем запросы группой, если пришло несколько за хартбит, посылаем их разом
                #self.index += 1
            for i in self.cluster:
                if i != self:
                    i.ack_log_event.succeed(value=self)
            self.env.process(self._process_ack())
        #else:
            #self.set_new_heartbit_event()
        # write_to_file(f'Лидер {self.name}, запросов:{self.entries} подтверждений: {self.ack_count}', self.env)
        # if self.entries > 0 and self.ack_count > len(self.cluster) // 2:  # отделить комит
        #     write_to_file(f'{self.name} посылает комиты',  self.env)
        #     for i in self.cluster:
        #         if i != self:
        #             i.commit_log_event.succeed(value=self)
        #     self.entries -= 1
        #     RaftNode.processed_entries += 1  # считаем запрос обработанным
        # self.ack_count = 0
        # self.set_new_heartbit_event()

    def _process_ack(self):
        yield self.env.timeout(0)
        write_to_file(f'Лидер {self.name}, запросов:{self.entries} подтверждений: {self.ack_count}', self.env)
        if self.entries > 0:
            if self.ack_count > len(self.cluster) // 2:  # подтвердило большинство
                write_to_file(f'{self.name} посылает комиты',  self.env)
                self.index += self.entries  # лидер фиксирует запись у себя
                for i in self.cluster:
                    if i != self:
                        i.commit_log_event.succeed(value=self)
                #self.entries -= 1
                RaftNode.processed_entries += self.entries  # считаем запрос закомиченым
                self.entries = 0
            else:
                write_to_file('Запись не подтвердилась большинством', self.env)
        write_to_file(f'Зафиксированных записей: {RaftNode.processed_entries}', self.env)
        write_to_file(f'Общее количество записей: {self.metrics.processed_entries}', self.env)
        self.ack_count = 0
        #self.set_new_heartbit_event()

    def entry_callback(self, leader) -> None:
        #leader = event.value
        leader.entries += 1
        write_to_file(f'Лидер {leader.name} принял запрос, необработанных записей: {self.entries}',  leader.env)
        self.metrics.processed_entries += 1
        #leader.index += 1
        #leader.set_new_entry_event(leader)

    def nodes_voted_timeout_callback(self, event) -> None:
        write_to_file(f'{self.name} проверка результатов выборов',  self.env)
        if self.vote_count > len(self.cluster) // 2:
            write_to_file(f'{self.name} стал лидером',  self.env)
            self.state = LEADER
            self.set_new_heartbit_event()
            self.set_new_entry_event(self)
        else:
            self.state = FOLLOWER
            write_to_file(f'{self.name} проиграл выборы и стал фоловером',  self.env)
        self.vote_count = 0

    def vote_callback(self, event) -> None:
        candidate = event.value
        #self.set_new_timeout_event()  # обновили таймаут
        self.set_new_vote_event()  # обновили возможность голосовать 
        if not self.voted and self.status != LEADER:
            write_to_file(f'{self.name} голосует',  self.env)
            if candidate.term == self.term and candidate.index >= self.index or candidate.term > self.term:
                candidate.vote_count += 1  # проголосовали за кандидата
                self.voted = True
                write_to_file(f'{self.name} проголосовал за {candidate.name}',  self.env)
                if candidate.term > self.term:
                    self.term += 1
                    write_to_file(f'{self.name} увеличил терм из-за кандидата',  self.env)

    def timeout_callback(self, event=None) -> None:
        if not self.is_shutdown:
            write_to_file(f'{self.name} таймаут колбек. Последний хартбит от лидера: {self.last_heard_from_leader}', self.env)
            #if self.env.now - self.last_heard_from_leader > self.election_timeout:
            write_to_file(f"{self.name} не получил ответа и переходит в состояние кандидата.", self.env)
            self.state = CANDIDATE

    def ack_log_callback(self, event) -> None:
        write_to_file(f'К {self.name} пришел запрос ack', self.env)
        self.leader = event.value
        if self.state == CANDIDATE and self.term < self.leader.term:
            self.state = FOLLOWER
        if not self.is_shutdown and not self.leader.is_shutdown and self.term <= self.leader.term: # что с индексом? если терм принимающего выше?
            if self.state == LEADER:  # если получили терм поновее(или такой же?) зануляем запросы лидера, передаем их новому, отменяем хартбиты и entry
                self.leader.entries = self.entries
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

            self.state = FOLLOWER
            if self.leader.entries > 0 and self.index != self.leader.index:  # фоловер не синхронизирован
                write_to_file(f'{self.name} не синхронизирован с {self.leader.name}, терм лидера {self.leader.term}, индекс лидера {self.leader.index}, терм узла {self.term} индекс узла {self.index}',  self.env)
                self.index = self.leader.index  # синхронизировали(доработка)

            if self.leader.entries > 0:  # если это не простой хартбит
                self.leader.ack_count += 1
                self.voted = False  # после выборов нужно установить в False
                self.vote_count = 0
                #self.index += 1
                write_to_file(f'{self.name} подтвердил запрос {self.leader.name}, терм лидера {self.leader.term}, индекс лидера {self.leader.index}, терм узла {self.term} индекс узла {self.index}',  self.env)
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

    def request_votes(self) -> None:
        write_to_file(f'{self.name} начал собирать голоса', self.env)
        self.vote_count = 1  # голосуем за себя
        self.voted = True
        for node in self.cluster:  # посылаем запросы
            if node != self and not node.is_shutdown:
                node.set_new_vote_event()
                node.requested_vote_event.succeed(value=self)

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
            write_to_file(f'{self.name} таймаут прерван в {self.env.now}', self.env)

    def heartbit_process(self):
        try:
            yield self.env.timeout(HEARTBIT)
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

        # self.timeout_event = self.env.timeout(self.election_timeout)
        # self.timeout_event.callbacks.append(self.timeout_callback)

    def set_new_voted_timeout_event(self):
        self.nodes_voted_timeout_event = self.env.timeout(VOTING_TIMEOUT)
        self.nodes_voted_timeout_event.callbacks.append(self.nodes_voted_timeout_callback)

    def set_new_heartbit_event(self):
        if self.heartbit_proc is not None and self.heartbit_proc.is_alive:
            self.heartbit_proc.interrupt()
        self.heartbit_proc = self.env.process(self.heartbit_process())
        # self.heartbit_event = self.env.timeout(HEARTBIT)
        # self.heartbit_event.callbacks.append(self.heartbit_callback)

    def set_new_entry_event(self, leader):
        if self.entry_proc is not None and self.entry_proc.is_alive and self.entry_proc != self.env.active_process:
            self.entry_proc.interrupt()
        self.entry_proc = self.env.process(self.entry_process(leader))
        # self.entry_event = self.env.timeout(get_next_request_time(), value=leader)
        # self.entry_event.callbacks.append(self.entry_callback)


def write_to_file(text, env):
    with open('results.txt', mode='a') as f:
        f.write(f'\n{env.now}: {text}')


def run_simulation():
    env = simpy.Environment()
    metrics = Metrics()
    cluster = [RaftNode(env, f"Узел {i}", [], metrics) for i in range(5)]
    cluster[0].state = LEADER
    cluster[0].set_new_entry_event(cluster[0])
    cluster[0].set_new_heartbit_event()

    for node in cluster:
        node.cluster = cluster
        node.leader = cluster[0]
    env.run(until=300)
    write_to_file(f'Зафиксировано/Издано {RaftNode.processed_entries / metrics.processed_entries}', env)
    clear_file()


def clear_file():
    input('Enter:')
    with open('results.txt', 'w') as f:
        f.write('')


run_simulation()
