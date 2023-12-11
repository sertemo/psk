import backend.db as db
import backend.template_manager as tm
import backend.dataloader as dl

import re
from typing import Union
import string
from passlib.context import CryptContext
import random
import validators
import numpy as np
from cryptography.fernet import Fernet

from icecream import ic
#ruta_frontend = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
#sys.path.append(ruta_frontend)
#import dataloader as dl 

EMAIL_REGEX = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
PASS_LEN = 8
PASS_NUMS = 2
PASS_SPECIAL = 1
PASS_CHAR = 4
HASH_SCHEMA = CryptContext(schemes=["bcrypt"], deprecated= "auto") 


def encriptar_fernet(api_key:str) -> tuple[bytes,bytes]:
    """Devuelve una tupla con la api key encriptada y el objeto llave para desencriptar

    Parameters
    ----------
    api_key : str
        _description_

    Returns
    -------
    tuple[bytes,Fernet]
        _description_
    """
    key = Fernet.generate_key()
    cipher_suite = Fernet(key)
    cipher_text = cipher_suite.encrypt(api_key.encode())
    return cipher_text, key


def desencriptar_fernet(key:bytes, cipher_text:bytes) -> str:
    """Devuelve el string correspondiente al objeto desencriptado

    Parameters
    ----------
    cipher_suite : Fernet
        _description_
    cipher_text : bytes
        _description_

    Returns
    -------
    str
        _description_
    """
    cipher_suite = Fernet(key)
    return cipher_suite.decrypt(cipher_text).decode()


def verificar_existen_todas_variables_plantilla(template_manager:tm.HTMLTemplateManager, variables_que_existen:set)-> set:
    ## Excluimos $nombre_receptor de la plantilla ya que es un valor que usamos luego en la pestaña distribuir
    variables_plantilla_modif = set(var for var in template_manager.variables_plantilla if var!='\$nombre_receptor')
    #print(f"{variables_plantilla_modif=}")
    diferencia = variables_plantilla_modif.difference(variables_que_existen) ## Aquí se verían las variables que están en la plantilla y NO en las variables existentes
    ## Si diferencia NO está vacío da error
    #print(f"{diferencia=}")
    return diferencia


def validar_columnas_excel(columnas_correctas:set, excel_dl:dl.ExcelDataLoader) -> set:
    """Verifica que las columnas del excel pasado correspondan con unos nombres de columna establecidos

    Parameters
    ----------
    columnas_correctas : set
        _description_
    excel_dl : dl.ExcelDataLoader
        _description_

    Returns
    -------
    set
        _description_
    """
    columnas_xls = excel_dl.columns_set
    # nombres que están en excel y no son correctos.
    diferencia = columnas_xls.difference(columnas_correctas)
    return diferencia


def validar_sectores_excel(sectores_guardados:list, excel_dl:dl.ExcelDataLoader) -> set:
    """Devuelve un set con los sectores del excel que no corresponden con los sectores guardados.

    Parameters
    ----------
    sectores_guardados : list
        _description_
    excel_dl : dl.ExcelDataLoader
        _description_

    Returns
    -------
    set
        _description_
    """
    sectores_excel = set(sector for sector in excel_dl.df["sector"] if sector) ## Quitamos los nan para que no den problemas
    #print(sectores_excel)
    diferencia = sectores_excel.difference(sectores_guardados)
    return diferencia


def validar_idiomas_excel(idiomas_admisibles:set, excel_dl:dl.ExcelDataLoader) -> set:
    """Devuelve un set con los idiomas que no son admisibles.

    Parameters
    ----------
    idiomas_admisibles : set
        _description_
    excel_dl : dl.ExcelDataLoader
        _description_

    Returns
    -------
    set
        _description_
    """
    idiomas_excel = set(idioma for idioma in excel_dl.df["idioma"] if idioma) # Quitamos los nan para que no den problemas
    #print(idiomas_excel)
    diferencia = idiomas_excel.difference(idiomas_admisibles)
    return diferencia


