import re
with open("Data.ad", encoding='utf-8') as file:
    f = file.readlines()

lines_inserted = 0
for index, line in enumerate(f):
    match = re.search(r'comments="(.*)"', line)
    string_to_add = ""
    if match:
        print(match.group(1), " at ", index)
        if "LDH" in match.group(1):
            string_to_add = ("\tassay=\"LDH\"\n")
        elif "MTT" in match.group(1):
            string_to_add = ("\tassay=\"MTT\"\n")

        if string_to_add != "":
            with open("Data.ad", encoding='utf-8') as file:
                buf = file.readlines()
                file.close()

            with open("Data.ad", "w") as out_file:
                buf.insert(index + lines_inserted, string_to_add)
                buf = "".join(buf)
                out_file.write(buf)
                out_file.close()
                lines_inserted += 1




