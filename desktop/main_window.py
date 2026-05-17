import sys
from config_window import NetworkConfigWindow
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QTextEdit, QComboBox
)
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np
import simpy
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)
print(dir(__import__(__name__)))
from model.network import NetworkManager
from model.algo import run
#from model.run import Run
#import model.raft
import json
import datetime


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Моделирование сети")
        self.setMinimumSize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        self.run_btn = QPushButton("Запуск")
        self.run_btn.clicked.connect(self.run_simulation)
        top_layout.addWidget(self.run_btn)

        top_layout.addWidget(QLabel("Количество прогонов:"))
        self.runs_input = QSpinBox()
        self.runs_input.setMinimum(1)
        self.runs_input.setMaximum(1000)
        self.runs_input.setValue(2)
        top_layout.addWidget(self.runs_input)

        self.config_btn = QPushButton("Конфигурация сети")
        self.config_btn.clicked.connect(self.open_config)
        top_layout.addWidget(self.config_btn)
        main_layout.addLayout(top_layout)

        metrics_layout = QHBoxLayout()
        metric_names = [
            "1. Среднее зафиксировано/издано",
            "2. Среднее количество отключений",
            "3. Медиана избраний лидером",
            "4. Медиана отключений",
            "5. Медиана запросов на синхронизацию",
            "6. Средняя продолжительность отключения",
            "7. Средняя продолжительность выборов\n к общей продолжительности",
            "8. Доля активного времени"
        ]

        self.metric_fields = {}

        for col in range(4):
            col_layout = QHBoxLayout()
            label = QLabel(metric_names[col])
            col_layout.addWidget(label)

            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setStyleSheet("font-size: 14px;")
            text_edit.setFixedHeight(60)
            text_edit.setFontWeight(QFont.Bold)
            text_edit.setFixedWidth(150)
            col_layout.addWidget(text_edit)
            self.metric_fields[metric_names[col]] = text_edit
            metrics_layout.addLayout(col_layout)
        main_layout.addLayout(metrics_layout)
        main_layout.addSpacing(20)
        metrics_layout = QHBoxLayout()

        for col in range(4, 8):
            col_layout = QHBoxLayout()
            label = QLabel(metric_names[col])
            col_layout.addWidget(label)

            text_edit = QTextEdit()
            text_edit.setStyleSheet("font-size: 14px;")
            text_edit.setFontWeight(QFont.Bold)
            text_edit.setReadOnly(True) 
            text_edit.setFixedHeight(60)
            text_edit.setFixedWidth(150)
            col_layout.addWidget(text_edit)
            self.metric_fields[metric_names[col]] = text_edit
            metrics_layout.addLayout(col_layout)
        main_layout.addLayout(metrics_layout)
        main_layout.addSpacing(20)

        graphs_layout = QHBoxLayout()

        # Первый график
        self.figure1, self.ax1 = plt.subplots(figsize=(5, 4))
        self.canvas1 = FigureCanvas(self.figure1)
        graphs_layout.addWidget(self.canvas1, 1)

        # Вертикальный layout для комбобокса + второго графика
        right_layout = QVBoxLayout()

        self.node_selector = QComboBox()
        right_layout.addWidget(self.node_selector)  # комбобокс сверху

        self.figure2, self.ax2 = plt.subplots(figsize=(5, 4))
        self.canvas2 = FigureCanvas(self.figure2)
        right_layout.addWidget(self.canvas2, 1)  # график под комбобоксом

        # Добавляем вертикальный layout в горизонтальный
        graphs_layout.addLayout(right_layout, 1)

        main_layout.addLayout(graphs_layout)
        central_widget.setLayout(main_layout)

        self.env = simpy.Environment()
        self.network_manager = NetworkManager(env=self.env, num_nodes=4, min_delay=0.001, max_delay=0.5)

        self.network_config_window = NetworkConfigWindow(network_manager=self.network_manager)

    def open_config(self):
        self.network_config_window.show()
    
    def save_results(self, results: dict, timestamp: datetime):
        current_dir = os.path.dirname(os.path.abspath(__file__))  # dip/desktop

        # Папка results на одном уровне с desktop
        project_root = os.path.join(current_dir, '..')          # dip/
        results_dir = os.path.join(project_root, 'results')     # dip/results
        file_path = os.path.join(results_dir, f'results {timestamp}.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4)

    def run_simulation(self):
        runs = self.runs_input.value()
        until = 300

        settings = self.network_config_window.get_settings()
        nodes = settings['general']['num_nodes']
        accuracy = 0
        accuracy_runs = []
        common_outages = 0
        elected_nodes = [[] for _ in range(nodes)]
        outages = [[] for _ in range(nodes)]
        
        syn = [[] for _ in range(nodes)]
        shutdown_time = [0 for _ in range(nodes)]
        times_issued = []
        times_committed = []
        values_issued = []
        values_committed = []
        election_duration = 0
        shutdown_time_sum = 0

        for i in range(runs):
            print(f'запуск {i} {self.network_manager.num_nodes}')
            result, timestamp = run(self.env, network_manager=self.network_manager, until=until, settings=settings)
            print(result)
            accuracy += result['accuracy']
            accuracy_runs.append(result['accuracy'])
            common_outages += result['common_outages']
            election_duration += result['election_time']
            times_committed.append(result['times_committed'])
            times_issued.append(result['times_requested'])
            values_committed.append(result['values_committed'])
            values_issued.append(result['values_requested'])
            #shutdown_time_sum += result['shutdown_time']
            for i in range(nodes):
                elected_nodes[i].append(result['elected_nodes'][i])
                outages[i].append(result['outages'][i])
                syn[i].append(result['syn_req'][i])
                shutdown_time[i] += result['shutdown_time'][i]
                shutdown_time_sum += result['shutdown_time'][i]
            self.env = simpy.Environment()
            self.network_manager.env = self.env

        avg_acc = round(accuracy / runs, 3)
        avg_am_outages = round(common_outages / runs, 3)
        med_elected = [round(float(np.mean(elected_nodes[i], axis=0)), 3) for i in range(nodes)]
        med_outages = [round(float(np.mean(outages[i], axis=0)), 3) for i in range(nodes)]
        med_syn = [round(float(np.mean(syn[i], axis=0)), 3) for i in range(nodes)]
        #avg_shut = [round(shutdown_time[i] / runs, 3) for i in range(nodes)]
        avg_shut = round(sum(shutdown_time) / nodes / runs, 3)
        avg_dur_until = round((election_duration / runs / until), 3)
        active_time = [round((1 - (shutdown_time[i] / runs / until)), 3) for i in range(nodes)]

        results_to_save = {
            'average_accuracy': avg_acc,
            'average_amount_of_outages': avg_am_outages,
            'median_elected_of_node': med_elected,
            'median_outages_of_node': med_outages,
            'median_syn_of_node': med_syn,
            'average_shut_of_node': avg_shut,
            'average_duration_until': avg_dur_until,
            'active_time': active_time
        }

        self.metric_fields["1. Среднее зафиксировано/издано"].setText(f"{avg_acc}")
        self.metric_fields["2. Среднее количество отключений"].setText(f"{avg_am_outages}")
        self.metric_fields["3. Медиана избраний лидером"].setText(f"{med_elected}")
        self.metric_fields["4. Медиана отключений"].setText(f"{med_outages}")
        self.metric_fields["5. Медиана запросов на синхронизацию"].setText(f"{med_syn}")
        self.metric_fields["6. Средняя продолжительность отключения"].setText(f"{avg_shut}")
        self.metric_fields["7. Средняя продолжительность выборов\n к общей продолжительности"].setText(f"{avg_dur_until}")
        self.metric_fields["8. Доля активного времени"].setText(f"{active_time}")

        self.ax1.clear()
        self.ax1.plot(range(runs), accuracy_runs, marker='o')
        self.ax1.set_title("Зафиксировано/Издано от прогона")
        self.ax1.set_xlabel("Прогон")
        self.ax1.set_ylabel("Доля зафиксировано/издано")
        self.ax1.grid(True)
        self.canvas1.draw()


        def update_node_plot():
            iter = self.node_selector.currentIndex()
            self.ax2.clear()

            self.ax2.plot(
                times_issued[iter], 
                values_issued[iter], 
                color='red', linewidth=1.5, alpha=0.7, label='Издано'
            )
            self.ax2.plot(
                times_committed[iter], 
                values_committed[iter], 
                color='blue', linewidth=1.5, alpha=0.7, label='Зафиксировано'
            )

            self.ax2.set_title(f"Издано и Зафиксировано от времени — Прогон {iter}")
            self.ax2.set_xlabel("Время")
            self.ax2.set_ylabel("Количество записей")
            self.ax2.set_xlim(0, until)
            self.ax2.grid(True)
            self.ax2.legend()
            self.canvas2.draw()
        self.node_selector.clear()
        self.node_selector.addItems([f"Прогон {i}" for i in range(runs)])
        self.node_selector.currentIndexChanged.connect(update_node_plot)
        update_node_plot()
        self.save_results(results_to_save, timestamp)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec_())