from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QComboBox, QMessageBox
)
import random

class NetworkDelayWindow(QWidget):
    def __init__(self, network, num_nodes=4):
        super().__init__()
        self.setWindowTitle("Настройка сетевых задержек")
        self.setMinimumSize(400, 200)
        self.num_nodes = num_nodes
        self.network = network

        self.layout = QVBoxLayout()
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Минимальная задержка (ms):"))
        self.min_delay_input = QLineEdit("10")
        range_layout.addWidget(self.min_delay_input)
        range_layout.addWidget(QLabel("Максимальная задержка (ms):"))
        self.max_delay_input = QLineEdit("100")
        range_layout.addWidget(self.max_delay_input)
        self.layout.addLayout(range_layout)

        node_layout = QHBoxLayout()
        self.node_from_combo = QComboBox()
        self.node_from_combo.addItems([f"Узел {i}" for i in range(num_nodes)])
        self.node_from_combo.currentIndexChanged.connect(self.set_time)
        self.node_to_combo = QComboBox()
        self.node_to_combo.addItems([f"Узел {i}" for i in range(num_nodes)])
        self.node_to_combo.currentIndexChanged.connect(self.set_time)
        self.delay_input = QLineEdit()
        self.delay_input.setPlaceholderText("Задержка между узлами (ms)")
        self.delay_input.setText(str(self.network.get_delay(self.node_from_combo.currentIndex(), self.node_to_combo.currentIndex())))

        node_layout.addWidget(QLabel("От:"))
        node_layout.addWidget(self.node_from_combo)
        node_layout.addWidget(QLabel("До:"))
        node_layout.addWidget(self.node_to_combo)
        self.layout.addLayout(node_layout)
        self.layout.addWidget(self.delay_input)

        apply_btn = QPushButton("Применить задержку")
        apply_btn.clicked.connect(self.apply_delay)
        self.layout.addWidget(apply_btn)

        self.setLayout(self.layout)

    def set_time(self):
        try:
            self.delay_input.setText(str(self.network.get_delay(self.node_from_combo.currentIndex(), self.node_to_combo.currentIndex())))
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Не удалось отобразить задержку:\n{e}")
            msg.exec_()

    def apply_delay(self):
        from_idx = self.node_from_combo.currentIndex()
        to_idx = self.node_to_combo.currentIndex()
        try:
            min_delay = float(self.min_delay_input.text())
            max_delay = float(self.max_delay_input.text())
            self.network.min_delay = min_delay
            self.network.max_delay = max_delay
            self.network.fill_delays()
            delay = float(self.delay_input.text())
            self.network.set_delay(from_idx, to_idx, delay)
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Не удалось задать задержки:\n{e}")
            msg.exec_()
        self.hide()