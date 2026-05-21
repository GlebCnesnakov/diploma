import json
import datetime
import sys
import os
import networkx as nx
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPen, QBrush, QPainter
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtWidgets import QFileDialog

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

NODE_RADIUS = 25


class EdgeItem(QGraphicsLineItem):
    def __init__(self, source_node, target_node, delay):
        super().__init__()

        self.source_node = source_node
        self.target_node = target_node
        self.delay = delay

        self.setPen(QPen(Qt.black, 2))

        self.label = QGraphicsSimpleTextItem(str(delay))

        self.update_position()

    def update_position(self):
        x1 = self.source_node.pos().x()
        y1 = self.source_node.pos().y()

        x2 = self.target_node.pos().x()
        y2 = self.target_node.pos().y()

        self.setLine(x1, y1, x2, y2)

        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2

        self.label.setPos(mx, my)


class NodeItem(QGraphicsEllipseItem):
    def __init__(self, node_id, x, y):
        super().__init__(-NODE_RADIUS, -NODE_RADIUS, NODE_RADIUS * 2, NODE_RADIUS * 2)

        self.node_id = node_id
        self.edges = []

        self.setBrush(QBrush(Qt.cyan))
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable)

        self.setPos(x, y)

        self.text = QGraphicsSimpleTextItem(str(node_id), self)
        self.text.setPos(-5, -10)

    def itemChange(self, change, value):
        if change == QGraphicsEllipseItem.ItemPositionChange:
            for edge in self.edges:
                edge.update_position()

        return super().itemChange(change, value)

class GraphScene(QGraphicsScene):
    def __init__(self):
        super().__init__()

        self.graph = nx.Graph()

        self.nodes = {}
        self.edges = []

        self.selected_node = None

    def add_node(self, x, y):
        node_id = len(self.nodes)
        node = NodeItem(node_id, x, y)
        self.nodes[node_id] = node
        self.graph.add_node(node_id, enabled=True)
        self.addItem(node)

    def add_edge(self, source_id, target_id, delay):
        if source_id == target_id:
            return

        if self.graph.has_edge(source_id, target_id):
            return

        source_node = self.nodes[source_id]
        target_node = self.nodes[target_id]

        edge = EdgeItem(source_node, target_node, delay)

        source_node.edges.append(edge)
        target_node.edges.append(edge)

        self.edges.append(edge)

        self.graph.add_edge(source_id, target_id, delay=delay)

        self.addItem(edge)
        self.addItem(edge.label)

    def mouseDoubleClickEvent(self, event):
        pos = event.scenePos()

        clicked_items = self.items(pos)

        clicked_node = None

        for item in clicked_items:
            if isinstance(item, NodeItem):
                clicked_node = item
                break

        if clicked_node:
            if self.selected_node is None:
                self.selected_node = clicked_node
                clicked_node.setBrush(QBrush(Qt.green))
            else:
                delay, ok = QInputDialog.getDouble(
                    None,
                    'Delay',
                    'Введите задержку:',
                    0.1,
                    0.001,
                    1000,
                    3,
                )

                if ok:
                    self.add_edge(
                        self.selected_node.node_id,
                        clicked_node.node_id,
                        delay,
                    )

                self.selected_node.setBrush(QBrush(Qt.cyan))
                self.selected_node = None

        else:
            self.add_node(pos.x(), pos.y())

        super().mouseDoubleClickEvent(event)

    def remove_selected(self):
        selected_items = self.selectedItems()

        for item in selected_items:
            if isinstance(item, NodeItem):
                self.remove_node(item)

    def remove_node(self, node):
        node_id = node.node_id

        for edge in list(node.edges):
            self.remove_edge(edge)

        self.graph.remove_node(node_id)

        self.removeItem(node)

        del self.nodes[node_id]

    def remove_edge(self, edge):
        src = edge.source_node.node_id
        dst = edge.target_node.node_id

        if self.graph.has_edge(src, dst):
            self.graph.remove_edge(src, dst)

        self.removeItem(edge)
        self.removeItem(edge.label)

        if edge in edge.source_node.edges:
            edge.source_node.edges.remove(edge)

        if edge in edge.target_node.edges:
            edge.target_node.edges.remove(edge)

    def get_topologies_path(self):
        # папка в проекте
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        path = os.path.join(project_root, 'desktop', 'topologies')
        os.makedirs(path, exist_ok=True)
        return path

    def export_json(self):
        path = self.get_topologies_path()
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = os.path.join(path, f'topology_{timestamp}.json')

        data = {
            'nodes': [],
            'edges': [],
        }

        for node_id, node in self.nodes.items():
            data['nodes'].append({
                'id': node_id,
                'x': node.pos().x(),
                'y': node.pos().y(),
                'enabled': self.graph.nodes[node_id]['enabled']
            })

        for src, dst, attrs in self.graph.edges(data=True):
            data['edges'].append({
                'source': src,
                'target': dst,
                'delay': attrs['delay']
            })

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

        return filename

    def import_json(self):
        path = self.get_topologies_path()
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
            None,
            "Выберите файл топологии JSON",
            path,
            "JSON Files (*.json)",
            options=options
        )

        if not filename:
            return

        self.clear()
        self.graph.clear()
        self.nodes.clear()
        self.edges.clear()

        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for node_data in data['nodes']:
            node = NodeItem(
                node_data['id'],
                node_data['x'],
                node_data['y']
            )
            self.nodes[node.node_id] = node
            self.graph.add_node(node.node_id, enabled=node_data.get('enabled', True))
            self.addItem(node)

        for edge_data in data['edges']:
            self.add_edge(
                edge_data['source'],
                edge_data['target'],
                edge_data['delay']
            )


class MainWindow(QMainWindow):
    def __init__(self, network_manager):
        super().__init__()
        self.network_manager = network_manager
        self.setWindowTitle('Редактор топологии сети')
        self.resize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout()

        button_layout = QHBoxLayout()

        self.save_button = QPushButton('Сохранить JSON')
        self.load_button = QPushButton('Загрузить JSON')
        self.delete_button = QPushButton('Удалить выбранное')

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)

        self.scene = GraphScene()

        self.view = QGraphicsView(self.scene)

        self.view.setRenderHint(QPainter.Antialiasing)

        self.view.setViewportUpdateMode(
            QGraphicsView.FullViewportUpdate
        )

        self.view.setDragMode(
            QGraphicsView.RubberBandDrag
        )

        layout.addWidget(self.view)

        central.setLayout(layout)

        self.save_button.clicked.connect(self.save_json)
        self.load_button.clicked.connect(self.load_json)
        self.delete_button.clicked.connect(self.scene.remove_selected)

    def save_json(self):
        filename = self.scene.export_json()
        QMessageBox.information(self, 'Успех', f'Топология сохранена:\n{filename}')

    def load_json(self):
        try:
            self.scene.import_json()
            QMessageBox.information(self, 'Успех', 'Топология загружена.')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())