def validar_emails_excel(excel_dl:dl.ExcelDataLoader) -> set[str]:
    """Verifica que los mails proporcionados sean correctos, devuelve un set con los mails erróneos

    Parameters
    ----------
    excel_dl : dl.ExcelDataLoader
        _description_

    Returns
    -------
    set[str]
        _description_
    """
    emails_set = set(excel_dl.df["email"])
    emails_fail = set()
    for mail in emails_set:
        if (type(mail) == str) and (mail):
            if not email_valido(mail):
                emails_fail.add(mail)
    #print(f"{emails_set=}")
    #print(f"{emails_fail=}")
    return emails_fail


def validar_gmail_key_fake(api_key:str) -> bool:
    """Verifica simplemente que la api key tenga 16 caracteres y sean todos letras

    Parameters
    ----------
    api_key : str
        _description_

    Returns
    -------
    bool
        _description_
    """
    api_key = "".join(api_key.split()) # Quitamos espacios en blanco si los hubiera
    if (caracteres:=sum(c in string.ascii_lowercase for c in api_key)) != 16:
        return False
    return True


def existe_usuario(usuario:str, gestor_db:db.UserDBHandler)-> bool:
    """Devuelve True si el usuario existe en db o False en caso contrario

    Parameters
    ----------
    usuario : str
        _description_
    gestor_db : db.DBHandler
        _description_

    Returns
    -------
    bool
        _description_
    """
    if gestor_db.find_one(campo_buscado="usuario", valor_buscado=usuario):
        return True
    return False


def crear_contraseña_valida():
    pass_char = random.randint(PASS_CHAR, PASS_CHAR + 2)
    pass_nums = random.randint(PASS_NUMS, PASS_NUMS + 3)
    pass_special = random.randint(PASS_SPECIAL, PASS_SPECIAL + 4)

    # Caracteres válidos para la contraseña
    letras = string.ascii_letters
    numeros = string.digits
    caracteres_especiales = "!@#$%^&*(),.?\":{}|<>"

    # Generar partes de la contraseña
    parte_letras = "".join(random.choice(letras) for _ in range(pass_char))
    parte_numeros = "".join(random.choice(numeros) for _ in range(pass_nums))
    parte_especiales = "".join(random.choice(caracteres_especiales) for _ in range(pass_special))

    # Combinar y mezclar
    contrasena_temporal = parte_letras + parte_numeros + parte_especiales
    contrasena = "".join(random.sample(contrasena_temporal, len(contrasena_temporal)))

    return contrasena


def validar_usuario(usuario:str, gestor_db:db.UserDBHandler)-> Union[str, None]:
    """Valida que el usuario cumpla los criterios establecidos:
    1 - que no tenga espacios en blanco
    2 - que no exista el mismo usuario en db

    Parameters
    ----------
    usuario : str
        _description_
    database : db.DBHandler
        _description_

    Returns
    -------
    str
        Si retorna algo es que existe usuario en db, lo retornado es el error
    """
    ## Comprobamos espacios en blanco
    if len(usuario.split()) > 1:
        return "El usuario no puede tener espacios en blanco."
    ## Comprobamos si existe en db ya ese usuario
    if  existe_usuario(usuario, gestor_db):
        return "El nombre de usuario ya existe."
    
    return None


def is_valid_image_url(url:str)-> bool:
    """Valida si una url pertenece a una imagen

    Parameters
    ----------
    url : _type_
        _description_

    Returns
    -------
    bool
        _description_
    """
    valid = validators.url(url)
    if valid == True:
        # Las extensiones de imagen más comunes son: .jpg, .jpeg, .png, .gif, .bmp, .tiff, .webp
        # extensiones
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp']
        if any(url.endswith(f'.{ext}') for ext in image_extensions):
            return True
    return False


