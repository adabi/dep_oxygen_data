from PyQt5 import QtCore, QtWidgets
from parsing import add_experiment, modify_experiment, add_plate, modify_plate
from collections import OrderedDict


class ExperimentsModel(QtCore.QAbstractTableModel):

    sig_changes = QtCore.pyqtSignal(str, str, str)

    def __init__(self, data, cell_line):
        super().__init__()
        self.cell_line = cell_line
        self.data = data
        self.number_of_rows = len(data) + 1

    def headerData(self, p_int, Qt_Orientation, role=None):
        headers = ["ID", "Date", "Compounds", "Concentrations", "Exposure Time", "Condition", "Assay", "Comments"]
        if Qt_Orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return headers[p_int]

    def rowCount(self, parent=None, *args, **kwargs):
        return self.number_of_rows

    def columnCount(self, parent=None, *args, **kwargs):
        return 8

    def data(self, QModelIndex, role=None):
        row = QModelIndex.row()
        column = QModelIndex.column()
        if QModelIndex:
            if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
                if row < self.number_of_rows - 1:
                    return self.data[row][column]
                else:
                    if column == 1:
                        return("NEW")



    def flags(self, QModelIndex):
        flags = super().flags(QModelIndex)
        column = QModelIndex.column()
        row = QModelIndex.row()

        if QModelIndex.isValid():
            if row < self.number_of_rows -1:
                if column != 0:
                    flags =  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
            else:
                if column == 1:
                    flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

        return flags

    def setData(self, QModelIndex, Any, role=None):
        fields = ["date", "compounds", "concentrations", "exposure_time", "condition", "assay", "comments"]
        row = QModelIndex.row()
        column = QModelIndex.column()

        if role == QtCore.Qt.EditRole:
            if row == self.number_of_rows - 1:
                if len(self.data) == 0:
                    new_id = 1
                else:
                    new_id = max(int(x[0]) for x in self.data) + 1
                    new_id = str(new_id)
                self.data.append([new_id, Any, "", "", "", "", "", "", ""])
                self.beginInsertRows(QtCore.QModelIndex(), self.number_of_rows, self.number_of_rows)
                self.insertRow(self.number_of_rows)
                self.endInsertRows()
                self.number_of_rows += 1
                self.dataChanged.emit(QModelIndex, QModelIndex)
                add_experiment(self.cell_line, new_id, Any, "", "", "", "", "", "")
            else:
                self.data[row][column] = Any
                self.dataChanged.emit(QModelIndex, QModelIndex)
                modify_experiment(self.cell_line, self.data[row][0], fields[column - 1], Any)

        return True

    def deleteExperiment(self, row):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        self.removeRow(row)
        del self.data[row]
        self.endRemoveRows()
        self.number_of_rows -= 1

    def resetModel(self, data, cell_line):
        self.beginResetModel()
        self.cell_line = cell_line
        self.data = data
        self.number_of_rows = len(data) + 1
        self.endResetModel()


