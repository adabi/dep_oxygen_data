import re
import pathlib
from collections import OrderedDict

def grab_cell_lines():
    cell_lines = []
    f = open("Data.ad", encoding='utf-8')
    for index, line in enumerate(f):
        if line[0] == "{":
            cell_lines.append (f.__next__().split("=")[1].split("\"")[1])

    return (cell_lines)


def grab_experiments(cell_line):

    f = open("Data.ad", encoding='utf-8')
    experiments_start_at = 0
    for index, line in enumerate(f, start=0):
        if line[0] == "{" and f.__next__().split("=")[1].split("\"")[1] == cell_line:
            experiments_start_at = index + 1
            break

    experiments = []
    experiment = None
    for index, line in enumerate(f, start=experiments_start_at):


        if line[0] == "}":
            break

        if len(line) > 1:
            if line[1] == "}" and experiment is not None:
                experiments.append([experiment, date, compounds, concentrations, exposure_time,condition,assay, comments])

        if line.split("=")[0] == "\texperiment":
            experiment = int(line.split("=")[1].split("\"")[1])

        if line.split("=")[0] == "\tdate":
            date = line.split("=")[1].split("\"")[1]

        if line.split("=")[0] == "\tcompounds":
            compounds = line.split("=")[1].split("\"")[1]

        elif line.split("=")[0] == "\tconcentrations":
            concentrations = line.split("=")[1].split("\"")[1]

        elif line.split("=")[0] == "\texposure_time":
            exposure_time = line.split("=")[1].split("\"")[1]

        elif line.split("=")[0] == "\tcondition":
            condition = line.split("=")[1].split("\"")[1]

        elif line.split("=")[0] == "\tassay":
            assay = line.split("=")[1].split("\"")[1]

        elif line.split("=")[0] == "\tcomments":
            comments = line.split("=")[1].split("\"")[1]



    return experiments


def grab_plates(cell_line, experiment):

    f = open("Data.ad", encoding='utf-8')
    experiments_start_at = 0
    current_experiment_starts_at = 0
    plates = []
    for index, line in enumerate(f):
        if len(line) > 9 and line [0:9] == "cell_line":
            if line.split("=")[1].split("\"")[1] == cell_line:
                experiments_start_at = index - 1
                break

    for index, line in enumerate(f, start=experiments_start_at + 2):
        if line[0] == "}":
            break

        if len(line) > 11 and line[1:11] == "experiment":
            if line.split("=")[1].split("\"")[1] == str(experiment):
                current_experiment_starts_at = index - 1
                break
    for index, line in enumerate(f, start=current_experiment_starts_at + 2):

        if len(line) > 1:
            if line[1] == "}":

                break

        if len(line) > 4:

            if line[0:2] == "\t\t":

                if line.split("=")[0] == "\t\tplate":
                    plate = line.split("=")[1].split("\"")[1]

                elif  line.split("=")[0] == "\t\tfile":
                    file = line.split("=")[1].split("\"")[1]

                elif line.split("=")[0] == "\t\trange":
                    range = line.split("=")[1].split("\"")[1]

                elif line.split("=")[0] == "\t\tconcentrations":
                    concentrations = prase_concentrations(line.split("=")[1])

        if len(line) > 3:
            if line[2] == "}":
                file = pathlib.Path(file)
                to_append = ([plate, file, range, dict(concentrations)])
                plates.append(to_append)

    return plates

