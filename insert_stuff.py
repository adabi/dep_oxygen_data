import re
import pathlib
with open("Data.ad", encoding='utf-8') as file:
    f = file.readlines()

for index, line in enumerate(f):
    match = re.search(r'file="(.*)"', line)
    if match:
        print(match.group(1))
        old_path = match.group(1)
        new_path = pathlib.PureWindowsPath(old_path)
        new_path = str(pathlib.Path(new_path))
        new_line = line.replace(old_path, new_path)
        print(line, new_line)

        with open("Data.ad", encoding='utf-8') as file:
            buf = file.readlines()
            file.close()

        with open("Data.ad", "w") as out_file:
            buf[index] = new_line
            buf = "".join(buf)
            out_file.write(buf)
            out_file.close()



