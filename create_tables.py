import json
import os
import pandas as pd

script_path = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_path, "Data")
file_list = ["equipo_categoria.json", "factor_categoria.json", "factor_coincidencia.json", "factor_horario.json", "partidos.json"]
result_files = ["equipo_categoria.csv", "factor_categoria.csv", "factor_coincidencia.csv", "factor_horario.csv", "partidos.csv"]

class DataManager():
    df_team_cat : pd.DataFrame
    df_cat_fact : pd.DataFrame
    df_coincidence_fact : pd.DataFrame
    df_schedule : pd.DataFrame
    df_matches : pd.DataFrame

    def __init__(self):
        self.create_dataframes()
        self.open_dataframes()

    def _open_json(self, path) -> dict:
        with open(path) as f:
            result_dict = json.load(f)
        return result_dict

    def create_dataframes(self):
        for file_str , result_file in zip(file_list, result_files):
            data_dict = self._open_json(os.path.join(data_path, "jsons", file_str))
            try:
                df = pd.DataFrame(data_dict)
                df.to_csv(os.path.join(data_path,"csvs", result_file))
            except Exception as e:
                print(e)
                raise Exception("Los datos de entrada no son correctos para crear un dataframe")
    def open_dataframes(self):
        self.df_team_cat = pd.read_csv(os.path.join(data_path, "csvs", result_files[0]), index_col = 0)
        self.df_cat_fact = pd.read_csv(os.path.join(data_path, "csvs", result_files[1]), index_col = 0)
        self.df_coincidence_fact = pd.read_csv(os.path.join(data_path, "csvs", result_files[2]), index_col = 0)
        self.df_schedule = pd.read_csv(os.path.join(data_path, "csvs", result_files[3]), index_col = 0)
        self.df_matches = pd.read_csv(os.path.join(data_path, "csvs", result_files[4]), index_col = 0)
        


if __name__ == "__main__":
    dataManager = DataManager()