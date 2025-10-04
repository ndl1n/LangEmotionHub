import csv
import os
import uuid


class LineChatProcessor:
    def __init__(self, output_name, master_name="", data_dir=""):
        self.master_name = master_name
        self.output_name = output_name
        self.data_dir = data_dir
        self.output_file_name = f"{str(uuid.uuid4())}.csv"
        self.instructions_list = []
        self.inputs_list = []
        self.outputs_list = []

    def is_master(self, name):
        # 判斷當前行是否來自 master_name
        return self.master_name in name

    def create_formatted_content(self, file_name):
        instruction = ""
        input = ""
        output = ""
        lines = file_name.readlines()

        if not lines:
            return
        pre_is_master = False

        for i in range(4, len(lines)):
            line = lines[i].decode("utf-8")
            if line == "\n":
                continue
            if line.endswith("已收回訊息"):
                continue
            w = line.split("\t")
            if len(w) < 3:
                continue
            if "收回訊息" in w[2]:
                continue
            if self.is_master(w[1]):
                output += w[2]
                pre_is_master = True
            else:
                if pre_is_master:
                    self.instructions_list.append(instruction)
                    self.inputs_list.append(input)
                    self.outputs_list.append(output)
                    instruction = ""
                    input = ""
                    output = ""
                input += w[2]
                pre_is_master = False

    def output_file(self, instructions_list, inputs_list, outputs_list):
        # 輸出文件，如果長度不一致則直接返回
        if (
            len(instructions_list) != len(inputs_list)
            or len(inputs_list) != len(outputs_list)
            or len(instructions_list) != len(outputs_list)
        ):
            return

        block_title = "你是好友，也是大學同學。請以好友的回應回答對話。"

        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)

        output_file_path = os.path.join(self.data_dir, self.output_file_name)

        with open(output_file_path, "w", encoding="utf-8", newline="") as writer_file:
            fieldnames = ["instruction", "input", "output", "text"]
            writer = csv.DictWriter(writer_file, fieldnames=fieldnames)
            writer.writeheader()

            for i in range(len(inputs_list)):
                writer.writerow(
                    {
                        "input": inputs_list[i],
                        "output": outputs_list[i],
                        "instruction": block_title,
                    }
                )

        return self.output_file_name

    def process(self, file):
        self.create_formatted_content(file)
        return self.output_file(
            self.instructions_list, self.inputs_list, self.outputs_list
        )
