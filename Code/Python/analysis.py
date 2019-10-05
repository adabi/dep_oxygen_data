from PyQt5 import QtCore, QtWidgets, uic
import sys
import pathlib
from parsing import grab_cell_lines, grab_experiments, grab_plates, delete_experiment, delete_plate
from models import ExperimentsModel, PlatesModel
import pandas as pd
import re
from collections import OrderedDict
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from scipy import stats
from comparison import ComparisonWindow
from excel_save import ExcelSaveWindow


class FilterSortingModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def lessThan(self, left, right):
        if max(left.row(), right.row()) == self.sourceModel().rowCount() - 1:
            return False
        return QtCore.QSortFilterProxyModel.lessThan(self, left, right)

    def filterAcceptsRow(self, source_row, source_parent):
        criteria = [x.strip() for x in self.parent.txtFilter.text().split(",")]
        if self.parent.txtFilter.text().strip() == "":
            return True
        else:
            if source_row < self.sourceModel().rowCount() - 1:
                match = True
                for criterion in criteria:
                    match = match and criterion in self.sourceModel().data[source_row]
                return match
            else:
                return True


class PlotDialogBox(QtWidgets.QMainWindow):
    def __init__(self, parent, figure):
        super().__init__(parent=parent)
        uic.loadUi('plotdialog.ui', self)
        self.plotWidget = FigureCanvas(figure)
        lay = QtWidgets.QVBoxLayout(self.content_plot)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.plotWidget)
        # add toolbar
        self.addToolBar(QtCore.Qt.BottomToolBarArea, NavigationToolbar(self.plotWidget, self))


