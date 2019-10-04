from PyQt5 import QtWidgets, QtCore, uic
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from parsing import grab_cell_lines, grab_experiments, grab_plates
from models import ExperimentsModel, CompareModel
from collections import OrderedDict
from itertools import chain
import re
import pandas as pd
from scipy import stats

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

class ComparisonWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("compare_window.ui", self)
        self.cell_lines = grab_cell_lines()
        self.comboCellLines.addItems(self.cell_lines)
        self.current_cell_line = self.comboCellLines.currentText()
        self.comboCellLines.currentTextChanged.connect(self.grabExperiments)
        self.grabExperiments()
        self.tableExperiments.setColumnWidth(3, 350)
        self.tableExperiments.horizontalHeader().setStretchLastSection(True)
        self.tableExperiments.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableExperiments.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.experimentsSelectionModel = self.tableExperiments.selectionModel()
        self.bttnAdd.clicked.connect(self.add_experiment)
        self.compare_model = CompareModel()
        self.tableComparison.setModel(self.compare_model)
        self.tableComparison.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableComparison.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.comboNormalize.addItems(["Blank"])
        self.comboSignificance.addItems(["Blank"])
        self.bttnLDH.clicked.connect(self.plotLDH)
        self.bttnMTT.clicked.connect(self.plotMTT)


    def grabExperiments(self):
        self.current_cell_line = self.comboCellLines.currentText()
        data = grab_experiments(self.current_cell_line)
        self.experiments_model = ExperimentsModel(data, self.current_cell_line)
        self.tableExperiments.setModel(self.experiments_model)
        self.experimentsSelectionModel = self.tableExperiments.selectionModel()

    def add_experiment(self):
        row = self.experimentsSelectionModel.selectedIndexes()[0].row()
        experiment = self.experiments_model.data[row][0:5]
        concentrations = self.experiments_model.data[row][3]
        concentrations = [x.strip() for x in concentrations.split(",")]
        self.compare_model.insertExperiment(experiment, self.current_cell_line)
        self.comboNormalize.clear()
        self.comboNormalize.addItem("None")
        self.comboNormalize.addItems(concentrations)
        self.comboSignificance.clear()
        self.comboSignificance.addItem("None")
        self.comboSignificance.addItems(concentrations)

    def plotLDH(self):
        grouped_values = []
        std_errors = []
        significance = []
        for item in self.compare_model.data:
            print(item)
            cell_line = item[1]
            experiment = item[0]
            concentrations = item[4]
            concentrations = [x.strip() for x in concentrations.split(",")]
            concentrations_dict = {}
            for concentration in concentrations:
                concentrations_dict[concentration] = []
            plates = grab_plates(cell_line, experiment, concentrations_dict)
            values = OrderedDict()
            file_grab_successful = True
            for concentration in concentrations:
                values[concentration] = []
            for plate in plates:
                try:
                    df = pd.read_excel(plate[1], header=None)

                    coordinates = []
                    # Split the range down the : character
                    range_split = plate[2].split(":")
                    # Parse each half of the split range into a row, column and then add to the list
                    for range_plate in range_split:
                        match = re.match(r"([a-z]+)([0-9]+)", range_plate, re.I)
                        if match:
                            items = match.groups()
                            coordinates += [int(items[1]) - 1, self.convert_letter_to_number(items[0])]
                    df = df.iloc[coordinates[0]:coordinates[2] + 1, coordinates[1]:coordinates[3] + 1]
                    df_normalized = df / df.max(numeric_only=True).max()
                    for concentration in concentrations:
                        rows = plate[3][concentration]
                        for row in rows:
                            values[concentration] += list(df_normalized[row])

                except Exception as exc:
                    if exc.args[0] == 2:
                        file_grab_successful = False
                        msgbox = QtWidgets.QMessageBox()
                        msgbox.setText("File not found. Please double check file path")
                        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                        msgbox.exec()
                        break

            if file_grab_successful:

                values_mean = OrderedDict()
                std_error_lst = []
                significance_lst = []
                print(values)
                for index, concentration in enumerate(values):
                    std_error = stats.sem(values[concentration])

                    if self.comboNormalize.currentText() == "None":
                        values_mean[concentration] = np.mean(values[concentration])
                    else:
                        values_mean[concentration] = np.mean(values[concentration]) / np.mean(
                            values[self.comboNormalize.currentText()])
                        std_error = std_error/ np.mean(
                            values[self.comboNormalize.currentText()])
                    std_error_lst.append(std_error)
                    if self.comboSignificance.currentText() != "None":
                        compare_to_concentration = self.comboSignificance.currentText()
                        t, p_value = stats.mannwhitneyu(values[compare_to_concentration],
                                                        values[concentration])
                        if p_value < 0.05:
                            significance_lst.append(index)

                grouped_values.append(list(values_mean.values()))
                std_errors.append(std_error_lst)
                significance.append(significance_lst)
        print(grouped_values)
        combined_group_values = list(chain(*grouped_values))
        combined_standard_erros = list(chain(*std_errors))
        added_list = [sum(x) for x in zip(combined_group_values, combined_standard_erros)]
        max_height = max(added_list)

        #print(heights)
        N = len(concentrations)
        fig, ax = plt.subplots()
        ax.set_ylim(0, max_height + 0.2)
        width = 0.3
        total_x_length = (int(width * len(grouped_values)) + 1) * len(concentrations)
        ind = np.arange(start=0, stop=total_x_length, step=total_x_length/len(concentrations))
        graph_lst = []

        for index, values in enumerate(grouped_values):
            if index == 0:
                graph_lst.append(ax.bar(ind, list(values), width, yerr=std_errors[index],error_kw=dict(capsize=2), label=self.compare_model.data[index][6]))
            else:
                graph_lst.append(ax.bar(ind + width*index, list(values), width, yerr=std_errors[index], error_kw=dict(capsize=2), label=self.compare_model.data[index][6]))
        x_tick_positions = ind + width*len(grouped_values)/2 - width/2
        ax.set_xticks(x_tick_positions)
        ax.set_xticklabels(concentrations)
        ax.set_title(self.txtGraphTitle.text())
        ax.set_ylabel("LDH (Cell Damage)")
        ax.set_xlabel("Concentration")
        ax.legend()
        def auto_label(graphs, xpos='center', significant=None):
            ha = {'center': 'center', 'right': 'left', 'left': 'right'}
            offset = {'center': 0, 'right': 1, 'left': -1}
            for index, graph in enumerate(graphs):
                for rect_index, rect in enumerate(graph):
                    height=rect.get_height()
                    if rect_index in significance[index]:
                        ax.annotate("*", xy=(rect.get_x() + rect.get_width() /2, height + std_errors[index][rect_index] + 0.005),
                                    xytext=(0, 3),
                                    textcoords="offset points",
                                    ha = 'center', va='bottom', color='red', weight='bold')
        auto_label(graph_lst)
        self.plotDialog = PlotDialogBox(parent=self, figure=fig)
        self.plotDialog.show()

    @staticmethod
    def convert_letter_to_number(letter):
        total = 0
        for index, character in enumerate(letter):
            number = ord(character.lower()) - 97
            total += number + 26 * index
        return int(total)

    @staticmethod
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

    def plotMTT(self):
        grouped_values = []
        std_errors = []
        significance = []
        for item in self.compare_model.data:
            print(item)
            cell_line = item[1]
            experiment = item[0]
            concentrations = item[4]
            concentrations = [x.strip() for x in concentrations.split(",")]
            concentrations_dict = {}
            for concentration in concentrations:
                concentrations_dict[concentration] = []
            plates = grab_plates(cell_line, experiment, concentrations_dict)
            values = OrderedDict()
            file_grab_successful = True
            for concentration in concentrations:
                values[concentration] = []
            for plate in plates:
                try:
                    df = pd.read_excel(plate[1], header=None)

                    coordinates = []
                    # Split the range down the : character
                    range_split = plate[2].split(":")
                    # Parse each half of the split range into a row, column and then add to the list
                    for range_plate in range_split:
                        match = re.match(r"([a-z]+)([0-9]+)", range_plate, re.I)
                        if match:
                            items = match.groups()
                            coordinates += [int(items[1]) - 1, self.convert_letter_to_number(items[0])]
                    df = df.iloc[coordinates[0]:coordinates[2] + 1, coordinates[1]:coordinates[3] + 1]
                    df_normalized = df / df.max(numeric_only=True).max()
                    for concentration in concentrations:
                        rows = plate[3][concentration]
                        for row in rows:
                            values[concentration] += list(df_normalized[row])

                except Exception as exc:
                    if exc.args[0] == 2:
                        file_grab_successful = False
                        msgbox = QtWidgets.QMessageBox()
                        msgbox.setText("File not found. Please double check file path")
                        msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                        msgbox.exec()
                        break

            if file_grab_successful:

                values_mean = OrderedDict()
                std_error_lst = []
                significance_lst = []
                print(values)
                for index, concentration in enumerate(values):
                    std_error = stats.sem(values[concentration])

                    if self.comboNormalize.currentText() == "None":
                        values_mean[concentration] = np.mean(values[concentration])
                    else:
                        values_mean[concentration] = np.mean(values[concentration]) / np.mean(
                            values[self.comboNormalize.currentText()])
                        std_error = std_error/ np.mean(
                            values[self.comboNormalize.currentText()])
                    std_error_lst.append(std_error)
                    if self.comboSignificance.currentText() != "None":
                        compare_to_concentration = self.comboSignificance.currentText()
                        t, p_value = stats.mannwhitneyu(values[compare_to_concentration],
                                                        values[concentration])
                        if p_value < 0.05:
                            significance_lst.append(index)

                grouped_values.append(list(values_mean.values()))
                std_errors.append(std_error_lst)
                significance.append(significance_lst)
        print(grouped_values)
        combined_group_values = list(chain(*grouped_values))
        combined_standard_erros = list(chain(*std_errors))
        added_list = [sum(x) for x in zip(combined_group_values, combined_standard_erros)]
        max_height = max(added_list)

        #print(heights)
        N = len(concentrations)
        fig, ax = plt.subplots()
        ax.set_ylim(0, max_height + 0.2)
        width = 0.3
        total_x_length = (int(width * len(grouped_values)) + 1) * len(concentrations)
        ind = np.arange(start=0, stop=total_x_length, step=total_x_length/len(concentrations))
        graph_lst = []

        for index, values in enumerate(grouped_values):
            if index == 0:
                graph_lst.append(ax.bar(ind, list(values), width, yerr=std_errors[index],error_kw=dict(capsize=2), label=self.compare_model.data[index][6]))
            else:
                graph_lst.append(ax.bar(ind + width*index, list(values), width, yerr=std_errors[index], error_kw=dict(capsize=2), label=self.compare_model.data[index][6]))
        x_tick_positions = ind + width*len(grouped_values)/2 - width/2
        ax.set_xticks(x_tick_positions)
        ax.set_xticklabels(concentrations)
        ax.set_title(self.txtGraphTitle.text())
        ax.set_ylabel("MTT (Viability)")
        ax.set_xlabel("Concentration")
        ax.legend()
        def auto_label(graphs, xpos='center', significant=None):
            ha = {'center': 'center', 'right': 'left', 'left': 'right'}
            offset = {'center': 0, 'right': 1, 'left': -1}
            for index, graph in enumerate(graphs):
                for rect_index, rect in enumerate(graph):
                    height=rect.get_height()
                    if rect_index in significance[index]:
                        ax.annotate("*", xy=(rect.get_x() + rect.get_width() /2, height + std_errors[index][rect_index] + 0.005),
                                    xytext=(0, 3),
                                    textcoords="offset points",
                                    ha = 'center', va='bottom', color='red', weight='bold')
        auto_label(graph_lst)
        self.plotDialog = PlotDialogBox(parent=self, figure=fig)
        self.plotDialog.show()