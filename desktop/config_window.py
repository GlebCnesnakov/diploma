from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QComboBox, QLineEdit, QRadioButton, QGroupBox, QMessageBox, QListWidget
)
import json
import datetime
import os
import simpy
from topology_editor import MainWindow
from PyQt5.QtWidgets import QFileDialog
import math


class NetworkConfigWindow(QWidget):
    def __init__(self, network_manager):
        super().__init__()
        self.network_config: dict
        with open('presets/initial_preset.json', 'r') as f:
            self.network_config = json.load(f)
        self.setWindowTitle("Настройки сети")
        self.setMinimumSize(600, 700)
        self.env = simpy.Environment()
        self.network_manager = network_manager

        self.layout = QVBoxLayout()
        #self.network_delays_window = NetworkDelayWindow(network=self.network_manager)
        hb_layout = QHBoxLayout()
        hb_layout.addWidget(QLabel("Heartbeat для лидера:"))
        self.heartbeat_input = QLineEdit(str(self.network_config['general']['heartbeat']))
        hb_layout.addWidget(self.heartbeat_input)
        self.layout.addLayout(hb_layout)

        node_layout = QHBoxLayout()
        node_layout.addWidget(QLabel("Количество узлов:"))
        self.nodes_input = QSpinBox()
        self.nodes_input.setMinimum(1)
        self.nodes_input.setValue((self.network_config['general']['num_nodes']))
        self.nodes_input.valueChanged.connect(self.update_node_combo)
        node_layout.addWidget(self.nodes_input)
        self.layout.addLayout(node_layout)

        preset_layout = QHBoxLayout()
        self.use_preset_btn = QPushButton("Использовать пресет")
        self.use_preset_btn.clicked.connect(self.show_use_preset_window)
        self.create_preset_btn = QPushButton("Создать пресет")
        self.create_preset_btn.clicked.connect(self.show_create_preset_window)
        self.delays_btn = QPushButton("Топология")
        self.delays_btn.clicked.connect(self.delays_show)
        self.load_topology_btn = QPushButton("Загрузить топологию")
        self.load_topology_btn.clicked.connect(self.load_topology_json)
        preset_layout.addWidget(self.load_topology_btn)
        self.reset_btn = QPushButton("Сбросить")
        self.reset_btn.clicked.connect(self.reset)
        preset_layout.addWidget(self.use_preset_btn)
        preset_layout.addWidget(self.create_preset_btn)
        preset_layout.addWidget(self.delays_btn)
        preset_layout.addWidget(self.reset_btn)
        self.layout.addLayout(preset_layout)

        node_select_layout = QHBoxLayout()
        node_select_layout.addWidget(QLabel("Выберите узел:"))
        self.node_combo = QComboBox()
        node_select_layout.addWidget(self.node_combo)
        self.layout.addLayout(node_select_layout)

        self.create_request_group()
        self.create_shutdown_group()
        self.node_combo.currentIndexChanged.connect(self.load_node_config)
        self.load_node_config(0)

        election_layout = QHBoxLayout()
        election_layout.addWidget(QLabel("election_timeout:"))
        self.election_input = QLineEdit(str(self.network_config['general']['election_timeout']))
        election_layout.addWidget(self.election_input)
        self.layout.addLayout(election_layout)

        sleeping_layout = QHBoxLayout()
        sleeping_layout.addWidget(QLabel("sleeping_time_min:"))
        self.sleep_min_input = QLineEdit(str(self.network_config['general']['sleeping_time_min']))
        sleeping_layout.addWidget(self.sleep_min_input)
        sleeping_layout.addWidget(QLabel("sleeping_time_max:"))
        self.sleep_max_input = QLineEdit(str(self.network_config['general']['sleeping_time_max']))
        sleeping_layout.addWidget(self.sleep_max_input)
        self.layout.addLayout(sleeping_layout)

        accept_layout = QHBoxLayout()
        accept_btn = QPushButton('Принять')
        accept_btn.clicked.connect(self.accept_config)
        accept_layout.addWidget(accept_btn)
        self.layout.addLayout(accept_layout)

        #self.create_preset_window = QWidget()

        self.setLayout(self.layout)
        self.update_node_combo()

    def get_topologies_path(self):
        # папка в проекте
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        path = os.path.join(project_root, 'desktop', 'topologies')
        os.makedirs(path, exist_ok=True)
        return path

    def load_topology_json(self):
        path = self.get_topologies_path()
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Выберите topology json",
            path,
            "JSON Files (*.json)",
            options=options
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                topology = json.load(f)

            self.network_manager.set_topology(topology)
            self.update_node_combo(len(topology['nodes']))
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Успех")
            msg.setText("Топология успешно загружена")
            msg.exec_()

        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Не удалось загрузить топологию:\n{e}")
            msg.exec_()

    def delays_show(self):
        self.network_delays_window = MainWindow(self.network_manager, self)
        self.network_delays_window.show()

    def reset(self):
        self.heartbeat_input.setText('0')
        self.sleep_max_input.setText('0')
        self.sleep_min_input.setText('0')
        self.election_input.setText('0')

        self.req_random_radio.setChecked(True)
        self.req_a_input.setText(str(0.0))
        self.req_b_input.setText(str(10.0))

        self.shutdown_random_radio.setChecked(True)
        self.shutdown_a_input.setText(str(0.0))
        self.shutdown_b_input.setText(str(10.0))

        self.network_config['nodes'] = []
        self.network_config['general']['num_nodes'] = 0
        self.network_config['general']['heartbeat'] = 0
        self.network_config['general']['election_timeout'] = 0
        self.network_config['general']['sleeping_time_min'] = 0
        self.network_config['general']['sleeping_time_max'] = 0

        self.node_combo.clear()
        self.node_combo.addItem('Узел 0')

        self.nodes_input.setValue(0)


    def show_use_preset_window(self):
        self.use_preset_window = QWidget()
        self.use_preset_window.setWindowTitle('Использование пресета')
        self.use_preset_window.setMinimumSize(100, 100)
        use_preset_layout = QVBoxLayout()
        use_preset_cb = QComboBox()
        use_preset_cb.addItems(filename for filename in os.listdir('presets/'))

        use_preset_btn = QPushButton('Использовать')
        use_preset_btn.clicked.connect(lambda: self.set_network_config(use_preset_cb.currentText(), self.use_preset_window))
        use_preset_layout.addWidget(use_preset_cb)
        use_preset_layout.addWidget(use_preset_btn)
        self.use_preset_window.setLayout(use_preset_layout)
        self.use_preset_window.show()

    def set_network_config(self, filename, window):
        
        def refresh_settings():
            gen = self.network_config['general']
            self.heartbeat_input.setText(str(gen['heartbeat']))
            self.sleep_max_input.setText(str(gen['sleeping_time_max']))
            self.sleep_min_input.setText(str(gen['sleeping_time_min']))
            self.election_input.setText(str(gen['election_timeout']))
            self.nodes_input.setValue(gen['num_nodes'])
            self.update_node_combo()

        try:
            with open(f'presets/{filename}') as f:
                text = f.read()
                self.network_config = json.loads(text)
                print('HELLO\n', self.network_config)
                refresh_settings()
                window.hide()
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Не удалось открыть пресет:\n{e}")
            msg.exec_()

    def show_create_preset_window(self):
        self.create_preset_window = QWidget()
        self.create_preset_window.setWindowTitle('Создание пресета')
        self.create_preset_window.setMinimumSize(100, 100)
        create_preset_layout = QVBoxLayout()
        create_tb = QLineEdit()
        create_btn = QPushButton('Создать')
        create_tb.setText(f'Пресет {datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}')
        create_btn.clicked.connect(lambda: self._save_preset(self.create_preset_window, create_tb.text()))
        create_preset_layout.addWidget(create_tb)
        create_preset_layout.addWidget(create_btn)
        self.create_preset_window.setLayout(create_preset_layout)
        self.create_preset_window.show()

    def _save_preset(self, window, text):
        try:
            #self.accept_config()
            data = json.dumps(self.network_config)
            with open(f'presets/{text}.json', 'w') as f:
                f.write(data)
            window.hide()
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Ошибка")
            msg.setText(f"Не удалось сохранить пресет:\n{e}")
            msg.exec_()

    def accept_config(self):
        #num_nodes = len(self.network_config['nodes'])
        count = self.nodes_input.value()
        self.network_manager.num_nodes = count # перезапуск манагера при изменении колва узлов
        self.network_manager.refresh_delays()

        #for index in range(num_nodes):
        index = self.node_combo.currentIndex()

            # === Request time ===
        if self.req_random_radio.isChecked():
            self.network_config['nodes'][index]['request_time'] = {
                'type': 'random',
                'a': float(self.req_a_input.text()),
                'b': float(self.req_b_input.text())
            }
        elif self.req_exp_radio.isChecked():
            self.network_config['nodes'][index]['request_time'] = {
                'type': 'exponential',
                'lambda': float(self.req_lambda_input.text())
            }
        elif self.req_manual_radio.isChecked():
            # Получаем выбранные узлы
            selected = [item.text() for item in self.req_manual_nodes.selectedItems()]
            node_ids = [int(s.split()[-1]) for s in selected]
            # Применяем только к выбранным узлам
            if index in node_ids:
                self.network_config['nodes'][index]['request_time'] = {
                    'type': 'manual',
                    'value': float(self.req_manual_input.text()),
                    'nodes': node_ids
                }

        if self.shutdown_random_radio.isChecked():
            self.network_config['nodes'][index]['shutdown_time'] = {
                'type': 'random',
                'a': float(self.shutdown_a_input.text()),
                'b': float(self.shutdown_b_input.text())
            }
        elif self.shutdown_exp_radio.isChecked():
            self.network_config['nodes'][index]['shutdown_time'] = {
                'type': 'exponential',
                'lambda': float(self.shutdown_lambda_input.text())
            }
        elif self.shutdown_manual_radio.isChecked():
            selected = [item.text() for item in self.shutdown_manual_nodes.selectedItems()]
            node_ids = [int(s.split()[-1]) for s in selected]
            if index in node_ids:
                self.network_config['nodes'][index]['shutdown_time'] = {
                    'type': 'manual',
                    'value': float(self.shutdown_manual_input.text()),
                    'nodes': node_ids
                }

        self.network_config['general']['heartbeat'] = float(self.heartbeat_input.text())
        self.network_config['general']['election_timeout'] = float(self.election_input.text())
        self.network_config['general']['sleeping_time_min'] = float(self.sleep_min_input.text())
        self.network_config['general']['sleeping_time_max'] = float(self.sleep_max_input.text())
        self.network_config['general']['num_nodes'] = self.nodes_input.value()

    def load_node_config(self, index):
        #print('load_node_config', self.network_config)
        if index < 0 or index >= len(self.network_config['nodes']):
            return
        node_cfg = self.network_config['nodes'][index]
        req = node_cfg['request_time']
        if req['type'] == 'random':
            self.req_random_radio.setChecked(True)
            self.req_a_input.setText(str(req.get('a', 0.0)))
            self.req_b_input.setText(str(req.get('b', 10.0)))
        elif req['type'] == 'exponential':
            self.req_exp_radio.setChecked(True)
            self.req_lambda_input.setText(str(req.get('lambda', 1.0)))
        elif req['type'] == 'manual':
            self.req_manual_radio.setChecked(True)
            self.req_manual_input.setText(str(req.get('value', 0.0)))
            selected_nodes = req.get('nodes', [])
            for i in range(self.req_manual_nodes.count()):
                item = self.req_manual_nodes.item(i)
                item.setSelected(i in selected_nodes)
        self.update_request_fields()
        
        shutdown = node_cfg['shutdown_time']
        if shutdown['type'] == 'random':
            self.shutdown_random_radio.setChecked(True)
            self.shutdown_a_input.setText(str(shutdown.get('a', 0.0)))
            self.shutdown_b_input.setText(str(shutdown.get('b', 10.0)))
        elif shutdown['type'] == 'exponential':
            self.shutdown_exp_radio.setChecked(True)
            self.shutdown_lambda_input.setText(str(shutdown.get('lambda', 1.0)))
        elif shutdown['type'] == 'manual':
            self.shutdown_manual_radio.setChecked(True)
            self.shutdown_manual_input.setText(str(req.get('value', 0.0)))
            selected_nodes = shutdown.get('nodes', [])
            for i in range(self.shutdown_manual_nodes.count()):
                item = self.shutdown_manual_nodes.item(i)
                item.setSelected(i in selected_nodes)
        self.update_shutdown_fields()

    def update_node_combo(self, amount=0):
        if amount == 0:
            count = self.nodes_input.value()
        else:
            count = amount
            self.nodes_input.setValue(amount)
        self.node_combo.clear()
        self.node_combo.addItems([f"Узел {i}" for i in range(count)])
        self.req_manual_nodes.clear()
        self.req_manual_nodes.addItems([f"Узел {i}" for i in range(count)])
        # for i in range(self.req_manual_nodes.count()):
        #     print(self.req_manual_nodes.count())
        #     req = self.network_config['nodes'][i]['request_time']
            
        #     item = self.req_manual_nodes.item(i)
        #     if req['type'] == 'manual':        # список индексов, которые хотим выбрать
        #         item.setSelected(True)
        #     else:
        #         item.setSelected(False)
        self.shutdown_manual_nodes.clear()
        self.shutdown_manual_nodes.addItems([f"Узел {i}" for i in range(count)])
        # for i in range(self.shutdown_manual_nodes.count()):
        #     req = self.network_config['nodes'][i]['shutdown_time']
        #     item = self.shutdown_manual_nodes.item(i)
        #     if req['type'] == 'manual':        # список индексов, которые хотим выбрать
        #         item.setSelected(True)
        #     else:
        #         item.setSelected(False)

        nodes_cfg = self.network_config['nodes']
        while len(nodes_cfg) < count:
            node_id = len(nodes_cfg)
            nodes_cfg.append({
                'node_id': node_id,
                'request_time': {'type': 'random', 'a': 0.0, 'b': 10.0},
                'shutdown_time': {'type': 'random', 'a': 0.0, 'b': 10.0}
            })
        while len(nodes_cfg) > count:
            nodes_cfg.pop()
        self.load_node_config(self.node_combo.currentIndex())

    def create_request_group(self):
        group = QGroupBox("Время поступления заявки")
        layout = QHBoxLayout()

        random_layout = QVBoxLayout()
        self.req_random_radio = QRadioButton("Равномерный закон")
        self.req_random_radio.setChecked(True)
        self.req_random_radio.toggled.connect(self.update_request_fields)
        random_layout.addWidget(self.req_random_radio)
        random_layout.addWidget(QLabel("a:"))
        self.req_a_input = QLineEdit("0.0")
        random_layout.addWidget(self.req_a_input)
        random_layout.addWidget(QLabel("b:"))
        self.req_b_input = QLineEdit("10.0")
        random_layout.addWidget(self.req_b_input)

        exp_layout = QVBoxLayout()
        self.req_exp_radio = QRadioButton("Закон Пуассона")
        self.req_exp_radio.toggled.connect(self.update_request_fields)
        exp_layout.addWidget(self.req_exp_radio)
        exp_layout.addWidget(QLabel("lambda:"))
        self.req_lambda_input = QLineEdit("1.0")
        exp_layout.addWidget(self.req_lambda_input)

        manual_layout = QVBoxLayout()
        self.req_manual_radio = QRadioButton("Ручной ввод")
        self.req_manual_radio.toggled.connect(self.update_request_fields)
        manual_layout.addWidget(self.req_manual_radio)
        manual_layout.addWidget(QLabel("Время (ms):"))
        self.req_manual_input = QLineEdit("0.0")
        manual_layout.addWidget(self.req_manual_input)
        manual_layout.addWidget(QLabel("Выберите узлы:"))
        self.req_manual_nodes = QListWidget()
        self.req_manual_nodes.setSelectionMode(QListWidget.MultiSelection)
        for i in range(self.nodes_input.value()):
            self.req_manual_nodes.addItem(f"Узел {i}")
        manual_layout.addWidget(self.req_manual_nodes)

        layout.addLayout(random_layout)
        layout.addLayout(exp_layout)
        layout.addLayout(manual_layout)

        group.setLayout(layout)
        self.layout.addWidget(group)
        self.update_request_fields()

    def update_request_fields(self):
        self.req_a_input.setEnabled(self.req_random_radio.isChecked())
        self.req_b_input.setEnabled(self.req_random_radio.isChecked())
        self.req_lambda_input.setEnabled(self.req_exp_radio.isChecked())
        self.req_manual_input.setEnabled(self.req_manual_radio.isChecked())
        self.req_manual_nodes.setEnabled(self.req_manual_radio.isChecked())

    def create_shutdown_group(self):
        group = QGroupBox("Время shutdown")
        layout = QHBoxLayout()
        random_layout = QVBoxLayout()
        self.shutdown_random_radio = QRadioButton("Равномерный закон")
        self.shutdown_random_radio.setChecked(True)
        self.shutdown_random_radio.toggled.connect(self.update_shutdown_fields)
        random_layout.addWidget(self.shutdown_random_radio)
        random_layout.addWidget(QLabel("a:"))
        self.shutdown_a_input = QLineEdit("0.0")
        random_layout.addWidget(self.shutdown_a_input)
        random_layout.addWidget(QLabel("b:"))
        self.shutdown_b_input = QLineEdit("10.0")
        random_layout.addWidget(self.shutdown_b_input)

        exp_layout = QVBoxLayout()
        self.shutdown_exp_radio = QRadioButton("Закон Пуассона")
        self.shutdown_exp_radio.toggled.connect(self.update_shutdown_fields)
        exp_layout.addWidget(self.shutdown_exp_radio)
        exp_layout.addWidget(QLabel("lambda:"))
        self.shutdown_lambda_input = QLineEdit("1.0")
        exp_layout.addWidget(self.shutdown_lambda_input)

        manual_layout = QVBoxLayout()
        self.shutdown_manual_radio = QRadioButton("Ручной ввод")
        self.shutdown_manual_radio.toggled.connect(self.update_shutdown_fields)
        manual_layout.addWidget(self.shutdown_manual_radio)
        manual_layout.addWidget(QLabel("Время (ms):"))
        self.shutdown_manual_input = QLineEdit("0.0")
        manual_layout.addWidget(self.shutdown_manual_input)
        manual_layout.addWidget(QLabel("Выберите узлы:"))
        self.shutdown_manual_nodes = QListWidget()
        self.shutdown_manual_nodes.setSelectionMode(QListWidget.MultiSelection)
        for i in range(self.nodes_input.value()):
            self.shutdown_manual_nodes.addItem(f"Узел {i}")
        manual_layout.addWidget(self.shutdown_manual_nodes)

        layout.addLayout(random_layout)
        layout.addLayout(exp_layout)
        layout.addLayout(manual_layout)
        group.setLayout(layout)
        self.layout.addWidget(group)
        self.update_shutdown_fields()

    def update_shutdown_fields(self):
        self.shutdown_a_input.setEnabled(self.shutdown_random_radio.isChecked())
        self.shutdown_b_input.setEnabled(self.shutdown_random_radio.isChecked())
        self.shutdown_lambda_input.setEnabled(self.shutdown_exp_radio.isChecked())
        self.shutdown_manual_input.setEnabled(self.shutdown_manual_radio.isChecked())
        self.shutdown_manual_nodes.setEnabled(self.shutdown_manual_radio.isChecked())

    def get_settings(self):
        return self.network_config