# A delegate dropbox for insertion into the experiments table view
class DelegateDropBox(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent, field):
        super().__init__(parent)
        self.field = field

    def createEditor(self, QWidget, QStyleOptionViewItem, QModelIndex):
        combo_box = QtWidgets.QComboBox()
        combo_box.setParent(QWidget)
        combo_box.setStyle(QWidget.style())
        combo_box.setFocusPolicy(QtCore.Qt.StrongFocus)
        if self.field == "Condition":
            items_to_add = ["Normoxia", "Hypoxia"]
        elif self.field == "Assay":
            items_to_add = (["LDH", "MTT"])
        elif self.field == "Exposure Time":
            items_to_add = ["24 Hours", "48 Hours"]
        else:
            items_to_add = ["DEP", "Ox66", "DEP + Ox66"]
        combo_box.addItems(items_to_add)
        return combo_box

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('maininterface.ui', self)
        cell_lines = grab_cell_lines()
        self.comboCellLines.addItems(cell_lines)
        self.current_cell_line = self.comboCellLines.currentText()
        experiments = grab_experiments(self.comboCellLines.currentText())
        self.experiments_model = ExperimentsModel(experiments, self.comboCellLines.currentText())
        self.proxyModel = FilterSortingModel(parent=self)
        self.tableExperiments.setSortingEnabled(True)
        self.proxyModel.setSourceModel(self.experiments_model)
        self.tableExperiments.setModel(self.proxyModel)
        self.d_assay_drop_box = DelegateDropBox(self.tableExperiments, field="Assay")
        self.d_condition_drop_box = DelegateDropBox(self.tableExperiments, field="Condition")
        self.d_exposure_time_drop_box = DelegateDropBox(self.tableExperiments, field="Exposure Time")
        self.d_compounds_drop_box = DelegateDropBox(self.tableExperiments, field="Compounds")
        self.tableExperiments.setItemDelegateForColumn(2, self.d_compounds_drop_box)
        self.tableExperiments.setItemDelegateForColumn(4, self.d_exposure_time_drop_box)
        self.tableExperiments.setItemDelegateForColumn(5, self.d_condition_drop_box)
        self.tableExperiments.setItemDelegateForColumn(6, self.d_assay_drop_box)
        self.proxyModel.setDynamicSortFilter(False)
        self.proxyModel.sort(0, QtCore.Qt.AscendingOrder)
        self.tableExperiments.setColumnWidth(3, 350)
        self.tableExperiments.horizontalHeader().setStretchLastSection(True)
        self.tableExperiments.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableExperiments.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.experimentsSelectionModel = self.tableExperiments.selectionModel()
        self.bttnAddPlates.clicked.connect(self.add_plates)
        self.tableExperiments.selectionModel().selectionChanged.connect(self.experiment_selected)
        self.tablePlates.doubleClicked.connect(self.open_file_dialog)
        self.bttnDeleteExperiment.clicked.connect(self.delete_experiment)
        self.bttnDeletePlate.clicked.connect(self.delete_plate)
        self.tablePlates.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tablePlates.setSelectionMode(QtWidgets.QAbstractItemView.ContiguousSelection)
        self.bttnPlot.clicked.connect(self.plot)
        self.comboCellLines.currentTextChanged.connect(self.new_cell_line)
        self.bttnExcel.clicked.connect(self.save_to_excel)
        self.bttnCompare.clicked.connect(self.openComparisonWindow)
        self.bttnCopy.clicked.connect(self.copy_concentrations)
        self.bttnPaste.clicked.connect(self.paste_concentrations)
        self.bttnPaste.setEnabled(False)
        self.txtFilter.textChanged.connect(self.filter_txt_changed)
        self.plates_model = PlatesModel([], None, None, [], None)
        self.platesSelectionModel = self.tablePlates.selectionModel()
        self.tablePlates.setModel(self.plates_model)

    def center(self):
        frameGm = self.frameGeometry()
        centerPoint = QtWidgets.QDesktopWidget().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def experiment_selected(self, selected):
        indices = selected.indexes()
        index = self.proxyModel.mapToSource(indices[0])
        row = index.row()
        if row < self.experiments_model.number_of_rows - 1:
            experiment = self.experiments_model.data[row][0]
            concentrations = self.experiments_model.data[row][3]
            assay = self.experiments_model.data[row][6]
            cell_line = self.comboCellLines.currentText()
            concentrations = [x.strip() for x in concentrations.split(",")]
            plates= grab_plates(cell_line, experiment)
            self.plates_model.resetModel(plates, cell_line, experiment, concentrations, assay)
            self.platesSelectionModel = self.tablePlates.selectionModel()
            self.comboSignificant.clear()
            self.comboSignificant.addItems(concentrations)
            if "Blank" in concentrations:
                self.comboSignificant.setCurrentText("Blank")
            self.comboNormalize.clear()
            self.comboNormalize.addItem("None")
            self.comboNormalize.addItems(concentrations)
            if "Blank" in concentrations:
                self.comboNormalize.setCurrentText("Blank")

    def open_file_dialog(self, index):
        column = index.column()

        if column == 1:
            dialog = QtWidgets.QFileDialog()
            dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
            if dialog.exec():
                selected_file = dialog.selectedFiles()[0]
                self.plates_model.setData(index, selected_file, QtCore.Qt.EditRole)

    @staticmethod
    def find_table_in_file(file):
        if file.is_file():
            ranges_list = []
            try:
                df = pd.read_excel(file, header=None)
            except Exception as exc:
                print(exc)

            criteria = df.astype(str).eq("A").any(0)
            columns_contaning_A = criteria.index[criteria]
            for column in columns_contaning_A:
                df_sliced = df[columns_contaning_A]
                rows_containing_A = df_sliced.eq("A").any(1).index[df_sliced.eq("A").any(1)]
                first_row = df.iloc[rows_containing_A[0] - 1]
                last_column = (first_row.isnull().index[first_row.isnull()])[1]
                null_rows = df[column].isnull().index[df[column].isnull()]

                last_rows = []
                for i, row in enumerate(null_rows):
                    if row < rows_containing_A[0] - 0:
                        pass

                    elif i > 0:
                        if row == null_rows[i - 1] + 1:
                            pass
                        else:
                            last_rows.append(row)
                    else:
                        last_rows.append(row)

                if len(last_rows) < len(rows_containing_A):
                    last_rows.append(len(df[column]) + 1)

                for i, row in enumerate(rows_containing_A):
                    ranges_list.append([row, last_rows[i] - 1, column + 1, last_column - 1])

            return ranges_list

    def add_plates(self):
        dialog = QtWidgets.QFileDialog()
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        if dialog.exec():
            selected_file = pathlib.PureWindowsPath(dialog.selectedFiles()[0]).as_posix()
            selected_file = pathlib.Path(selected_file)
            try:
                selected_file_tostore = selected_file.relative_to(pathlib.Path.cwd().parent.parent)
            except Exception as exc:
                print(exc)
                selected_file_tostore = selected_file
            ranges_list = self.find_table_in_file(selected_file)

            for plate_range in ranges_list:
                range_literal = (convert_number_to_letter(plate_range[2]) + str(plate_range[0] + 1) + ":" +
                                 convert_number_to_letter(plate_range[3]) + str(plate_range[1] + 1))

                index = self.plates_model.createIndex(self.plates_model.number_of_rows - 1, 1)
                self.plates_model.setData(index, str(selected_file_tostore), role=QtCore.Qt.EditRole)

                index = self.plates_model.createIndex(self.plates_model.number_of_rows - 2, 2)
                self.plates_model.setData(index, range_literal, QtCore.Qt.EditRole)

    def delete_experiment(self):
        indices = self.experimentsSelectionModel.selectedIndexes()
        index = self.proxyModel.mapToSource(indices[0])
        row = index.row()

        if row < self.experiments_model.number_of_rows - 1:
            cell_line = self.comboCellLines.currentText()
            experiment = self.experiments_model.data[row][0]
            delete_experiment(cell_line, experiment)
            self.experiments_model.deleteExperiment(row)

    def delete_plate(self):
        indices = self.platesSelectionModel.selectedIndexes()
        for index in indices:
            row = index.row()
            if row < self.plates_model.number_of_rows - 1:
                cell_line = self.comboCellLines.currentText()
                experiment = self.plates_model.experiment
                plate = self.plates_model.data[row][0]
                delete_plate(cell_line, experiment, plate)
                self.plates_model.deletePlate(row)

    def plot(self):
        concentrations = self.plates_model.concentrations
        assay = self.plates_model.assay
        values = OrderedDict()
        file_grab_successful = True
        for concentration in concentrations:
            values[concentration] = []
        for item in self.plates_model.data:
            try:
                file = item[1]
                file = pathlib.Path.cwd().parent.parent.joinpath(file)
                df = pd.read_excel(file, header=None)
                coordinates = []
                # Split the range down the : character
                range_split = item[2].split(":")
                # Parse each half of the split range into a row, column and then add to the list
                for range_plate in range_split:
                    match = re.match(r"([a-z]+)([0-9]+)", range_plate, re.I)
                    if match:
                        items = match.groups()
                        coordinates += [int(items[1]) - 1, convert_letter_to_number(items[0])]

                df = df.iloc[coordinates[0]:coordinates[2] + 1, coordinates[1]:coordinates[3] + 1]
                df_normalized = df / np.nanmax(df)
                for concentration in concentrations:
                    rows = item[3][concentration]
                    for row in rows:
                        values[concentration] += (df_normalized[row].values.tolist())
            except Exception as exc:
                if exc.args[0] == 2:
                    print(exc)
                    file_grab_successful = False
                    msgbox = QtWidgets.QMessageBox()
                    msgbox.setText("File not found. Please double check file path")
                    msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                    msgbox.exec()
                    break
                else:
                    print(exc)
                    break

        if file_grab_successful:
            values_mean = OrderedDict()
            significance = []

            for index, concentration in enumerate(values):

                if self.comboNormalize.currentText() == "None":
                    values_mean[concentration] = np.mean(values[concentration])
                else:
                    values_mean[concentration] = np.mean(values[concentration]) / np.mean(
                        values[self.comboNormalize.currentText()])

                t, p_value = stats.mannwhitneyu(values[self.comboSignificant.currentText()], values[concentration])
                if p_value < 0.05:
                    significance.append(index)


            y_pos = np.arange(len(concentrations))

            #figure = plt.figure()
            figure, ax = plt.subplots()
            rects = ax.bar(y_pos, values_mean.values(), align='center', alpha=0.5)
            ax.set_xticks(y_pos)
            ax.set_xticklabels(concentrations)
            max_value = max(values_mean.values())
            ax.set_ylim(0, max_value + 0.15)
            selected_row = self.experimentsSelectionModel.selectedIndexes()[0].row()
            comment = self.experiments_model.data[selected_row][2] + " - " + self.experiments_model.data[selected_row][4]
            if assay == "LDH":
                ax.set_ylabel('LDH (Cell Damage)')
                ax.set_title(f'{self.current_cell_line} - LDH ({comment})')
            else:
                ax.set_ylabel('MTT (Cell Viability)')
                ax.set_title(f'{self.current_cell_line} - MTT ({comment})')

            def autolabel(rects, xpos='center', significant= None):
                """
                Attach a text label above each bar in *rects*, displaying its height.

                *xpos* indicates which side to place the text w.r.t. the center of
                the bar. It can be one of the following {'center', 'right', 'left'}.
                """
                if significant is None:
                    significant = []

                ha = {'center': 'center', 'right': 'left', 'left': 'right'}
                offset = {'center': 0, 'right': 1, 'left': -1}

                for index, rect in enumerate(rects):
                    height = rect.get_height()
                    ax.annotate('{}'.format(round(height, 2)),
                                xy=(rect.get_x() + rect.get_width() / 2, height),
                                xytext=(offset[xpos] * 3, 3),  # use 3 points offset
                                textcoords="offset points",  # in both directions
                                ha=ha[xpos], va='bottom')

                    if index in significant:
                        ax.annotate("*", xy=(rect.get_x() + rect.get_width() /2, height + 0.03),
                                    xytext=(0, 3),
                                    textcoords="offset points",
                                    ha = 'center', va='bottom', color='red', weight='bold')

            autolabel(rects, significant=significance)
            self.plotDialog = PlotDialogBox(parent=self, figure=figure)
            self.plotDialog.show()

    def new_cell_line(self):
        experiments = grab_experiments(self.comboCellLines.currentText())
        self.experiments_model.resetModel(experiments, self.comboCellLines.currentText())


    def save_to_excel(self):
        excel_window = ExcelSaveWindow()
        excel_window.show()


    def openComparisonWindow(self):
        self.comparison_window = ComparisonWindow()
        self.comparison_window.show()

    def copy_concentrations(self):
        self.copied_dict = [x[3] for x in self.plates_model.data]
        self.bttnPaste.setEnabled(True)

    def paste_concentrations(self):
        self.plates_model.pasteRows(self.copied_dict)

    def filter_txt_changed(self):
        self.proxyModel.setFilterKeyColumn(0)

def convert_letter_to_number(letter):
    total = 0
    for index, character in enumerate(letter):
        number = ord(character.lower()) - 97
        total += number + 26 * index
    return int(total)


def convert_number_to_letter(number):
    number += 1
    letter_list = []
    letter = ""
    while True:
        if number == 0:
            break
        else:
            letter_list.insert(0, number % 26)
            number = number // 26

    for item in letter_list:
        letter += chr(item + 64)
        return letter

sys._excepthook = sys.excepthook
def exception_hook(exctype, value, traceback):
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)
sys.excepthook = exception_hook

app = QtWidgets.QApplication(sys.argv)
main_win = MainWindow()
main_win.show()
main_win.center()
sys.exit(app.exec_())

