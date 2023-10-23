from collections.abc import Sequence
from dotenv import load_dotenv

import os
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import pytz
from typing import Union, Any, Literal

import sqlite3
from sqlite3 import Cursor
from pymongo import MongoClient

from icecream import ic

from cryptography.fernet import Fernet

load_dotenv()

## SQLITE ##

NOMBRE_DB_SQLITE = "db/stats.db"

class SQLManager:
    def __init__(self, db_filename):
        self.db_filename = db_filename

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_filename)
        return self.conn.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

class SQLContext:
    def __init__(self, *, nombre_tabla:str, db_filename=NOMBRE_DB_SQLITE) -> None:
        self.db_filename = db_filename
        self.tabla = nombre_tabla

    def get_table(self) -> list[tuple]:
        """Devuelve una lista de tuplas conteniendo cada tupla los campos de cada columna \
            para cada registro de la tabla dada"""
        with SQLManager(self.db_filename) as c:
            results = c.execute(f"""SELECT * from {self.tabla}""")
            return results.fetchall()
        
    def show_table_columns(self) -> list[str]:
        with SQLManager(self.db_filename) as c:
            c.execute(f"PRAGMA table_info({self.tabla})")
            info = c.fetchall()
            column_names = [column[1] for column in info]
            return column_names
        
    def add_column(self, *, nombre_columna: str, tipo_dato: str) -> None:
        with SQLManager(self.db_filename) as c:
            c.execute(f"ALTER TABLE {self.tabla} ADD COLUMN {nombre_columna} {tipo_dato}")
    
    def insert_one(self, columnas:dict) -> None:
        """inserta un registro en la tabla dada."""
        with SQLManager(self.db_filename) as c:
            query = f"""INSERT INTO {self.tabla} ({", ".join(columnas.keys())}) VALUES ({", ".join('?' * len(columnas))})"""
            c.execute(query, tuple(columnas.values()))

    def find_one(self, *, campo_buscado:str, valor_buscado:str):
        """Devuelve todos los campos de la fila cuyo campo coincide con el valor buscado

        Parameters
        ----------
        campo_buscado : str
            _description_
        valor_buscado : str
            _description_

        Returns
        -------
        _type_
            _description_
        """
        with SQLManager(self.db_filename) as c:
            consulta = f"SELECT * FROM {self.tabla} WHERE {campo_buscado} = ?"
            results = c.execute(consulta, (valor_buscado,))
            return results.fetchone()
        
    def find_one_field(self, *, campo_buscado:str, valor_buscado:str, campo_a_retornar:str):
        """Devuelve todos el campo especificado de la fila cuyo campo coincide con el valor buscado

        Parameters
        ----------
        campo_buscado : str
            _description_
        valor_buscado : str
            _description_

        Returns
        -------
        _type_
            _description_
        """
        with SQLManager(self.db_filename) as c:
            consulta = f"SELECT {campo_a_retornar} FROM {self.tabla} WHERE {campo_buscado} = ?"
            results = c.execute(consulta, (valor_buscado,))            
            if (output:=results.fetchone()) is not None:
                return output[0]
            else:
                return output
    
    @classmethod
    def create_table(cls, *, db_filename:str, nombre_tabla:str, columnas:tuple[str]) -> None:
        with SQLManager(db_filename) as c:
            c.execute(f"""
                    CREATE TABLE {nombre_tabla} ({", ".join(columnas)})""") ## He quitado el IF NOT EXISTS
        return cls
    
    def delete_table(self) -> None:
        with SQLManager(self.db_filename) as c:
            c.execute(f"DELETE from {self.tabla}")
            c.execute(f"DELETE FROM sqlite_sequence WHERE name = '{self.tabla}'") # Para reiniciar el autoincremental

    def delete_one(self, *, campo_buscado:str, valor_buscado:str) -> None:
        with SQLManager(self.db_filename) as c:
            consulta = f"DELETE FROM {self.tabla} WHERE {campo_buscado} = ?"
            c.execute(consulta, (valor_buscado,))

    def update_one(self, *, columna_a_actualizar:str, nuevo_valor: str, campo_buscado:str, valor_buscado:str) -> None:
        with SQLManager(self.db_filename) as c:
            consulta = f"""UPDATE {self.tabla} SET {columna_a_actualizar} = ? WHERE {campo_buscado} = ?"""
            c.execute(consulta, (nuevo_valor, valor_buscado))



## MONGODB ##

DEFAULT_DB = 'PSK'
BLOCKING_TIME = 30 # minutos


def format_datetime()-> str:
    return datetime.strftime(datetime.now(tz=pytz.timezone('Europe/Madrid')),format="%d-%m-%Y %H:%M:%S")


class Usuario(BaseModel):
    nombre_completo:str
    usuario:str
    contraseña:str
    telefono:str
    puesto:str
    email:str
    fecha_alta:datetime = Field(default_factory=format_datetime)
    activo:bool=False
    bloqueado:bool=False # Si intenta autenticarse erróneamente más de x veces
    fecha_bloqueo:Union[datetime, None]=None


