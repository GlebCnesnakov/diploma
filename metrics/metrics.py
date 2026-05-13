import logging


def write_to_file(text, env, timestamp):
    ...
    #with open(f'logs/log {timestamp}.txt', 'a') as f:
        #f.write(f'\n{round(env.now, 3)}: {text}')


class Metrics:
    def __init__(self, env,  timestamp, num_nodes=4):
        self.timestamp = timestamp
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
        self.times_committed = []
        self.values_committed = []
        self.times_requested = []
        self.values_requested = []
        self.logger = logging.getLogger(__name__)
    
    def add_values_committed(self, value):
        if (len(self.values_committed) > 0):
            self.values_committed.append(self.values_committed[len(self.values_committed) - 1] + value)
        else:
            self.values_committed.append(value)

    def add_values_requested(self):
        if (len(self.values_requested) > 0):
            self.values_requested.append(self.values_requested[len(self.values_requested) - 1] + 1)
        else:
            self.values_requested.append(1)

    def get_times_committed(self):
        return self.times_committed
    
    def get_times_requested(self):
        return self.times_requested
    
    def get_values_requested(self):
        return self.values_requested
    
    def get_values_committed(self):
        return self.values_committed

    def get_accuracy(self, served_entries, mode='text'):
        if mode == 'text':
            #write_to_file(f'\nЗафиксировано/Издано: {served_entries / self.processed_entries }\n', self.env, self.timestamp)
            self.logger.info(f'\nЗафиксировано/Издано: {served_entries / self.processed_entries }\n')
        return served_entries / self.processed_entries

    def get_common_outages(self, mode='text'):
        if mode == 'text':
            #write_to_file(f'Общее количество отключений: {self.common_outages}\n', self.env, self.timestamp)
            self.logger.info(f'Общее количество отключений: {self.common_outages}\n')
        return self.common_outages

    def get_elected_nodes(self, mode='text'):
        if mode == 'text':
            #write_to_file(f'Количество избраний лидером каждого узла:\n', self.env, self.timestamp)
            self.logger.info(f'Количество избраний лидером каждого узла:\n')
            for i in range(self.num_nodes):
                #write_to_file(f'Узел {i}: {self.elected_leaders_amount[i]}', self.env, self.timestamp)
                self.logger.info(f'Узел {i}: {self.elected_leaders_amount[i]}')
            #write_to_file('\n', self.env, self.timestamp)
            #self.logger(f'\nЗафиксировано/Издано: {served_entries / self.processed_entries }\n')
        return self.elected_leaders_amount

    def get_outages(self, mode='text'):
        if mode == 'text':
            #write_to_file(f'Количество отключений каждого узла:\n', self.env, self.timestamp)
            self.logger.info(f'Количество отключений каждого узла:\n')
            for i in range(self.num_nodes):
                #write_to_file(f'Узел {i}: {self.outages[i]}', self.env, self.timestamp)
                self.logger.info(f'Узел {i}: {self.outages[i]}')
            #write_to_file('\n', self.env, self.timestamp)
            #self.logger(f'\nЗафиксировано/Издано: {served_entries / self.processed_entries }\n')
        return self.outages

    def get_syn_requests(self, mode='text'):
        if mode == 'text':
            #write_to_file(f'Количество запросов на синхронизацию каждого узла:\n', self.env, self.timestamp)
            self.logger.info(f'Количество запросов на синхронизацию каждого узла:\n')
            for i in range(self.num_nodes):
                #write_to_file(f'Узел {i}: {self.syn_requests[i]}', self.env, self.timestamp)
                self.logger.info(f'Узел {i}: {self.syn_requests[i]}')
            #write_to_file('\n', self.env, self.timestamp)
            #self.logger(f'\nЗафиксировано/Издано: {served_entries / self.processed_entries }\n')
        return self.syn_requests

    def get_shutdown_time(self, mode='text'):
        if mode == 'text':
            #write_to_file(f'Продолжительность отключения каждого узла:\n', self.env, self.timestamp)
            self.logger.info(f'Продолжительность отключения каждого узла:\n')
            for i in range(self.num_nodes):
                #write_to_file(f'Узел {i}: {self.shutdown_time[i]}', self.env, self.timestamp)
                self.logger.info(f'Узел {i}: {self.shutdown_time[i]}')
            #write_to_file('\n', self.env, self.timestamp)
            #self.logger(f'\nЗафиксировано/Издано: {served_entries / self.processed_entries }\n')
        return self.shutdown_time

    def get_election_time(self, mode='text'):
        if mode == 'text':
            #write_to_file(f'Продолжительность выборов: {self.election_lasting}\n', self.env, self.timestamp)
            self.logger.info(f'Продолжительность выборов: {self.election_lasting}\n')
        return self.election_lasting


    def calculate_metrics(self, served_entries, mode='text'):
        return {
            'accuracy': self.get_accuracy(served_entries=served_entries, mode=mode),
            'common_outages': self.get_common_outages(mode=mode),
            'elected_nodes': self.get_elected_nodes(mode=mode),
            'outages': self.get_outages(mode=mode),
            'syn_req': self.get_syn_requests(mode=mode),
            'shutdown_time': self.get_shutdown_time(mode=mode),
            'election_time': self.get_election_time(mode=mode),
            'times_committed': self.get_times_committed(),
            'times_requested': self.get_times_requested(),
            'values_committed': self.get_values_committed(),
            'values_requested': self.get_values_requested()
        }
    #ср заф.изд: sum accuracy / N
    #ср кол-во отключений sum common_outages / N
    # медиана избраний med elected nodes
    # медиана отключений [] med outages
    # медиана запросов на синхр [] med syn
    # ср. прод откл[] mean shut_time
    #ср. прод выборов к общей прод. election_time/until
    #доля активного времени узла[] 1 - shut_time / until
    #заф.изд от прогона acc от N
    #заф.изд от времени 