def add_experiment(cell_line, experiment, date, compounds, concentrations, exposure_time, condition, assay, comments):
    f = open("Data.ad")
    cell_line_starts_at = 0
    experiments_end_at = 0
    for index, line in enumerate(f):
        if len(line) > 8:
            if line.split("=")[0] == "cell_line":
                if line.split("=")[1].split("\"")[1] == cell_line:
                    cell_line_starts_at = index
                    break

    for index, line in enumerate(f, start = cell_line_starts_at):
        if line[0] == "}":
            experiments_end_at = index
            break

    with open("Data.ad", encoding='utf-8') as file:

        buf = file.readlines()
        file.close()

    with open("Data.ad", "w") as out_file:
        buf.insert(experiments_end_at +1 , ("\t{\n"
                                            f"\texperiment=\"{experiment}\"\n" 
                                            f"\tdate=\"{date}\"\n" 
                                            f"\tcompounds=\"{compounds}\"\n"
                                            f"\tconcentrations=\"{concentrations}\"\n"
                                            f"\texposure_time=\"{exposure_time}\"\n"
                                            f"\tcondition=\"{condition}\"\n"
                                            f"\tassay=\"{assay}\"\n"
                                            f"\tcomments=\"{comments}\"\n"
                                            "\t}\n"))
        buf = "".join(buf)
        out_file.write(buf)
        out_file.close()

    f.close()

def add_plate(cell_line, experiment, plate, file_location, range, concentrations):
    f = open("Data.ad")
    cell_line_starts_at = 0
    experiment_starts_at = 0
    plates_end_at = 0

    for index, line in enumerate(f):
        if len(line) > 8:
            if line.split("=")[0] == "cell_line":
                if line.split("=")[1].split("\"")[1] == cell_line:
                    cell_line_starts_at = index - 1
                    break

    for index, line in enumerate(f, start= cell_line_starts_at + 2):
        if len(line) > 10:
            if line.split("=")[0] == "\texperiment":
                if line.split("=")[1].split("\"")[1] == str(experiment):
                    experiment_starts_at = index - 1
                    break


    for index, line in enumerate(f, start=experiment_starts_at + 2):
        if len(line) > 1:
            if line[1] == "}":
                plates_end_at = index - 1
                break

    with open("Data.ad", encoding='utf-8') as file:

        buf = file.readlines()
        file.close()

    with open("Data.ad", "w") as out_file:
        string_to_add = ("\t\t{\n"
                         f"\t\tplate=\"{plate}\"\n"
                         f"\t\tfile=\"{file_location}\"\n"
                         f"\t\trange=\"{range}\"\n"
                         f"\t\tconcentrations={concentrations}\n"
                         "\t\t}\n")


        buf.insert(plates_end_at +1 , string_to_add)
        buf = "".join(buf)
        out_file.write(buf)
        out_file.close()

    f.close()


def modify_experiment(cell_line, experiment, field, new):
    line_to_replace = None
    f = open("Data.ad")
    cell_line_starts_at = 0
    experiment_starts_at=0

    for index, line in enumerate(f):
        if len(line) > 8:
            if line.split("=")[0] == "cell_line":
                if line.split("=")[1].split("\"")[1] == cell_line:
                    cell_line_starts_at = index - 1
                    break


    for index, line in enumerate(f, start=cell_line_starts_at + 2):
        if len(line) > 10:
            if line.split("=")[0] == "\texperiment":
                if line.split("=")[1].split("\"")[1] == str(experiment):
                    experiment_starts_at = index - 1
                    break

    for index, line in enumerate(f, start=experiment_starts_at + 2):
        if len(line) > 1:
            if line.split("=")[0] == f"\t{field}":
                line_to_replace = index
            elif line[1] == "}":
                break

    if line_to_replace is None:
        print("Error: Couldn't find the experiment or field")

    else:
        with open("Data.ad", encoding='utf-8') as file:

            buf = file.readlines()

        with open("Data.ad", "w") as out_file:
            buf[line_to_replace] = f"\t{field}=\"{new}\"\n"
            buf = "".join(buf)
            out_file.write(buf)
            out_file.close()