class UsuarioSesion(BaseModel):
    nombre_completo:str
    usuario:str
    telefono:str
    puesto:str
    email:str
    

class Sector(BaseModel):
    nombre_sector:str
    nombre_sector_fr:str
    nombre_sector_en:str
    enlace_img1:str
    enlace_img2:str
    clientes_satisfechos:str
    listado_clientes:list


class Plantilla(BaseModel):
    html:str
    tipo:str=Literal["prospeccion", "reactivacion"]
    idioma:str=Literal["es", "fr", "en"]


class ApiKey(BaseModel):
    usuario:str
    objeto_key:Union[bytes, str]



class DBHandler(Sequence):
    def __init__(self, collection:str, database:str=DEFAULT_DB):
        self.client = MongoClient(os.environ["DB_MONGO"])
        self.db = self.client[database]
        self.collection = collection
    
    def __len__(self):
        """Devuelve el número de documentos de la collección
        """
        return len(list(self.db[self.collection].find()))
    
    def __getitem__(self, idx:int):
        """el indice idx de la collection de la instancia

        Parameters
        ----------
        collections : str
            _description_
        """
        documents = list(self.db[self.collection].find())

        #Borramos el id
        for doc in documents:
            del doc["_id"]
        return documents[idx]
    
    def insert(self, document:Union[Usuario, Sector]):
        self.db[self.collection].insert_one(document.dict(by_alias=True))

    def find_one(self, campo_buscado:str, valor_buscado:Any)-> dict:
        """Devuelve un dict con todos los campos del valor buscado

        Parameters
        ----------
        campo_buscado : str
            _description_
        valor : Any
            _description_

        Returns
        -------
        dict
            _description_
        """
        return self.db[self.collection].find_one({campo_buscado: valor_buscado})

    def find_one_field(self, campo_buscado:str, valor:Any, campo_a_retornar:str)-> Any:
        """Devuelve el valor del campo que coincide con el documento buscado

        Parameters
        ----------
        campo_buscado : str
            _description_
        valor : Any
            _description_

        Returns
        -------
        dict
            _description_
        """
        search_dict = self.db[self.collection].find_one({campo_buscado: valor})

        if search_dict is None:
            return None
        return search_dict[campo_a_retornar] 

    def update(self, busqueda:str, valor_buscado:str, diccionario_modificaciones:dict):
        assert isinstance(diccionario_modificaciones, dict), f"{diccionario_modificaciones} tiene que ser un diccionario."
        filtro = {busqueda: valor_buscado}
        valores_nuevos = {"$set": diccionario_modificaciones}
        self.db[self.collection].update_one(filtro, valores_nuevos)
    
    def delete_one(self, busqueda:str, valor_buscado:Any):
        filtro = {busqueda: valor_buscado}
        self.db[self.collection].delete_one(filtro)

    def increment_one(self):
        pass


class UserDBHandler(DBHandler):
    def get_user_activo(self, usuario:str)-> bool:
        user_dict = self.db[self.collection].find_one({"usuario": usuario})
        return user_dict["activo"]
    
    def get_user_name(self, usuario:str)-> str:
        user_dict = self.db[self.collection].find_one({"usuario": usuario})
        return user_dict["nombre_completo"]    

    
    def get_user_email(self, usuario:str)-> str:
        user_dict = self.db[self.collection].find_one({"usuario": usuario})
        return user_dict["email"]
    

    def get_user_hashpass(self, usuario:str, collection:str="usuarios")-> str:
        user_dict = self.db[collection].find_one({"usuario": usuario})
        return user_dict["contraseña"]
    

    def get_user_bloqueado(self, usuario:str)-> bool:
        user_dict = self.db[self.collection].find_one({"usuario": usuario})
        return user_dict["bloqueado"]
    

    def get_fecha_bloqueo(self, usuario:str)-> datetime:
        user_dict = self.db[self.collection].find_one({"usuario": usuario})
        return user_dict["fecha_bloqueo"] 


    def get_remaining_time_or_none(self, usuario:str)-> Union[timedelta, None]:
        """Devuelve None si el usuario no está bloqueado, devuelve el tiempo en minutos que le queda al usuario para desbloquear su cuenta

        Parameters
        ----------
        usuario : str
            _description_

        Returns
        -------
        str
            _description_
        """
        ahora = datetime.now()
        fecha_bloqueo = self.get_fecha_bloqueo(usuario)
        fin = fecha_bloqueo + timedelta(minutes=BLOCKING_TIME)

        if ahora < fin:
            return fin - ahora

        return None

    
    def bloquear_cuenta(self, usuario:str)-> None:
        self.update("usuario", usuario,{
            "bloqueado": True,
            "fecha_bloque": datetime.now()
        })


    def desbloquear_cuenta(self, usuario:str)-> None:
        self.update("usuario", usuario,{
            "bloqueado": False,
            "fecha_bloque": None,
        })
    

class SectorDBHandler(DBHandler):
    pass


class TemplateDBHandler(DBHandler):
    pass
