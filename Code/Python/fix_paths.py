new_data = []
with open("Data.ad", 'r') as file:
    data = file.readlines()
    for line in data:
        if len(line) > 5:
            if line[2:6] == "file":
                new_data.append(line.replace("\\", "/"))
            else:
                new_data.append(line)
        else:
            new_data.append(line)


with open("Data_fixed.ad", "w") as out_file:
    buf = "".join(new_data)
    out_file.write(buf)
    out_file.close()