def validar_img_url_en_dict_sector(dict_sector:dict)-> str:
    """Recibe el dict de sesion y devuelve el mensaje de error en caso de que una url no sea buena

    Parameters
    ----------
    dict_sector : dict
        _description_

    Returns
    -------
    str
        _description_
    """
    keys_to_check = ['enlace_img1', 'enlace_img2']  # Puedes extender esta lista según tus necesidades
    url_fails = []
    for key in keys_to_check:
        if key in dict_sector:
            if not is_valid_image_url(dict_sector[key]):
                url_fails.append(key)
    if url_fails:
        return "La URL en {} no es válida o no es una imagen.".format(", ".join(url_fails))
    return ""


def email_valido(email:str)-> bool:
    """Verifica que el formato del email sea válido

    Parameters
    ----------
    email : str
        _description_

    Returns
    -------
    bool
        _description_
    """
    ## Comprobamos instancia de str
    if not isinstance(email,str):
        return False
    ## Comprobamos formato
    if not re.fullmatch(EMAIL_REGEX, email):
        return False
    
    return True


def validar_email_db(email:str, gestor_db:Union[db.UserDBHandler, db.SQLContext], verificar_mail:bool=True)-> Union[str, None]:
    """Valida que el mail cumpla los criterios establecidos:
    1 - sea un mail válido: con regex (opcional si verificar_mail = True)
    2 - que no exista el mismo email en db

    Válido para gestor_db de Mongo o de SQL.
    Para Mongo retorna el dict correspondiente a ese mail, para SQL retorna tupla con todas las columnas

    Parameters
    ----------
    email : str
        _description_
    database : db.DBHandler | db.SQLContext
        _description_

    Returns
    -------
    dict | tuple
        Retorna str con mensaje si no es válido.
    """
    if verificar_mail:
        if not email_valido(email):
            return "El email introducido no es un email válido."

    if gestor_db.find_one("email", email):
        return "Ya existe ese email con otro usuario."
    
    return None


def validar_contraseña(password:str)-> Union[str, None]:
    """Valida que la contraseña cumpla las características que se le han pedido desde la UI

    Returns
    -------
    _type_
        _description_
    """
    ## Tamaño de la cadena de la pass
    if len(password) < PASS_LEN:
        return f"La contraseña debe tener al menos {PASS_LEN} caracteres. Tiene {len(password)}."
    
    ## Número de dígitos
    numeros =  sum(c.isdigit() for c in password)
    if numeros < PASS_NUMS:
        return f"La contraseña debe tener al menos {PASS_NUMS} dígitos. Tiene {numeros}."
    
    ## Número de letras
    letras = sum(c in string.ascii_letters for c in password)
    if letras < PASS_CHAR:
        return f"La contraseña debe tener al menos {PASS_CHAR} letras. Tiene {letras}."
    
    ## Caracteres especiales
    caracteres_especiales = sum(c in "!@#$%^&*(),.?\":{}|<>" for c in password)
    if caracteres_especiales < PASS_SPECIAL:
        return f"La contraseña debe tener al menos {PASS_SPECIAL} caracteres especiales '!@#$%^&*(),.?\":|<>'. Tiene {caracteres_especiales}."

    return None


def hashear_contraseña(password:str)-> str:
    return HASH_SCHEMA.hash(password)


def verificar_contraseña(password:str, password_real:str)-> bool:
    """Comprueba que una contraseña y su hasheada sean la misma

    Returns
    -------
    _type_
        _description_
    """
    return HASH_SCHEMA.verify(password, password_real)


def existe_sector(nombre_sector:str, gestor_db_sector:db.SectorDBHandler)-> bool:
    """Devuelve True si el sector existe en db (el nombre en español) False en caso contrario

    Parameters
    ----------
    nombre_sector : str
        _description_
    gestor_db_sector : db.SectorDBHandler
        _description_

    Returns
    -------
    bool
        _description_
    """

    if gestor_db_sector.find_one("nombre_sector", nombre_sector):
        return True
    return False