class PlatesModel(QtCore.QAbstractTableModel):

    sig_changes = QtCore.pyqtSignal(str, str, str)

    def __init__(self, data, cell_line, experiment, concentrations, assay):
        super().__init__()
        self.cell_line = cell_line
        self.data = data
        self.number_of_rows = len(data) + 1
        self.experiment = experiment
        self.concentrations = concentrations
        self.assay = assay
        for item in data:
            for concentration in concentrations:
                if concentration not in item[3]:
                    item[3][concentration] = []

        self.headers = ["ID", "File", "Range"] + concentrations
        self.fields = ["plate", "file", "range"] + self.concentrations


    def headerData(self, p_int, Qt_Orientation, role=None):


        if Qt_Orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.headers[p_int]

    def rowCount(self, parent=None, *args, **kwargs):
        return self.number_of_rows

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self.concentrations) + 3

    def data(self, QModelIndex, role=None):
        row = QModelIndex.row()
        column = QModelIndex.column()
        if QModelIndex and (role==QtCore.Qt.DisplayRole or role==QtCore.Qt.EditRole):
            if row < self.number_of_rows - 1:
                if column > 2:
                    return str(self.data[row][3][self.headers[column]])[1:-1]
                else:
                    if column == 1:
                        return str(self.data[row][column])
                    else:
                        return self.data[row][column]
            else:
                if column == 1:
                    return("NEW")
                else:
                    return None

    def flags(self, QModelIndex):
        flags = super().flags(QModelIndex)
        column = QModelIndex.column()
        row = QModelIndex.row()

        if QModelIndex.isValid():
            if row < self.number_of_rows -1:
                if column > 1:
                    flags =  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

        return flags

    def setData(self, QModelIndex, Any, role=None):

        row = QModelIndex.row()
        column = QModelIndex.column()
        if role == QtCore.Qt.EditRole:

            if row == self.number_of_rows - 1:
                if len(self.data) == 0:
                    new_id = "1"
                else:
                    new_id = str(int(self.data[-1][0]) + 1)
                self.data.append([new_id, Any, ""] + [{x:[] for x in self.concentrations}])
                self.beginInsertRows(QtCore.QModelIndex(), self.number_of_rows, self.number_of_rows)
                self.insertRow(self.number_of_rows)
                self.endInsertRows()
                self.number_of_rows += 1
                self.dataChanged.emit(QModelIndex, QModelIndex)
                blank_concentrations = ""
                for concentration in self.concentrations:
                    blank_concentrations += f"[{concentration}]:[],"
                blank_concentrations = blank_concentrations[:-1]
                add_plate(self.cell_line, self.experiment, new_id, Any, "", blank_concentrations)

            else:

                if column > 2:
                    try:
                        field = "concentrations"
                        new = ""
                        list_new = []
                        #create a list of the entered rows to input into the model's data:
                        for item in Any.split(","):
                            if item != '':
                                list_new.append(int(item))
                        self.data[row][3][self.headers[column]] = list_new
                        for concentration in self.concentrations:
                            new += f"[{concentration}]:{str(self.data[row][3][concentration])},"
                        new = new[:-1]
                        self.dataChanged.emit(QModelIndex, QModelIndex)
                        modify_plate(self.cell_line, self.experiment, self.data[row][0], field, new)
                    except:
                        msgbox = QtWidgets.QMessageBox()
                        msgbox.setText("Error. Please enter field again")
                        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                        msgbox.exec_()
                else:

                    field = self.fields[column]
                    self.data[row][column] = Any
                    self.dataChanged.emit(QModelIndex, QModelIndex)
                    modify_plate(self.cell_line, self.experiment, self.data[row][0], field, Any)

        return True

    def deletePlate(self, row):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        self.removeRow(row)
        del self.data[row]
        self.endRemoveRows()
        self.number_of_rows -= 1

    def pasteRows(self, rows):
        for index, plate in enumerate(rows):
            new = ""
            field = "concentrations"
            for concentration in plate:
                self.data[index][3][concentration] = plate[concentration]
                new += f"[{concentration}]:{str(plate[concentration])},"
            new = new[:-1]
            index1 = self.createIndex(index, 3)
            index2 = self.createIndex(index, len(plate) + 2)
            modify_plate(self.cell_line, self.experiment, self.data[index][0], field, new)
            self.dataChanged.emit(index1, index2)

    def sort(self, p_int, order=None):
        self.data = sorted(self.data,key=lambda x: x[p_int], reverse = order == 1)
        index1 = self.createIndex(0, 0)
        index2 = self.createIndex(len(self.data) - 1, 10)
        self.dataChanged.emit(index1, index2)

    def resetModel(self, data, cell_line, experiment, concentrations, assay):
        self.beginResetModel()
        self.cell_line = cell_line
        self.data = data
        self.number_of_rows = len(data) + 1
        self.experiment = experiment
        self.concentrations = concentrations
        self.assay = assay
        for item in data:
            for concentration in concentrations:
                if concentration not in item[3]:
                    item[3][concentration] = []

        self.headers = ["ID", "File", "Range"] + concentrations
        self.fields = ["plate", "file", "range"] + self.concentrations

        self.endResetModel()

class CompareModel(QtCore.QAbstractTableModel):

    sig_changes = QtCore.pyqtSignal(str, str, str)

    def __init__(self, data=None):
        super().__init__()
        if data is None:
            self.data = []
        else:
            self.data = [x + [""] for x in data]


    def headerData(self, p_int, Qt_Orientation, role=None):
        headers = ["ID", "Cell Line", "Date", "Compounds", "Concentrations", "Exposure Time", "Graph Legend"]
        if Qt_Orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return headers[p_int]

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self.data)

    def columnCount(self, parent=None, *args, **kwargs):
        return 7

    def flags(self, QModelIndex):
        flags = super().flags(QModelIndex)
        column = QModelIndex.column()

        if column == 6:
            flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

        return flags

    def data(self, QModelIndex, role=None):
        row = QModelIndex.row()
        column = QModelIndex.column()
        if QModelIndex and (role==QtCore.Qt.DisplayRole or role==QtCore.Qt.EditRole):
            return self.data[row][column]

    def setData(self, QModelIndex, Any, role=None):
        row = QModelIndex.row()
        column = QModelIndex.column()
        if role == QtCore.Qt.EditRole:
            self.data[row][column] = Any
            self.dataChanged.emit(QModelIndex, QModelIndex)
            return True

    def deleteExperiment(self, row):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        self.removeRow(row)
        del self.data[row]
        self.endRemoveRows()
        self.number_of_rows -= 1

    def insertExperiment(self, experiment, cell_line):
        self.beginInsertRows(QtCore.QModelIndex(), len(self.data), len(self.data))
        self.insertRow(len(self.data))
        self.data.append([experiment[0]] + [cell_line] + experiment[1:] + [""])
        self.endInsertRows()

class ListModel(QtCore.QAbstractListModel):
    def __init__(self, data):
        super().__init__()
        self.data = data

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self.data)

    def data(self, QModelIndex, role=None):
        row = QModelIndex.row()
        if QModelIndex:
            if role == QtCore.Qt.DisplayRole:
                return self.data[row]

    def add_items(self, items):
        self.beginInsertRows(QtCore.QModelIndex(), len(self.data), len(self.data) + len(items))
        for item in items:
            self.data.append(item)
            self.insertRow(len(self.data))
        self.endInsertRows()

    def remove_items(self, rows):
        for row in sorted(rows, reverse=True):
            self.beginRemoveRows(QtCore.QModelIndex(), row, row)
            self.removeRow(row)
            del self.data[row]
            self.endRemoveRows()



