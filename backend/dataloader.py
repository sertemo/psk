from collections.abc import Sequence
from io import BytesIO
import pandas as pd
import numpy as np
import io

# DataLoader
class ExcelDataLoader(Sequence):
    def __init__(self, excel_uploaded_file, columns_to_lower:list[str]=["idioma"]) -> None: # Hardcoded columna idioma
        self._data = pd.read_excel(BytesIO(excel_uploaded_file.read()), engine='openpyxl')
        self._fillna()
        self._lower_clean_headers()
        self._strip_all_data()
        self._lower_columns(columns_to_lower)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, idx:int):
        return self._data.iloc[idx]

    @property
    def df(self) -> pd.DataFrame:
        return self._data
    
    @property
    def columns_set(self) -> set:
        return set(self.df.columns)

    def _fillna(self):
        self._data.fillna(value=np.nan, inplace=True)

    def _lower_clean_headers(self) -> None:
        """Quita espacios en blanco de los headers y pasa a minúsculas
        """
        self._data.columns = self._data.columns.str.strip().str.lower()

    def _strip_all_data(self) -> None:
        """Quita los espacios en blanco de todos los campos
        """
        for col in self._data.columns:
            self._data[col] = self._data[col].str.strip()

    def _lower_columns(self, columns:list[str]) -> None:
        """Pasas a minúsculas las columnas proporcionadas en la lista

        Parameters
        ----------
        columns : list[str]
            _description_
        """
        for col in columns:
            if col in self._data.columns:
                self._data[col] = self._data[col].str.lower()

    def remove_rows(self, idx_list:list) -> None:
        """Elimina las filas proporcionadas de la lista

        Parameters
        ----------
        idx_list : list
            _description_
        """
        [self._data.drop(idx, inplace=True) for idx in idx_list]

    def modify_row(self, idx:int, column:str, new_value:str) -> None:
        self._data.loc[idx, column] = new_value

    def to_excel(self) -> bytes:
        """Devuelve el excel en bytes para poder descargarlo

        Parameters
        ----------
        df : pd.DataFrame
            _description_

        Returns
        -------
        bytes
            _description_
        """
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            self._data.to_excel(writer, index=False)
        return output.getvalue()