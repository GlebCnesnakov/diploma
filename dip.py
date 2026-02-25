import simpy
import random
import time
import os


FOLLOWER = 'follower'
CANDIDATE = 'candidate'
LEADER = 'leader'
ELECTION_TIMEOUT = 5
VOTE_PROBABILTY = 0.6

class RaftNode:
    def __init__(self, env, name, cluster):
        self.env = env
        self.name = name
        self.cluster = cluster
        self.state = FOLLOWER
        self.vote_count = 0
        self.election_timeout = ELECTION_TIMEOUT
        self.last_heard_from_leader = env.now
        self.election_process = env.process(self.run())
        self.voted = False
    
    def run(self):
        while True:
            if self.state == FOLLOWER:
                yield self.env.timeout(self.election_timeout)
                if self.env.now - self.last_heard_from_leader > self.election_timeout:
                    write_to_file(f"{self.name} не получил ответа и переходит в состояние кандидата.", self.env)
                    self.state = CANDIDATE
                    self.start_election()
            elif self.state == CANDIDATE:
                yield self.env.timeout(random.uniform(1, 2))
                if self.vote_count > len(self.cluster) // 2:
                    self.state = LEADER
                    write_to_file(f"{self.name} стал лидером", self.env)
                    self.free_nodes_votes()
                    self.start_replication()
                else:
                    self.state = FOLLOWER
                    write_to_file(f"{self.name} стал фолловером после неудачных выборов.", self.env)
            elif self.state == LEADER:
                yield self.env.timeout(random.uniform(1, 2))
                if (random.random() < 0.05): # лидер может молчать
                    silence_time = random.uniform(self.election_timeout - 1, self.election_timeout + 2)
                    write_to_file(f'Лидер молчит {silence_time + 1} ед. времени', self.env)
                    self.state = FOLLOWER # лидер стал фоловером
                    yield self.env.timeout(silence_time) # время молчания лидера
                else:
                    self.start_replication()
                    #self.replicate_logs()

    def start_election(self):
        self.vote_count = 1
        for node in self.cluster:
            if node != self:
                node.receive_vote_request(self)

    def free_nodes_votes(self):
        for node in self.cluster:
            node.voted = False

    def receive_vote_request(self, candidate):
        if self.state == FOLLOWER:
            if random.random() < VOTE_PROBABILTY and not self.voted:
                write_to_file(f"{self.name} голосует за {candidate.name}.", self.env)
                candidate.vote_count += 1
                self.last_heard_from_leader = self.env.now
                self.voted = True

    def start_replication(self):
        write_to_file(f'{self.name} начал отправлять конфигурацию', self.env)
        
        for node in self.cluster:
            if node != self:
                node.replicate_conf()

    def replicate_conf(self):

        write_to_file(f"{self.name} принимает конфигурацию.", self.env)
        self.receive_heartbeat() 
    
    def receive_heartbeat(self):
        self.last_heard_from_leader = self.env.now

def write_to_file(text, env):
    with open('results.txt', mode='a') as f:
        f.write(f'\n{env.now}: {text}')



def run_simulation():
    env = simpy.Environment()
    cluster = [RaftNode(env, f"Node{i}", []) for i in range(5)]

    for node in cluster:
        node.cluster = cluster
    env.run(until=300)
    clear_file()

def clear_file():
    input('Enter:')
    with open('results.txt', 'w') as f:
        f.write('')

run_simulation()