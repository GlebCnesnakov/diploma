import sys
from config_window import NetworkConfigWindow
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QTextEdit
)
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np


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
        self.runs_input.setValue(10)
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

        self.figure1, self.ax1 = plt.subplots(figsize=(5,4))
        self.canvas1 = FigureCanvas(self.figure1)
        graphs_layout.addWidget(self.canvas1, 1)

        self.figure2, self.ax2 = plt.subplots(figsize=(5,4))
        self.canvas2 = FigureCanvas(self.figure2)
        graphs_layout.addWidget(self.canvas2, 1)

        main_layout.addLayout(graphs_layout)

        central_widget.setLayout(main_layout)

        self.network_config_window = NetworkConfigWindow()

    def open_config(self):
        self.network_config_window.show()

    def run_simulation(self):
        runs = self.runs_input.value()
        nodes = 4

        commit_ratio = np.random.rand(runs)
        disconnects = np.random.randint(0, 5, size=(runs, nodes))
        leader_elections = np.random.randint(0, 3, size=(runs, nodes))
        sync_requests = np.random.randint(0, 5, size=(runs, nodes))
        downtime = np.random.rand(runs, nodes) * 100
        election_duration = np.random.rand(runs) * 20
        total_duration = 100 * np.ones(runs)
        active_time_ratio = np.random.rand(runs, nodes)

        issued = np.random.randint(50, 100, size=(runs, nodes))
        committed = (issued * (0.7 + 0.3*np.random.rand(runs, nodes))).astype(int)

        self.metric_fields["1. Среднее зафиксировано/издано"].setText(f"{commit_ratio.mean():.3f}")
        self.metric_fields["2. Среднее количество отключений"].setText(f"{disconnects.mean():.3f}")
        self.metric_fields["3. Медиана избраний лидером"].setText(f"{np.median(leader_elections, axis=0)}")
        self.metric_fields["4. Медиана отключений"].setText(f"{np.median(disconnects, axis=0)}")
        self.metric_fields["5. Медиана запросов на синхронизацию"].setText(f"{np.median(sync_requests, axis=0)}")
        self.metric_fields["6. Средняя продолжительность отключения"].setText(f"{downtime.mean(axis=0)}")
        self.metric_fields["7. Средняя продолжительность выборов\n к общей продолжительности"].setText(f"{(election_duration/total_duration).mean():.3f}")
        self.metric_fields["8. Доля активного времени"].setText(f"{active_time_ratio.mean(axis=0)}")

        self.ax1.clear()
        self.ax1.plot(range(runs), commit_ratio, marker='o')
        self.ax1.set_title("Зафиксировано/Издано от прогона")
        self.ax1.set_xlabel("Прогон")
        self.ax1.set_ylabel("Доля зафиксировано/издано")
        self.ax1.grid(True)
        self.canvas1.draw()

        self.ax2.clear()
        for i in range(runs):
            self.ax2.plot(range(nodes), issued[i], color='red', linewidth=1, alpha=0.6, label='Издано' if i==0 else "")
            self.ax2.plot(range(nodes), committed[i], color='blue', linewidth=1, alpha=0.6, label='Зафиксировано' if i==0 else "")
        self.ax2.set_title("Издано и Зафиксировано от времени")
        self.ax2.set_xlabel("Узел")
        self.ax2.set_ylabel("Количество записей")
        self.ax2.set_xticks(range(nodes))
        self.ax2.set_xticklabels([f"Узел {i}" for i in range(nodes)])
        self.ax2.grid(True)
        self.ax2.legend()
        self.canvas2.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec_())