from collections.abc import Sequence
from io import BytesIO
import base64
import pandas as pd
import numpy as np
import io

# DataLoader
class ExcelDataLoader(Sequence):
    def __init__(self, excel_uploaded_file):
        self._data = pd.read_excel(BytesIO(excel_uploaded_file.read()), engine='openpyxl')
        self._fillna()
        self._lower_clean_headers()

    def __len__(self):
        return len(self._data)

    def __getitem__(self, idx):
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
        """limpiamos las columnas y pasamos a minúsculas automáticamente
        """
        self._data.columns = self._data.columns.str.strip().str.lower()

    def remove_rows(self, idx_list:list):
        """Elimina las filas proporcionadas de la lista

        Parameters
        ----------
        idx_list : list
            _description_
        """
        [self._data.drop(idx, inplace=True) for idx in idx_list]

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