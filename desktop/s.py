from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit

app = QApplication([])

window = QWidget()
layout = QVBoxLayout(window)

# Название текстбокса
label = QLabel("Медиана запросов на синхр")
# Сам текстбокс
textbox = QLineEdit()
textbox.setText("123")  # пример значения
textbox.setReadOnly(True)  # если только вывод

# Сначала добавляем label, потом textbox
layout.addWidget(label)
layout.addWidget(textbox)

label = QLabel("Медиана запросов на синхр")
# Сам текстбокс
textbox = QLineEdit()
textbox.setText("123")  # пример значения
textbox.setReadOnly(True)  # если только вывод

# Сначала добавляем label, потом textbox
layout.addWidget(label)
layout.addWidget(textbox)

window.show()
app.exec()