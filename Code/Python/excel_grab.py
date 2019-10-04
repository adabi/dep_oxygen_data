import pandas as pd


def findTablesinFile(file):
    ranges_list = []
    df = pd.read_excel(file, header=None)
    criteria = df.eq("A").any(0)
    columns_contaning_A = criteria.index[criteria]
    df_list = []
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
                if row == null_rows[i-1] + 1:
                    pass
                else:
                    last_rows.append(row)
            else:
                last_rows.append(row)
        if len(last_rows) < len(rows_containing_A):
            last_rows.append(len(df[column]) + 1)

        for i, row in enumerate(rows_containing_A):
            df_list.append(df.loc[row: last_rows[i] - 1, column+1:last_column-1])
            ranges_list.append([row, last_rows[i] - 1, column+1, last_column-1])

    return df_list, ranges_list


def convert_letter_to_number(letter):
    total = 0
    for index, character in enumerate(letter):
        number = ord(character.lower()) - 97
        total += number + 26*index
    return int(total)


def convert_number_to_letter(number):
    number += 1
    letter_list = []
    letter = ""
    while True:
        if number == 0:
            break
        else:
            letter_list.insert(0, number%26)
            number = number // 26

    for item in letter_list:
        letter += chr(item + 64)
    return letter




