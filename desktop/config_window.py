from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QComboBox, QLineEdit, QRadioButton, QGroupBox
)


class NetworkConfigWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Настройки сети")
        self.setMinimumSize(600, 700)

        self.layout = QVBoxLayout()

        # Heartbeat
        hb_layout = QHBoxLayout()
        hb_layout.addWidget(QLabel("Heartbeat для лидера:"))
        self.heartbeat_input = QLineEdit("1.0")
        hb_layout.addWidget(self.heartbeat_input)
        self.layout.addLayout(hb_layout)

        # Кол-во узлов
        node_layout = QHBoxLayout()
        node_layout.addWidget(QLabel("Количество узлов:"))
        self.nodes_input = QSpinBox()
        self.nodes_input.setMinimum(1)
        self.nodes_input.setValue(4)
        self.nodes_input.valueChanged.connect(self.update_node_combo)
        node_layout.addWidget(self.nodes_input)
        self.layout.addLayout(node_layout)

        # Кнопки пресетов
        preset_layout = QHBoxLayout()
        self.use_preset_btn = QPushButton("Использовать пресет")
        self.create_preset_btn = QPushButton("Создать пресет")
        self.delays_btn = QPushButton("Задержки")
        self.reset_btn = QPushButton("Сбросить")
        preset_layout.addWidget(self.use_preset_btn)
        preset_layout.addWidget(self.create_preset_btn)
        preset_layout.addWidget(self.delays_btn)
        preset_layout.addWidget(self.reset_btn)
        self.layout.addLayout(preset_layout)

        # Выбор узла
        node_select_layout = QHBoxLayout()
        node_select_layout.addWidget(QLabel("Выберите узел:"))
        self.node_combo = QComboBox()
        self.update_node_combo()
        node_select_layout.addWidget(self.node_combo)
        self.layout.addLayout(node_select_layout)

        # Время поступления заявки
        self.create_request_group()
        # Время shutdown
        self.create_shutdown_group()

        # Election timeout
        election_layout = QHBoxLayout()
        election_layout.addWidget(QLabel("election_timeout:"))
        self.election_input = QLineEdit("5.0")
        election_layout.addWidget(self.election_input)
        self.layout.addLayout(election_layout)

        # Sleeping time
        sleeping_layout = QHBoxLayout()
        sleeping_layout.addWidget(QLabel("sleeping_time_min:"))
        self.sleep_min_input = QLineEdit("1.0")
        sleeping_layout.addWidget(self.sleep_min_input)
        sleeping_layout.addWidget(QLabel("sleeping_time_max:"))
        self.sleep_max_input = QLineEdit("3.0")
        sleeping_layout.addWidget(self.sleep_max_input)
        self.layout.addLayout(sleeping_layout)

        self.setLayout(self.layout)

    def update_node_combo(self):
        count = self.nodes_input.value()
        self.node_combo.clear()
        self.node_combo.addItems([f"Узел {i}" for i in range(count)])

    def create_request_group(self):
        group = QGroupBox("Время поступления заявки")
        layout = QHBoxLayout()

        # Случайное время
        random_layout = QVBoxLayout()
        self.req_random_radio = QRadioButton("Случайное время")
        self.req_random_radio.setChecked(True)
        self.req_random_radio.toggled.connect(self.update_request_fields)
        random_layout.addWidget(self.req_random_radio)
        random_layout.addWidget(QLabel("a:"))
        self.req_a_input = QLineEdit("0.0")
        random_layout.addWidget(self.req_a_input)
        random_layout.addWidget(QLabel("b:"))
        self.req_b_input = QLineEdit("10.0")
        random_layout.addWidget(self.req_b_input)

        # Экспоненциальное
        exp_layout = QVBoxLayout()
        self.req_exp_radio = QRadioButton("Экспоненциальное")
        self.req_exp_radio.toggled.connect(self.update_request_fields)
        exp_layout.addWidget(self.req_exp_radio)
        exp_layout.addWidget(QLabel("lambda:"))
        self.req_lambda_input = QLineEdit("1.0")
        exp_layout.addWidget(self.req_lambda_input)

        layout.addLayout(random_layout)
        layout.addLayout(exp_layout)
        group.setLayout(layout)
        self.layout.addWidget(group)
        self.update_request_fields()

    def update_request_fields(self):
        self.req_a_input.setEnabled(self.req_random_radio.isChecked())
        self.req_b_input.setEnabled(self.req_random_radio.isChecked())
        self.req_lambda_input.setEnabled(self.req_exp_radio.isChecked())

    def create_shutdown_group(self):
        group = QGroupBox("Время shutdown")
        layout = QHBoxLayout()

        # Случайное время
        random_layout = QVBoxLayout()
        self.shutdown_random_radio = QRadioButton("Случайное время")
        self.shutdown_random_radio.setChecked(True)
        self.shutdown_random_radio.toggled.connect(self.update_shutdown_fields)
        random_layout.addWidget(self.shutdown_random_radio)
        random_layout.addWidget(QLabel("a:"))
        self.shutdown_a_input = QLineEdit("0.0")
        random_layout.addWidget(self.shutdown_a_input)
        random_layout.addWidget(QLabel("b:"))
        self.shutdown_b_input = QLineEdit("10.0")
        random_layout.addWidget(self.shutdown_b_input)

        # Экспоненциальное
        exp_layout = QVBoxLayout()
        self.shutdown_exp_radio = QRadioButton("Экспоненциальное")
        self.shutdown_exp_radio.toggled.connect(self.update_shutdown_fields)
        exp_layout.addWidget(self.shutdown_exp_radio)
        exp_layout.addWidget(QLabel("lambda:"))
        self.shutdown_lambda_input = QLineEdit("1.0")
        exp_layout.addWidget(self.shutdown_lambda_input)

        layout.addLayout(random_layout)
        layout.addLayout(exp_layout)
        group.setLayout(layout)
        self.layout.addWidget(group)
        self.update_shutdown_fields()

    def update_shutdown_fields(self):
        self.shutdown_a_input.setEnabled(self.shutdown_random_radio.isChecked())
        self.shutdown_b_input.setEnabled(self.shutdown_random_radio.isChecked())
        self.shutdown_lambda_input.setEnabled(self.shutdown_exp_radio.isChecked())