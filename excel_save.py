from PyQt5 import QtWidgets, QtCore, uic
from models import ListModel
import parsing
import pandas as pd
import re
import numpy as np

class ExcelSaveWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("excel_save.ui", self)
        cells_lst = parsing.grab_cell_lines()
        self.bttnSave.clicked.connect(self.save_excel)
        self.objects_lst = [
            {
                "available_list": self.listCellsAvailable,
                "save_list": self.listCellsSave,
                "available_model": ListModel(cells_lst),
                "save_model": ListModel([]),
                "add_button": self.bttnAddCells,
                "delete_button": self.bttnDeleteCells
            },
            {
                "available_list": self.listCompoundsAvailable,
                "save_list": self.listCompoundsSave,
                "available_model": ListModel(["Ox66", "DEP", "DEP + Ox66"]),
                "save_model": ListModel([]),
                "add_button": self.bttnAddCompounds,
                "delete_button": self.bttnDeleteCompounds
            },
            {
                "available_list": self.listTimesAvailable,
                "save_list": self.listTimesSave,
                "available_model": ListModel(["24 Hours", "48 Hours"]),
                "save_model": ListModel([]),
                "add_button": self.bttnAddTimes,
                "delete_button": self.bttnDeleteTimes
            },
            {
                "available_list": self.listConditionsAvailable,
                "save_list": self.listConditionsSave,
                "available_model": ListModel(["Normoxia", "Hypoxia"]),
                "save_model": ListModel([]),
                "add_button": self.bttnAddConditions,
                "delete_button": self.bttnDeleteConditions
            },
            {
                "available_list": self.listAssaysAvailable,
                "save_list": self.listAssaysSave,
                "available_model": ListModel(["LDH", "MTT"]),
                "save_model": ListModel([]),
                "add_button": self.bttnAddAssays,
                "delete_button": self.bttnDeleteAssays
            }
        ]
        self.setup_models(self.objects_lst)

    def setup_models(self, objects_list):
        for item in objects_list:
            item['available_list'].setModel(item['available_model'])
            item['available_list'].setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            item['save_list'].setModel(item['save_model'])
            item['available_selection_model'] = item['available_list'].selectionModel()
            item['save_list'].setModel(item['save_model'])
            item['save_list'].setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            item['save_selection_model'] = item['save_list'].selectionModel()
            item['add_button'].clicked.connect(lambda state, x=item: self.move_items(
                selection_model=x['available_selection_model'],
                source_model=x['available_model'],
                destination_model=x['save_model']
            ))
            item['delete_button'].clicked.connect(lambda state, x=item: self.move_items(
                selection_model=x['save_selection_model'],
                source_model=x['save_model'],
                destination_model=x['available_model']
            ))

    def move_items(self, selection_model, source_model, destination_model):
        selected_indices = selection_model.selectedIndexes()
        rows = [index.row() for index in selected_indices]
        cells_to_add = [source_model.data[row] for row in rows]
        destination_model.add_items(items=cells_to_add)
        source_model.remove_items(rows)

    def save_excel(self):
        cell_lines = self.objects_lst[0]['save_model'].data
        compounds = self.objects_lst[1]['save_model'].data
        exposure_times = self.objects_lst[2]['save_model'].data
        conditions = self.objects_lst[3]['save_model'].data
        assays = self.objects_lst[4]['save_model'].data
        cells_lst = []
        compound_lst = []
        exposure_time_lst = []
        condition_lst = []
        treatment_lst = []
        response_lst = []
        for cell_line in cell_lines:
            experiments = parsing.grab_experiments(cell_line)
            print(experiments)
            experiments = [experiment for experiment in experiments
                           if experiment[2] in compounds and
                           experiment[4] in exposure_times and
                           experiment[5] in conditions and
                           experiment[6] in assays]

            for experiment in experiments:
                compounds = experiment[2]
                concentrations = [x.strip() for x in experiment[3].split(",")]
                exposure_time = experiment[4]
                condition = experiment[5]
                assay = experiment[6]
                #values = {}
                file_grab_successful = True
                #for concentration in concentrations:
                   #values[concentration] = []
                plates = parsing.grab_plates(cell_line, experiment[0], concentrations)

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
                                coordinates += [int(items[1]) - 1, convert_letter_to_number(items[0])]

                        df = df.iloc[coordinates[0]:coordinates[2] + 1, coordinates[1]:coordinates[3] + 1]

                        if "Blank" in concentrations:
                            rows = plate[3]['Blank']
                            values_blank = []
                            for row in rows:
                                values_blank.append(df[row].values.tolist())
                            scaling_factor = np.mean(values_blank)
                        else:
                            scaling_factor = np.nanmax(df)

                        df_scaled = df / scaling_factor
                        for concentration in concentrations:
                            rows = plate[3][concentration]
                            for row in rows:
                                values = (df_scaled[row].values.tolist())
                                response_lst += values
                                treatment_lst += [concentration] * len(values)
                                cells_lst += [cell_line] * len(values)
                                compound_lst += [compounds] * len(values)
                                condition_lst += [condition] * len(values)
                                exposure_time_lst += [exposure_time] * len(values)

                    except Exception as exc:
                        if exc.args[0] == 2:
                            file_grab_successful = False
                            msgbox = QtWidgets.QMessageBox()
                            msgbox.setText("File not found. Please double check file path")
                            msgbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                            msgbox.exec()
                            break
                        else:
                            raise exc

                    if file_grab_successful:
                        full_data_dict = {"Cells": cells_lst,
                                          "Compound": compound_lst,
                                          "exposure_time": exposure_time_lst,
                                          "condition": condition_lst,
                                          "treatment": treatment_lst,
                                          "response": response_lst}
                        print(len(cells_lst), len(compound_lst), len(exposure_time_lst), len(condition_lst), len(treatment_lst), len(response_lst))
                        full_data_df = pd.DataFrame(data=full_data_dict)
                        print(full_data_df)


def convert_letter_to_number(letter):
    total = 0
    for index, character in enumerate(letter):
        number = ord(character.lower()) - 97
        total += number + 26 * index
    return int(total)