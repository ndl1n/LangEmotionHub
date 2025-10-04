import os
from typing import List, Optional
import uuid
import pandas as pd


from service.utils_controller import FILE_DIRECTORY


def merge_csv_files(file_list: List[str]) -> Optional[str]:
    file_name = str(uuid.uuid4())
    output_file = os.path.join(FILE_DIRECTORY, file_name)
    # Read and concatenate all CSV files
    df_list = [pd.read_csv(file) for file in file_list if os.path.exists(file)]
    if len(df_list) == 0:
        return None
    merged_df = pd.concat(df_list, ignore_index=True)

    merged_df.to_csv(output_file, index=False)
    return file_name
