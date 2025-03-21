import os
import sqlite3

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QIcon, QFont, QDoubleValidator
from PyQt5.QtWidgets import QMainWindow, QDialog
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QVBoxLayout, QComboBox, QCompleter, \
    QListWidget, QListWidgetItem, QSizePolicy, QSplitter, QSpinBox, QPushButton, QHBoxLayout, QFormLayout


class ImageWindow(QDialog):
    PLACEHOLDER_IMAGE_PATH = os.path.join('Images', 'Placeholder.jpg')

    def __init__(self, imgPath, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Card Viewer")
        self.setGeometry(100, 100, 400, 400)
        self.label = QLabel()

        # Set pixmap to a placeholder img if the specified img path does not exist
        if not os.path.isfile(imgPath):
            self.label.setPixmap(QPixmap(self.PLACEHOLDER_IMAGE_PATH))
        else:
            self.label.setPixmap(QPixmap(imgPath))

        layout = QVBoxLayout()
        layout.addWidget(self.label)

        self.setLayout(layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton or  event.key() == Qt.Key_Escape:
            self.close()


class MainWindow(QMainWindow):
    PLACEHOLDER_IMAGE_PATH = os.path.join('Images', 'Placeholder.jpg')

    def __init__(self):
        super().__init__()
        self.win = None
        self.inWin = None
        self.delC = None
        self.imgWindow = None
        self.setWindowTitle("Trading App")
        self.splitter = QSplitter()
        leftLayout = QVBoxLayout()
        rightLayout = QVBoxLayout()
        photoLayout = QVBoxLayout()

        self.label = QLabel()
        self.input = QLineEdit()
        self.resultList = QListWidget()
        self.inputPercentage = QSpinBox()
        self.inputPercentage.setToolTip("Set the price range percentage. Default value is 20%")
        self.inputPercentage.setRange(0, 100)
        self.inputPercentage.setValue(20)
        self.filterBox = QComboBox()
        self.filterBox.setToolTip("Set the card filter. Default value is 'All' ")
        self.photo = QLabel()
        self.photo.setPixmap(QPixmap(r'Images\Placeholder.jpg'))

        self.buttonLayout = QHBoxLayout()
        self.updateBtn = QPushButton()
        self.updateBtn.setText("Update Card Price")
        self.newBtn = QPushButton()
        self.newBtn.setText("Insert New Card")
        self.deleteBtn = QPushButton()
        self.deleteBtn.setText("Delete Card")
        self.buttonLayout.addWidget(self.updateBtn)
        self.buttonLayout.addWidget(self.newBtn)
        self.buttonLayout.addWidget(self.deleteBtn)

        policy = self.filterBox.sizePolicy()
        policy.setHorizontalPolicy(QSizePolicy.Expanding)
        self.filterBox.setSizePolicy(policy)
        self.filterBox.setInsertPolicy(QComboBox.InsertAlphabetically)

        photoLayout.addWidget(self.photo)
        leftLayout.addLayout(photoLayout)
        leftLayout.addStretch(1)
        rightLayout.addWidget(self.input)
        rightLayout.addWidget(self.filterBox)
        rightLayout.addWidget(self.inputPercentage)
        rightLayout.addWidget(self.label)
        rightLayout.addWidget(self.resultList)
        rightLayout.addLayout(self.buttonLayout)

        leftWidget = QWidget()
        leftWidget.setLayout(leftLayout)
        rightWidget = QWidget()
        rightWidget.setLayout(rightLayout)

        self.splitter.addWidget(leftWidget)
        self.splitter.addWidget(rightWidget)

        self.setCentralWidget(self.splitter)

        self.conn = sqlite3.connect('data.db')
        self.cur = self.conn.cursor()
        query = 'SELECT Name, Card_Set, Price FROM Cards'
        results = self.cur.execute(query).fetchall()

        # Prepare names for the autocompleter
        self.names = [f"{result[0]} | {result[1]} | ${result[2]}" for result in results]

        completer = QCompleter(self.names)
        self.input.setCompleter(completer)
        completer.setCaseSensitivity(2)

        completer.activated.connect(self.updateLabel)
        self.resultList.itemClicked.connect(self.resultItemClicked)
        self.resultList.setFocusPolicy(Qt.StrongFocus)
        self.filterBox.activated.connect(self.filter)
        self.inputPercentage.valueChanged.connect(self.updateLabel)
        self.updateBtn.clicked.connect(self.updateWindowShow)
        self.newBtn.clicked.connect(self.insertWindowShow)
        self.deleteBtn.clicked.connect(self.deleteWindowShow)

    # Function to open card img in new window
    def openCardView(self, imgPath):
        if self.imgWindow is not None:
            self.imgWindow.close()
        self.imgWindow = ImageWindow(imgPath, self)
        self.imgWindow.show()

    def updateWindowShow(self):
        self.win = UpdateWindow(self.conn, self.cur)
        self.win.updateCompleted.connect(self.showUpdate)
        self.win.show()

    def deleteWindowShow(self):
        self.delC = DeleteWindow(self.conn, self.cur)
        self.delC.deleteCompleted.connect(self.showUpdate)
        self.delC.show()

    def insertWindowShow(self):
        self.inWin = InsertWindow(self.conn, self.cur)
        self.inWin.insertCompleted.connect(self.showUpdate)
        self.inWin.show()

    def showUpdate(self):
        self.input.setText("Action Completed!")
        query = 'SELECT Name, Card_Set, Price FROM Cards'
        results = self.cur.execute(query).fetchall()
        self.names = [f"{result[0]} | {result[1]} | ${result[2]}" for result in results]
        completer = QCompleter(self.names)
        self.input.setCompleter(completer)
        completer.setCaseSensitivity(2)
        completer.activated.connect(self.updateLabel)

    def updateLabel(self):
        user_input = self.input.text()
        name, cset, price = map(str.strip, user_input.split("|"))
        imgPath = os.path.join("Images", cset, f"{name}.jpg")

        if not os.path.isfile(imgPath):
            self.photo.setPixmap(QPixmap(r'Images\Placeholder.jpg'))
        else:
            self.photo.setPixmap(QPixmap(imgPath))

        price = user_input.split("$")[-1]
        percentage = self.inputPercentage.value() / 100
        lowerBound = float(price) * (1.0 - percentage)
        upperBound = float(price) * (1.0 + percentage)

        query = 'SELECT Name, Card_Set, Price, Type FROM Cards ' \
                'WHERE Price BETWEEN ? AND ? AND Card_Set NOT LIKE "%Promo%" ' \
                'ORDER BY Card_Set, Price'

        res = self.cur.execute(query, (lowerBound, upperBound)).fetchall()
        self.filterBox.clear()
        self.resultList.clear()
        self.filterBox.addItem("All")
        self.filterBox.addItem("Trade Up")
        seen = []

        for row in res:
            cname, cardSet, price, ctype = row
            text = f"{cname} - {cardSet} - ${price}"
            imgPath = os.path.join("Images", cardSet, f"{cname}.jpg")

            if cardSet not in seen:
                seen.append(cardSet)
                self.filterBox.addItem(cardSet)

            if ctype not in seen:
                seen.append(ctype)
                self.filterBox.addItem(ctype)

            item = QListWidgetItem(text)
            item.imgPath = imgPath

            if cname != name:
                self.resultList.addItem(item)

    def filter(self):
        user_input = self.input.text()
        price = user_input.split("$")[-1]
        userFilter = self.filterBox.currentText()
        percentage = self.inputPercentage.value() / 100
        lowerBound = float(price) * (1.0 - percentage)
        upperBound = float(price) * (1.0 + percentage)

        if userFilter == 'All':
            self.updateLabel()

        elif userFilter == 'Trade Up':
            query = 'SELECT Name, Card_Set, Price, Type FROM Cards ' \
                    'WHERE Price BETWEEN ?  AND ?  AND Card_Set NOT LIKE "%Promo%" ' \
                    'ORDER BY Card_Set, Price'

            res = self.cur.execute(query, (price, upperBound)).fetchall()
            self.resultList.clear()
            seen = []

            for row in res:
                name, cardSet, price, ctype = row
                text = f"{name} - {cardSet} - ${price}"
                imgPath = os.path.join("Images", cardSet, f"{name}.jpg")
                if cardSet not in seen and cardSet != self.filterBox.currentText():
                    seen.append(cardSet)
                    self.filterBox.addItem(cardSet)
                if ctype not in seen and ctype != self.filterBox.currentText():
                    seen.append(ctype)
                    self.filterBox.addItem(ctype)
                item = QListWidgetItem(text)
                item.imgPath = imgPath

                self.resultList.addItem(item)

        else:
            query = 'SELECT Name, Card_Set, Price, Type FROM Cards ' \
                    'WHERE Price BETWEEN ?  AND ?  AND Card_Set NOT LIKE "%Promo%" ' \
                    'AND (Card_SET = ? OR Type = ?)' \
                    'ORDER BY Card_Set, Price'

            res = self.cur.execute(query, (lowerBound, upperBound, userFilter, userFilter)).fetchall()
            self.resultList.clear()
            seen = []

            for row in res:
                name, cardSet, price, ctype = row
                text = f"{name} - {cardSet} - ${price}"
                imgPath = os.path.join("Images", cardSet, f"{name}.jpg")
                if cardSet not in seen and cardSet != self.filterBox.currentText():
                    seen.append(cardSet)
                    self.filterBox.addItem(cardSet)
                if ctype not in seen and ctype != self.filterBox.currentText():
                    seen.append(ctype)
                    self.filterBox.addItem(ctype)
                item = QListWidgetItem(text)
                item.imgPath = imgPath
                self.resultList.addItem(item)

    def resultItemClicked(self, item):
        self.openCardView(item.imgPath)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            selectedCard = self.resultList.selectedItems()
            if selectedCard:
                self.resultItemClicked(selectedCard[0])
            else:
                super().keyPressEvent(event)


class UpdateWindow(QWidget):
    updateCompleted = pyqtSignal()

    def __init__(self, conn, cur, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update Card")
        self.setGeometry(100, 100, 400, 200)
        self.userInput = QLineEdit()
        self.priceInput = QLineEdit()
        self.priceInput.setValidator(QDoubleValidator(0.0, 2147483647.0, 2, self))

        self.nameLabel = QLabel("Name:")
        self.nameLabel.setFont(QFont("Arial", 20))
        self.priceLabel = QLabel("Price:")
        self.priceLabel.setFont(QFont("Arial", 20))

        self.conn = conn
        self.cur = cur
        query = 'SELECT Name, Card_Set, Price FROM Cards'
        self.results = self.cur.execute(query).fetchall()

        # Prepare names for the autocompleter
        self.names = [f"{result[0]} | {result[1]} | ${result[2]}" for result in self.results]
        self.cardSets = [result[1] for result in self.results]

        self.uBtn = QPushButton("Update!")

        layout = QVBoxLayout()
        formLayout = QFormLayout()

        completer = QCompleter(self.names)
        self.userInput.setCompleter(completer)
        completer.setCaseSensitivity(2)

        formLayout.addRow(self.nameLabel, self.userInput)
        formLayout.addRow(self.priceLabel, self.priceInput)

        layout.addLayout(formLayout)
        layout.addWidget(self.uBtn)

        self.setLayout(layout)

        self.uBtn.clicked.connect(self.updateDB)

    def updateDB(self):
        try:
            name, cSet, _ = self.userInput.text().split(' | ')
            updateQuery = "UPDATE Cards " \
                          "SET Price = ? " \
                          "WHERE Name = ? AND Card_SET = ? "
            self.cur.execute(updateQuery, (self.priceInput.text(), name, cSet))
            self.conn.commit()

        except Exception:
            self.priceInput.setText("Must be an integer value!")

    def closeEvent(self, event):
        self.updateCompleted.emit()
        event.accept()


class InsertWindow(QWidget):
    insertCompleted = pyqtSignal()

    def __init__(self, conn, cur, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insert Card")
        self.setGeometry(100, 100, 400, 400)
        self.userInput = QLineEdit()
        self.priceInput = QLineEdit()
        self.cardSetInput = QLineEdit()
        self.priceInput.setValidator(QDoubleValidator(0.0, 2147483647.0, 2, self))

        self.nameLabel = QLabel("Name:")
        self.nameLabel.setFont(QFont("Arial", 20))
        self.priceLabel = QLabel("Price:")
        self.priceLabel.setFont(QFont("Arial", 20))
        self.cardLabel = QLabel("Card Set:")
        self.cardLabel.setFont(QFont("Arial", 20))

        self.conn = conn
        self.cur = cur

        self.iBtn = QPushButton()
        self.iBtn.setText("Insert New Card!")

        layout = QVBoxLayout()
        formLayout = QFormLayout()

        formLayout.addRow(self.nameLabel, self.userInput)
        formLayout.addRow(self.cardLabel, self.cardSetInput)
        formLayout.addRow(self.priceLabel, self.priceInput)

        formLayout.setVerticalSpacing(20)

        layout.addLayout(formLayout)
        layout.addWidget(self.iBtn)

        self.setLayout(layout)

        self.iBtn.clicked.connect(self.insertDB)

    def insertDB(self):
        try:

            updateQuery = "INSERT INTO Cards " \
                          "(Name, Price, Card_Set) " \
                          "VALUES (?, ?, ?) "
            self.cur.execute(updateQuery, (self.userInput.text(), self.priceInput.text(), self.cardSetInput.text()))
            self.conn.commit()

        except Exception:
            self.priceInput.setText("Must be an integer value!")

    def closeEvent(self, event):
        self.insertCompleted.emit()
        event.accept()


class DeleteWindow(QWidget):
    deleteCompleted = pyqtSignal()

    def __init__(self, conn, cur, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Delete Card")
        self.setGeometry(100, 100, 400, 200)
        self.userInput = QLineEdit()

        self.nameLabel = QLabel("Name:")
        self.nameLabel.setFont(QFont("Arial", 20))

        self.conn = conn
        self.cur = cur
        query = 'SELECT Name, Card_Set, Price FROM Cards'
        self.results = self.cur.execute(query).fetchall()

        # Prepare names for the autocompleter
        self.names = [f"{result[0]} | {result[1]} | ${result[2]}" for result in self.results]
        self.cardSets = [result[1] for result in self.results]

        self.dBtn = QPushButton("Delete!")

        layout = QVBoxLayout()
        formLayout = QFormLayout()

        completer = QCompleter(self.names)
        self.userInput.setCompleter(completer)
        completer.setCaseSensitivity(2)

        formLayout.addRow(self.nameLabel, self.userInput)

        layout.addLayout(formLayout)
        layout.addWidget(self.dBtn)

        self.setLayout(layout)

        self.dBtn.clicked.connect(self.deleteDB)

    def deleteDB(self):
        try:
            name, cSet, _ = self.userInput.text().split(' | ')
            updateQuery = "DELETE from Cards " \
                          "WHERE Name = ? AND Card_SET = ? "
            self.cur.execute(updateQuery, (name, cSet))
            self.conn.commit()

        except Exception:
            self.userInput.setText("Card Must Be in Database!")

    def closeEvent(self, event):
        self.deleteCompleted.emit()
        event.accept()


app = QApplication([])
window = MainWindow()
window.showMaximized()
app.setWindowIcon(QIcon(os.path.join("Images", 'pball.ico')))
window.setWindowIcon(QIcon(os.path.join("Images", 'pball.ico')))
app.exec()