def modify_plate(cell_line, experiment, plate, field, new):
    line_to_replace = None
    f = open("Data.ad")
    cell_line_starts_at = 0
    experiment_starts_at = 0
    current_plate_starts_at = 0
    line_to_replace = None
    for index, line in enumerate(f):
        if len(line) > 8:
            if line.split("=")[0] == "cell_line":
                if line.split("=")[1].split("\"")[1] == cell_line:
                    cell_line_starts_at = index - 1
                    break


    for index, line in enumerate(f, start=cell_line_starts_at + 2):
        if len(line) > 10:
            if line.split("=")[0] == "\texperiment":
                if line.split("=")[1].split("\"")[1] == str(experiment):
                    experiment_starts_at = index - 1
                    break



    for index, line in enumerate(f, start=experiment_starts_at + 2):
        if len(line) > 6:
            if line[2:7] == "plate":
                if line.split("=")[1].split("\"")[1] == plate:
                    current_plate_starts_at = index - 1
                    break



    for index, line in enumerate(f, start=current_plate_starts_at + 2):
        if len(line) > 2:
            if line[2] == "}":
                break
            else:
                if line.split("=")[0] == f"\t\t{field}":
                    line_to_replace = index
                    break

    if line_to_replace is None:
        print("Error. Couldn't find the field.")

    else:
        with open("Data.ad", "r") as file:
            buf = file.readlines()


        with open("Data.ad", "w+") as file:
            if field == "concentrations":
                buf[line_to_replace] = f"\t\t{field}={new}\n"
            else:
                buf[line_to_replace] = f"\t\t{field}=\"{new}\"\n"
            buf = "".join(buf)
            file.write(buf)



def delete_plate(cell_line, experiment, plate):
    f = open("Data.ad")
    cell_line_starts_at = 0
    experiment_starts_at = 0
    plate_ends_at = 0
    plate_starts_at=0

    for index, line in enumerate(f):
        if len(line) > 8:
            if line.split("=")[0] == "cell_line":
                if line.split("=")[1].split("\"")[1] == cell_line:
                    cell_line_starts_at = index - 1
                    break

    for index, line in enumerate(f, start= cell_line_starts_at + 2):
        if len(line) > 10:
            if line.split("=")[0] == "\texperiment":
                if line.split("=")[1].split("\"")[1] == str(experiment):
                    experiment_starts_at = index - 1
                    break

    for index, line in enumerate(f, start=experiment_starts_at + 2):
        if len(line) > 6:
            if line.split("=")[0] == "\t\tplate":
                if line.split("=")[1].split("\"")[1] == plate:
                    plate_starts_at = index - 1
                    break

    for index, line in enumerate(f, start=plate_starts_at + 2):
        if len(line) > 2:
            if line[2] == "}":
                plate_ends_at = index
                break

    with open("Data.ad", encoding='utf-8') as file:

        buf = file.readlines()

    with open("Data.ad", "w") as out_file:
        del buf[plate_starts_at: plate_ends_at + 1]
        buf = "".join(buf)
        out_file.write(buf)
        out_file.close()


def delete_experiment(cell_line, experiment):

    f = open("Data.ad")
    cell_line_starts_at = 0
    experiment_starts_at=0
    experiment_ends_at = 0

    for index, line in enumerate(f):
        if len(line) > 8:
            if line.split("=")[0] == "cell_line":
                if line.split("=")[1].split("\"")[1] == cell_line:
                    cell_line_starts_at = index
                    break


    for index, line in enumerate(f, start=cell_line_starts_at):
        if len(line) > 10:
            if line.split("=")[0] == "\texperiment":
                if line.split("=")[1].split("\"")[1] == str(experiment):
                    experiment_starts_at = index
                    break

    for index, line in enumerate(f, start=experiment_starts_at):
        if len(line) > 1:
            if line[1] == "}":
                experiment_ends_at = index + 2
                break

    if experiment_starts_at == 0 or experiment_ends_at == 0:
        print("Error. Couldn't find the experiment to delete in the data file")
    else:
        with open("Data.ad", encoding='utf-8') as file:

            buf = file.readlines()

        with open("Data.ad", "w") as out_file:
            del buf[experiment_starts_at : experiment_ends_at + 1]
            buf = "".join(buf)
            out_file.write(buf)
            out_file.close()


def prase_concentrations(line):
    items = re.findall(r'\[.*?\]:\[.*?\]', line)
    concentrations_dict = OrderedDict()

    for item in items:
        concentration = item.split(":")[0].strip()[1:-1]
        rows = item.split(":")[1].strip()[1:-1]
        rows = [int(x) for x in rows.split(",") if x != '']
        concentrations_dict[concentration] = rows

    return (concentrations_dict)

