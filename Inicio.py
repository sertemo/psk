import streamlit as st
from streamlit_option_menu import option_menu
from streamlit.runtime.uploaded_file_manager import UploadedFile

from typing import Union, Literal
from googletrans import Translator

import numpy as np

from icecream import ic
import logging

from pathlib import Path

import time
from datetime import datetime
import pytz

import pandas as pd

from functools import partial
import os

from backend import (dataloader as dl,
                    template_manager as tm,
                    db,
                    validaciones as val,
                    email_manager as em,
                    workers as w,)

#ruta_backend = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
#sys.path.append(ruta_backend)

## Constantes
version_app = '1.0'
NUM_INTENTOS = 4
NOMBRE_ADMIN = 'Sergio Tejedor'
USUARIO_ADMIN = 'sertemo'
ADMIN_MAIL = 'sergio.tejedor@ets-barre.com'
ADMIN_API_KEY = os.environ["ADMIN_GOOGLE_API_KEY"]
IDIOMAP = {
    'fr': 'francés',
    'en': 'inglés',
    'es': 'español',
}
PLANTILLA_MAP = {
    'plantillas_prosp': 'prospeccion',
    'plantillas_react': 'reactivacion',
}
COLUMNAS_EXCEL:set = {
    'email',
    'receptor',
    'idioma',
    'sector',
    'web',
    'empresa',
}
LOG_FOLDER = Path('logs')

## Parámetros válidos para todas las plantillas.
configuracion_plantilla = {
    'enlace_logo': 'https://i.imgur.com/Fv0NpWX.jpg',
    'enlace_banner': 'https://i.imgur.com/TnStO8u.jpg',
    'azul_talsa': "#005092",
    'rojo_talsa': "#c54933",
}

## Configuración de la app
st.set_page_config(
    page_title=f"pSK mailing {version_app} ~BETA~",
    page_icon="📮",
    layout="wide",
    initial_sidebar_state="auto",
)
## Logo de la empresa
st.sidebar.image(image='img/talsa.png',caption="")


## Funciones auxiliares
def create_log_file()-> str:
    fecha_string = datetime.strftime(datetime.now(tz=pytz.timezone('Europe/Madrid')),format="%Y-%m-%d")
    return LOG_FOLDER / (fecha_string + ".log")


def get_decrypted_api_key(
        nombre_usuario:str, 
        gestor_mongo_apikey:db.DBHandler, 
        gestor_sqlite_apikey:db.SQLContext) -> str:
    ## Hacemos búsqueda
    if (objeto_key:=gestor_mongo_apikey.find_one_field('usuario', nombre_usuario, 'objeto_key')) and \
    (apikey:=gestor_sqlite_apikey.find_one_field(campo_buscado='usuario', valor_buscado=nombre_usuario, campo_a_retornar='apikey')):
        return val.desencriptar_fernet(key=objeto_key, cipher_text=apikey)
    
    return ""


def get_variables_para_plantilla() -> set:
    """Devuelve un set de las variables que se puede usar en la plantilla.
    Esto es keys de los diccionarios:  configuracion_plantilla, st.session_state["parametros_comercial_sesion], sectores

    Returns
    -------
    list
        _description_
    """
    dict_todas = dict(**st.session_state.get("sectores",[{},])[0], **st.session_state.get("parametros_comercial_sesion",{}), **configuracion_plantilla)
    ## Borramos usuario
    del dict_todas["usuario"]
    return set('\$' + key for key in dict_todas.keys())


def get_nombre_comercial_sesion() -> str:
    """Devuelve el nombre completo del comercial de la sesión

    Returns
    -------
    str
        _description_
    """
    return st.session_state.get("parametros_comercial_sesion",{}).get("nombre_completo","")


def get_email_comercial_sesion() -> str:
    """Devuelve el email del comercial de la sesión

    Returns
    -------
    str
        _description_
    """
    return st.session_state.get("parametros_comercial_sesion",{}).get("email","")


def cargar_datos_user_en_sesion(usuario:str, gestor_db:Union[db.UserDBHandler, db.SectorDBHandler]) -> None:
    """Carga los datos del usuario autenticado en sesión st.session_state

    Parameters
    ----------
    usuario : str
        _description_
    """
    user_sesion_dict = gestor_db.find_one("usuario", usuario)
    st.session_state["parametros_comercial_sesion"] = db.UsuarioSesion(**user_sesion_dict).dict()


def cargar_sectores_en_sesion(gestor_db_sectores:db.SectorDBHandler) -> None:
    """Mete los sectores guardados en db en variables de sesión "sectores"

    Parameters
    ----------
    gestor_db_sectores : db.SectorDBHandler
        _description_
    """
    st.session_state["sectores"] = list(gestor_db_sectores)


def cargar_plantillas_en_sesion(gestor_db_plantillas:db.TemplateDBHandler) -> None:
    tipo_plantilla = gestor_db_plantillas.collection
    st.session_state[tipo_plantilla] = list(gestor_db_plantillas) # Debería haber 3 plantillas: es, fr, en


def sacar_plantilla_html_de_sesion(tipo_plantilla:Literal["plantillas_prosp", "plantillas_react"], idioma:Literal["fr", "en", "es"])-> str:
    """Dados un idioma y el tipo de la plantilla devuelve el HTML de la plantilla cargada en sesion

    Parameters
    ----------
    tipo_plantilla : str
        _description_
    idioma : str
        _description_

    Returns
    -------
    str
        _description_
    """
    plantillas:list[dict] = st.session_state.get(tipo_plantilla, [])
    plantilla_buscada = [plantilla["html"] for plantilla in plantillas if idioma in plantilla.values()]
    return plantilla_buscada[0] if plantilla_buscada else ""


def get_nombre_sectores()-> list:
    """Itera sobre los sectores de sesión para sacar los campos 'nombre_sector' de cada sector
    y devolver una lista con los nombres de los sectores.

    Returns
    -------
    list
        _description_
    """
    return sorted([sector["nombre_sector"] for sector in st.session_state.get("sectores",[])])


def borrar_plantilla_de_sesion(tipo_plantilla:Literal["plantillas_prosp", "plantillas_react"], idioma:Literal["fr", "en", "es"])-> None:
    """Itera sobre las plantillas del tipo indicado cargadas en sesion y borra la correspondiente

    Parameters
    ----------
    tipo_plantilla : Literal[&quot;plantillas_prosp&quot;, &quot;plantillas_react&quot;]
        _description_
    idioma : str
        _description_
    """
    plantillas_sesion = st.session_state.get(tipo_plantilla, [])
    [plantillas_sesion.pop(idx) for idx, plantilla in enumerate(plantillas_sesion) if plantilla["idioma"] == idioma]


def get_sector_from_session_by_name(nombre_sector:str)-> Union[dict, None]:
    """Dado el nombre de un sector, devuelve el dict correspondiente a ese sector

    Parameters
    ----------
    nombre_sector : str
        _description_

    Returns
    -------
    dict
        _description_
    """
    resultado = [sector_dict for sector_dict in st.session_state.get("sectores",[]) if sector_dict["nombre_sector"] == nombre_sector]
    return resultado[0] if resultado else None


def comprobar_campos_modificados(sesion_original:dict, sesion_modificada:dict) -> dict:
    """Devuelve un dict con las keys que han sido modificadas y los valores nuevos

    Parameters
    ----------
    sesion_original : dict
        _description_
    sesion_modificada : dict
        _description_

    Returns
    -------
    dict
        _description_
    """
    cambios = {}
    
    for clave, valor in sesion_original.items():
        if clave in sesion_modificada:
            if valor != sesion_modificada[clave]:
                cambios[clave] = sesion_modificada[clave]
                
    return cambios


def mostrar_msg_bienvenida(usuario:str, nombre_usuario:str):
    """Función para escribir el mensaje al usuario autenticado

    Parameters
    ----------
    usuario_sesion : _type_
        _description_
    """ 
    #texto(f"{usuario} en sesión", font_size=10)
    añadir_salto()
    template_welcome = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* Estilos generales */
        body {
            font-family: 'Arial', sans-serif;
            padding: 20px;
            background-color: #f4f4f4;
        }

        .container {
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }

        h1 {
            color: #2C3E50;
            border-bottom: 2px solid #3498DB;
            padding-bottom: 10px;
        }

        ul.recomendaciones {
            list-style-type: none;
            padding-left: 0;
        }

        ul.recomendaciones li {
            margin-bottom: 15px;
            font-size: 16px;
        }

        ul.recomendaciones li::before {
            content: "🔹";
            margin-right: 10px;
        }

    </style>
</head>
<body>
    <div class="container">
        <h1>Bienvenido a pSK mailing 1.0</h1>
        <p>Gracias por autenticarte en nuestra aplicación, <b>$usuario</b>.<br>A continuación, encontrarás algunas recomendaciones de uso y el funcionamiento general de la app.</p>        
        <h2>Recomendaciones de uso:</h2>
        <ul class="recomendaciones">
            <li>Es aconsejable, como primera etapa, tener una base de datos de <strong>sectores</strong> considerable.</li>
            <li>Para alojar las imágenes de los perfiles puedes usar <strong><a href='http://imgur.com'>imgur</a></strong> o similares. Deben estar alojadas en internet.</li>
            <li>Obtén la <strong>API key</strong> de tu cuenta de correo y guárdala bien. Para ello, en el apartado <b>Distribuir</b> y una vez subido un archivo excel, sigue los pasos indicados en la ayuda correspondiente.</li>
            <li>Ve a los <b>Personalizar</b> para cambiar parámetros de tu cuenta, agregar y modificar sectores y cambiar plantillas.</li>
            <li>Ve a <b>Distribuir</b> para realizar el mailing automático.</li>
            <li>Sigue las indicaciones que se van proporcionando en los desplegables y si tienes cualquier comentario escribe al administrador: <b>sergio.tejedor@ets-barre.com</b>.</li>
            <li>La idea a futuro es automatizar la realización del excel.</li>
        </ul>
    </div>
</body>
</html>"""

    plantilla = tm.CustomTemplate(template_welcome)
    st.markdown(plantilla.substitute({'usuario': usuario.split()[0]}), unsafe_allow_html=True)

    ## Mostrar aqui lógico para descargar archivos logging solo para el usuario admin. Escoger por día
    if (usuario == NOMBRE_ADMIN) and (nombre_usuario == USUARIO_ADMIN):
        añadir_salto()
        texto("ADMINISTRADOR")
        texto("Descargar archivo log", font_size=15, color=configuracion_plantilla["rojo_talsa"])
        archivo_log = st.text_input(" Escribe una fecha en formato **aaaa-mm-dd**", placeholder='ejemplo: 2023-10-20')
        if archivo_log:
            log_filename_to_download = archivo_log + '.log'
            ## Validación del nombre de archivo
            if not (LOG_FOLDER / log_filename_to_download).exists():
                st.error(f"No existe un archivo log con el nombre {log_filename_to_download}")
                logging.info(f"Búsqueda de archivo log '{log_filename_to_download}' errónea por parte de {usuario}.")
                st.stop()
            try:
                with open(LOG_FOLDER / log_filename_to_download, "rb") as file:                
                    boton = st.download_button(
                        label = "Descargar log",
                        data = file,
                        file_name = log_filename_to_download,
                        mime = "log/log",
                    )
                    logging.info(f"Descargado LOG:'{archivo_log}' por parte del admin {nombre_usuario}:{usuario}")
            except Exception as exc:
                st.error(f"Se ha producido el siguiente error al descargar: {exc}")
                logging.error(f"Error en archivo log '{archivo_log}' por parte del admin {nombre_usuario}:{usuario}.")


def mostrar_msg_autenticacion():
    st.info("Autentícate o Regístrate para poder continuar")


def texto(texto:str, /, *, font_size:int=20, color:str='#005092', font_family:str="Arial", formato:str=""):
    """ Función para personalizar el texto con HTML"""
    if formato:
        texto = f"<{formato}>{texto}</{formato}>"
    texto_formateado = f"""<div style='font-size: {font_size}px; color: {color}; font-family: {font_family}'>{texto}</div>"""
    st.markdown(texto_formateado, unsafe_allow_html=True)


texto_descriptivo = partial(texto, color=configuracion_plantilla["azul_talsa"], font_size=15)

texto_error = partial(texto, color=configuracion_plantilla["rojo_talsa"], font_size=15)

texto_correcto = partial(texto, color='#008d00', font_size=15 )


def añadir_salto(num_saltos:int=1) -> None:
    """Añade <br> en forma de HTML para agregar espacio
    """
    saltos = f"{num_saltos*'<br>'}"
    st.markdown(saltos, unsafe_allow_html=True)


def print_final_de_bucle(start:time, filas_excel:int, idx_to_delete:list[int]) -> None:
    texto_descriptivo("\nEnvíos terminados")
    minutos = (time.perf_counter() - start) // 60
    segundos = (time.perf_counter() - start) % 60
    texto_descriptivo(f"<b>Duración total: {minutos:.0f} min {segundos:.0f} s</b>")
    texto_descriptivo(f"Se han procesado <b>{len(idx_to_delete)}</b> filas de <b>{filas_excel}</b>.")
    logging.info(f"Final de Distribución para sesión. Se han procesado {len(idx_to_delete)} filas de {filas_excel}. Tiempo total: {minutos:.0f} min {segundos:.0f} s")


def autenticarse(gestor_db:db.UserDBHandler, gestor_mail:em.EmailManager) -> None:
    texto("~ Autenticarse ~", color='#c54933', formato='b', font_size=40)
    texto("Autentícate para iniciar sesión", formato='i')
    
    with st.form("identificarse",clear_on_submit=False):
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Enviar")

        with st.expander("¿ Has olvidado tu contraseña ?"):
            st.info("Se enviará un email con una nueva contraseña al email del usuario")
            recuperar = st.form_submit_button("Reestablecer contraseña")
            if recuperar:
                ## El usuario no puede estar vacío
                if not user:
                    st.error("El usuario no puede estar vacío.")
                    st.stop()
                ## Verificamos que el user exista
                if not val.existe_usuario(user, gestor_db):
                    st.error("Introduce un usuario válido.")
                    logging.info(f"Intento de recuperación de contraseña con usuario no válido {user}.")
                    st.stop()
                
                with st.spinner("Restableciendo contraseña..."):
                    logging.info(f"Restableciendo contraseña para {user}.")
                    ## Generar una contraseña nueva que cumpla el criterio establecido
                    nueva_pass = val.crear_contraseña_valida()
                    ## Reemplazar en db la contraseña hasheada
                    gestor_db.update("usuario", user, {"contraseña": val.hashear_contraseña(nueva_pass)})
                    ## Enviar mail al usuario con la nueva contraseña sin hashear
                    email_user = gestor_db.get_user_email(user)
                    try:
                        gestor_mail.enviar(
                            email_user,
                            asunto=f"""[pSK mailing] Restablecimiento de contraseña para {gestor_db.get_user_name(user)}""",
                            contenido=f"""Has solicitado un cambio de contraseña.\nTu nueva contraseña para el usuario <b>{user}</b> es: {nueva_pass}.\n
                            Podrás cambiarla cuando quieras en el apartado Personalizar.""",
                        )
                        st.success(f"Restablecimiento **correcto**: Se ha enviado un email al usuario {user} con la nueva contraseña.")
                        logging.info(f"Restablecimiento **correcto**: Se ha enviado un email al usuario {user} con la nueva contraseña.")
                    except Exception as exc:
                        st.error(f"Se ha producido el siguiente error al enviar: {exc}")
                        logging.error(f"Se ha producido el siguiente error al enviar: {exc}")
                

        if submit:
            if user and password:                
                ## Verificamos que usuario exista
                if not val.existe_usuario(user, gestor_db):
                    st.error("El usuario no existe.")
                    logging.info(f"Intento de autenticación de {user}. Usuario inexistente.")
                    st.stop()
                ## Verificamos si está bloqueado
                if gestor_db.get_user_bloqueado(user):
                    if (tiempo_restante_timedelta:= gestor_db.get_remaining_time_or_none(user)) is not None:
                        st.error(f"Tu cuenta está bloqueada. Tiempo restante para el desbloqueo: {tiempo_restante_timedelta.seconds // 60} minutos y {tiempo_restante_timedelta.seconds % 60} segundos. ")
                        logging.info(f"Intento de autenticación de {user}. Cuenta bloqueada. tiempo restante desbloqueo:{tiempo_restante_timedelta.seconds // 60} minutos y {tiempo_restante_timedelta.seconds % 60} segundos. ")
                        st.stop()
                    ## Desbloqueamos la cuenta
                    gestor_db.desbloquear_cuenta(user)
                ## Creamos el dict trackeo de número de intentos de ingresar por usuario
                st.session_state["auth_attempts"] = st.session_state.get("auth_attempts",{})
                ## Verificamos que la contraseña sea correcta
                contraseña_real = gestor_db.get_user_hashpass(user)
                if not val.verificar_contraseña(password, contraseña_real):                    
                    ## Incrementamos el número de attempts en sesión
                    st.session_state["auth_attempts"].update({
                        user: st.session_state.get("auth_attempts",{}).get(user,0) + 1
                    })
                    intentos = NUM_INTENTOS - st.session_state["auth_attempts"].get(user,0)

                    if intentos == 0:
                        ## Bloqueamos la cuenta
                        gestor_db.bloquear_cuenta(user)
                        st.error(f"Tu cuenta ha sido bloqueada durante {db.BLOCKING_TIME} minutos.")
                        logging.info(f"Intento de autenticación de {user}. Bloqueo de cuenta por superar el límite de intentos permitidos.")
                        st.stop()
                                                    
                    st.error("La contraseña no es correcta. Intentos restantes: {}".format(intentos))
                    logging.info(f"Intento de autenticación de {user}. Contraseña incorrecta.")
                    st.stop()
                ## Verificamos si el usuario está activo
                if not gestor_db.get_user_activo(user):
                    st.error("Tu cuenta no está activada. Contacta con el administrador para activar tu cuenta.")
                    logging.info(f"Intento de autenticación de {user}. Cuenta inactiva.")
                    st.stop()

                st.success("OK")           
                with st.spinner("Cargando información personal"):
                    ## Guardamos los datos en sesión para meter en la plantilla
                    cargar_datos_user_en_sesion(user, gestor_db)
                    logging.info(f"Autenticación CORRECTA de {user}.")
                    time.sleep(1)
                st.rerun()
        
            else:
                st.error("Los campos no pueden estar vacíos.")
                logging.info(f"Intento de autenticación de {user}. Campos vacíos.")

    texto("¿No estás registrado? Ve al apartado <b>Registrarse</b>", font_size=15)
   

def registrarse(gestor_db:db.UserDBHandler, gestor_email_admin:em.EmailManager) -> None:
    texto("~ Registrarse ~", color='#c54933', formato='b', font_size=40)
    texto("Regístrate para poder enviar emails en tu nombre", formato='i')
    
    with st.form("identificarse",clear_on_submit=False):
        st.info("Los campos con * aparecerán en los mails personalizados")
        col1, col2 = st.columns(2)
        with col1:            
            user = st.text_input("Usuario",
                                 help="El usuario no puede contener espacios en blanco")
            password_reg = st.text_input("Contraseña", 
                                         type="password", 
                                         help=f"La contraseña debe de tener al menos {val.PASS_LEN} caracteres totales, {val.PASS_NUMS} números, {val.PASS_SPECIAL} caracteres especiales y {val.PASS_CHAR} letras.",
                                         on_change=None) 
            email = st.text_input("Email")         

        with col2:
            name = st.text_input("Nombre Completo*")
            puesto = st.text_input("Puesto *", placeholder="Ej: Sales Manager")
            telefono = st.text_input("Teléfono de contacto *")
            
        submit = st.form_submit_button("Registrarse")        

        if submit:
            ## Validamos primero campos vacíos
            if user and password_reg and email and puesto and telefono and name:
                ## Validamos usuario correcto
                if (user_error:=val.validar_usuario(user, gestor_db)):
                    st.error(user_error)
                    logging.info(f"Registro incorrecto de usuario {user} por el motivo: {user_error}")
                    st.stop()
                ## Validamos email correcto
                elif (email_error:=val.validar_email_db(email, gestor_db)):
                    st.error(email_error)
                    logging.info(f"Registro incorrecto de usuario {user} por el motivo: {email_error}")
                    st.stop()
                ## Validamos contraseña correcta
                elif (pass_error:=val.validar_contraseña(password_reg)):
                    st.error(pass_error)
                    logging.info(f"Registro incorrecto de usuario {user} por el motivo: {pass_error}")
                    st.stop()
                
                ## Proceder a realizar el registro en base de datos
                with st.spinner("Registrando..."):
                    try:
                        ## Insertamos en base de datos      
                        gestor_db.insert(
                            db.Usuario(
                                nombre_completo=name,
                                usuario=user,
                                contraseña=val.hashear_contraseña(password_reg),
                                email=email,
                                puesto=puesto,
                                telefono=telefono,
                            )                        
                        )
                        texto_resgistro = f"[pSK] Nuevo registro de {name}: {email} - Activar cuenta de usuario"
                        ##Enviamos mail a administrador
                        gestor_email_admin.enviar(
                            ADMIN_MAIL,
                            texto_resgistro,
                            texto_resgistro,
                        )
                        st.success("""
                                Registro realizado correctamente para **{nombre}**.
                                \nSe le ha enviado una notificación al administrador {mail} para que active tu cuenta."""
                                .format(
                                    nombre=" ".join(n.capitalize() for n in name.split()),
                                    mail=ADMIN_MAIL))
                        logging.info(f"Registro completado de {name}, {user} con mail {email}. Envío de mail correcto.")
                    except Exception as exc:
                        st.error(f"No se ha podido registrar. Ha ocurrido el siguiente error: {exc}")
                        logging.error(f"Se ha producido un error al registrar al usuario {user}. Erro: {exc}")
            
            else:
                st.error("Ningún campo puede estar vacío.")
                logging.info(f"Intento de registro fallido con campos vacíos.")
                st.stop()


def distribuir(nombre_usuario:str) -> None:
    texto("~ Distribuir ~", color='#c54933', formato='b', font_size=40)
    texto("Carga un archivo excel y envía decenas de mails en segundos")

    añadir_salto()
    with st.expander("💡 Despliega para ver más información."):
        st.info(f"""
                La tabla excel deberá tener las siguientes columnas: **{", ".join(COLUMNAS_EXCEL)}**.\n
                Si los campos **email** o **sector** están vacíos, el algoritmo los ignorará y pasará a la siguiente línea.\n
                Los campos admisibles para la columna sector son: **{", ".join(get_nombre_sectores())}**.\n
                Los campos admisibles para la columna idioma son: **es, fr, en**.\n
                Si el campo **idioma** está vacío se considerará **español** por defecto.\n

                """)
    ## Widget para cargar el archivo Excel
    uploaded_file = st.file_uploader(label="Arrastra aquí tu archivo con los datos", type=["xlsx"])

    if uploaded_file is not None:
        ## Pasamos el excel al dataloader
        try:
            excel_dl = dl.ExcelDataLoader(uploaded_file)
            
        except Exception as exc:
            st.error("Se ha producido un error al cargar el archivo. Inténtalo más tarde o cambia de archivo.")
            logging.error(f"Se ha producido un error al cargar el excel para {nombre_usuario}.")
            st.stop()

        ## Validaciones del DataFrame
        if not (st.session_state.get("excel_cargado", False)):
            with st.spinner("Validando nombre de columnas en excel..."):
                ## Validar que las columnas tengan los nombres correctos
                if (diferencia:=val.validar_columnas_excel(COLUMNAS_EXCEL, excel_dl)):
                    st.error(f"""
                            Los nombres de columnas **{', '.join(diferencia)}** no son correctos.\n
                            Los nombres de las columnas a incluir son **{", ".join(COLUMNAS_EXCEL)}.**
                            """)
                    logging.info(f"Error en columnas de excel para sesión {nombre_usuario}: {', '.join(diferencia)}.")
                    st.stop()
            with st.spinner("Validando nombre de sectores en excel..."):
                ## Validar que los nombres de sectores existan y correspondan con los guardados.
                if (diferencia:=val.validar_sectores_excel(get_nombre_sectores(), excel_dl)):
                    st.error(f"""
                            Los sectores **{', '.join(diferencia)}** no son correctos.\n
                            Los nombres de las sectores a incluir son **{", ".join(get_nombre_sectores())}.**
                            """)
                    logging.info(f"Error en nombres de sectores de excel para sesión {nombre_usuario}: {', '.join(diferencia)}.")
                    st.stop()
            with st.spinner("Validando nombre de idiomas en excel..."):    
                ## Validar que los idiomas sean correctos
                if (diferencia:=val.validar_idiomas_excel(set(IDIOMAP), excel_dl)):
                    st.error(f"""
                            Los idiomas **{', '.join(diferencia)}** no son correctos.\n
                            Los nombres de los idiomas a incluir son **{", ".join(set(IDIOMAP))}.**
                            """)
                    logging.info(f"Error en nombres de idiomas de excel para sesión {nombre_usuario}: {', '.join(diferencia)}.")
                    st.stop()

            with st.spinner("Validando emails en excel..."):
                ## Verificar que los emails sean emails válidos
                if (set_mails_error:=val.validar_emails_excel(excel_dl)):
                    st.error(f"""
                            Los emails **{', '.join(set_mails_error)}** no son correctos.\n
                            Corrígelos para poder distribuir.
                            """)
                    logging.info(f"Error en nombres de emails de excel para sesión {nombre_usuario}: {', '.join(set_mails_error)}.")
                    st.stop()

                     
            st.session_state["excel_cargado"] = True ## Para no repetir el mensaje de success
            st.success("Datos cargados correctamente.")
            logging.info(f"El excel se ha cargado correctamente para la sesión {nombre_usuario}")
        
        if st.toggle("Visualiza los datos"):
            st.dataframe(excel_dl.df, use_container_width=True)       
        
        ## Tiempo de cool down
        descanso = st.slider("Escoge un tiempo de cool down entre envíos en **segundos**", min_value=5, max_value=20, value=10)
        logging.info(f"Descanso establecido para la sesión de {nombre_usuario} de {descanso} segundos.")

        ## Inicializamos gestores de db para la api key
        tabla_api_keys = 'saved_api_keys'
        gestor_mongo_apikey = db.DBHandler(tabla_api_keys)
        gestor_sqlite_apikey = db.SQLContext(nombre_tabla=tabla_api_keys, db_filename='backend/db/stats.db')

        ## Pedimos la API Key
        añadir_salto()
        texto(f"Escribe la API Key de Gmail para la cuenta <b>{get_email_comercial_sesion()}</b>.")
        gmail_key = st.text_input("Para poder enviar emails en tu nombre es necesario tener una API Key de Gmail",
                                  type='password',
                                  help="""
                                  Pasos:\n
                                  1- Ve a los parámetros de tu cuenta Gmail\n
                                  2- Activa la verificación en 2 pasos\n
                                  3- Busca con la lupa 'Crear contraseña de aplicación'\n
                                  4- Sigue las indicaciones y copia tu API Key en lugar seguro
                                    """,
                                    value=get_decrypted_api_key(
                                        nombre_usuario,
                                        gestor_sqlite_apikey=gestor_sqlite_apikey,
                                        gestor_mongo_apikey=gestor_mongo_apikey),
                                    )

        if gmail_key:
            ## Validamos la API Key de manera cutre
            if not val.validar_gmail_key_fake(gmail_key):
                st.error("La API Key no parece válida. Asegúrate de haber puesto una API de Gmail válida.")
                logging.info(f"API Key errónea para sesión {nombre_usuario}.")
                st.stop()
            
            if not (val.existe_usuario(nombre_usuario, gestor_mongo_apikey) and val.existe_usuario(nombre_usuario, gestor_sqlite_apikey)):
                guardar_api_key = st.button("Guardar API key", help="⚠️ Guardar la api key puede no ser seguro.")
                if guardar_api_key:
                    ## Encriptamos la api key sacando llave y valor encriptado
                    gmail_key_encriptada, key = val.encriptar_fernet(gmail_key)    
                    try:
                        ## Metemos en mongodb el objeto llave
                        gestor_mongo_apikey.insert(
                            db.ApiKey(
                                objeto_key=key,
                                usuario=nombre_usuario,
                            )                    
                        )
                        ## Metemos en sqlite la api key encriptada
                        gestor_sqlite_apikey.insert_one(
                            {
                                'usuario': nombre_usuario,
                                'apikey': gmail_key_encriptada
                            }
                        )
                        st.success("✅ Se ha **guardado** correctamente tu api key de gmail.")
                        logging.info(f"API Key guardada correctamente para usuario {nombre_usuario}.")
                    except Exception as exc:
                        st.error(f"⛔ Se ha producido el siguiente error: {exc}.")
                        logging.error(f"Se ha producido el siguiente error al guardar la api key para la sesión {nombre_usuario}: {exc}.")
            else:
                borrar_api_key = st.button("Borrar API key")
                if borrar_api_key:
                    try:
                        ## Borramos en mongo y en sqlite
                        gestor_mongo_apikey.delete_one('usuario', nombre_usuario)
                        gestor_sqlite_apikey.delete_one(campo_buscado='usuario',valor_buscado=nombre_usuario)
                        st.success("✅ Se ha **borrado** correctamente tu api key de gmail.")
                        logging.info(f"La API Key se ha borrado correctamente para el usuario {nombre_usuario}.")
                    except Exception as exc:
                        st.error(f"⛔ Se ha producido el siguiente error al borrar: {exc}.")
                        logging.error(f"Se ha producido un error al borrar la api key para la sesión {nombre_usuario}: {exc}.")

            añadir_salto()
            texto("Escoge el tipo de plantilla a utilizar")
            tipo_plantilla = st.radio(
                "Tipo de plantilla a utilizar para el mailing",
                options=[
                    "plantillas_prosp",
                    "plantillas_react",
                    ],
                format_func=lambda x: PLANTILLA_MAP[x],

            )
            st.info("""
                    💡 Asegúrate de que los datos cargados en el excel coincidan con la plantilla que has seleccionado.\n
                    Para cargar plantillas ve al apartado **Personalizar**.
                    """)
            
            if not sacar_plantilla_html_de_sesion(tipo_plantilla=tipo_plantilla, idioma='es'):
                st.error("⛔ No dispones de plantilla en español. Ve al apartado **Personalizar** para cargar una.")
                st.stop()

            ## Mostrar si existen plantillas para esa plantilla en idiomas. Explicar que de no existir se saltará la línea.
            for language in ['fr', 'en']:
                if sacar_plantilla_html_de_sesion(tipo_plantilla=tipo_plantilla, idioma=language):
                    st.success("✅ Disponible plantilla en {}.".format(IDIOMAP[language]))
                else:
                    st.error("⛔ No dispones de plantilla en {}. Ve al apartado **Personalizar** para cargar una.\
                              Los clientes que requieran traducción al {} serán ignorados.".format(IDIOMAP[language]))
                    
            ## Cargar un archivo adjunto
            texto("Escoge los archivos pdf a adjuntar")
            archivos_adjuntos = st.file_uploader("Carga archivos pdf para adjuntar", accept_multiple_files=True, type=["pdf"])

            distribuir = st.button("Comenzar los envíos")
            if distribuir:
                ic(archivos_adjuntos) #! DEBUG
                ## Inicializamos el gestor sql
                gestor_sql_client_done = db.SQLContext(nombre_tabla='client_done', db_filename='backend/db/stats.db')
                with st.status("Log del proceso"): ##TODO usar framework logging en archivo ?
                    ## Sacamos las filas totales del excel antes de manipular ya que las eliminamos al final.
                    filas_excel = len(excel_dl)
                    ## Creamos lista de indices a borrar (estos índices serán los que SI se han podido mandar. Instancia de la clase con Lock)
                    idx_to_delete:w.IndexListWithLock = w.IndexListWithLock() # Lista con Lock por si metemos threading
                    email_manager = em.EmailManager(get_email_comercial_sesion(), gmail_key)
                    start = time.perf_counter()

                    ## Empezamos el bucle
                    for idx, row in enumerate(excel_dl):
                        ## cargamos inputs del excel
                        receiver = row["email"]
                        nombre_receptor = "" if (name:=row["receptor"]) is np.nan else name
                        sector = row["sector"]
                        idioma = 'es' if row["idioma"] is np.nan else row["idioma"] ## ponemos español por defecto si el idioma está vacío.

                        texto_descriptivo(f"> Destinatario <b>{idx + 1}/{filas_excel}: {'~vacío~' if receiver is np.nan else receiver} en {IDIOMAP[idioma]}<b>")
                        ## Si no hay email o sector pasamos al siguiente
                        if (receiver is np.nan) or (sector is np.nan):
                            texto_error(f">> Los campos del <b>mail o sector</b> están vacíos. Pasando al siguiente.")
                            if idx == filas_excel - 1:
                                print_final_de_bucle(start, filas_excel, idx_to_delete)
                                break
                            else:
                                continue
                        ## Si es un idioma que no sea español y no hay plantilla cargada, pasamos al siguiente
                        if (idioma != 'es') and (not sacar_plantilla_html_de_sesion(tipo_plantilla=tipo_plantilla, idioma=language)):
                            texto_error(f">> No hay plantilla guardada en {IDIOMAP[idioma]}. Pasando al siguiente.")
                            if idx == filas_excel - 1:
                                print_final_de_bucle(start, filas_excel, idx_to_delete)
                                break
                            else:
                                continue                        
                        ## Comprobar con base de datos SQLite si el email ya se había utilizado.
                        if gestor_sql_client_done.find_one(campo_buscado='email', valor_buscado=receiver):
                            fecha_existente = gestor_sql_client_done.find_one_field(campo_buscado='email', valor_buscado=receiver, campo_a_retornar='fecha')
                            comercial_emisor = gestor_sql_client_done.find_one_field(campo_buscado='email', valor_buscado=receiver, campo_a_retornar='comercial')
                            texto_error(f">> Ya se ha enviado email a la dirección: {receiver} con fecha {fecha_existente} por {comercial_emisor}. Pasando al siguiente.")
                            ## Modificamos celda del mail con motivo del rechazo
                            row["email"] = receiver + ' (ya enviado)'
                            if idx == filas_excel - 1:
                                print_final_de_bucle(start, filas_excel, idx_to_delete)
                                break
                            else:
                                continue
                                                
                        ## Creamos el handler de la plantilla
                        handler = tm.HTMLTemplateManager(
                            configuracion_plantilla, 
                            st.session_state["parametros_comercial_sesion"], 
                            template_file=sacar_plantilla_html_de_sesion(tipo_plantilla, idioma))

                        ## Formateamos el cuerpo del body
                        formatted_body = handler.formatear_plantilla(
                                        idioma=idioma,
                                        **get_sector_from_session_by_name(sector), 
                                        nombre_receptor=nombre_receptor,
                                        )

                        ## Enviamos el mail 
                        if not archivos_adjuntos:
                            archivos_adjuntos = None
                        ic(archivos_adjuntos)
                        
                        ## Worker con posibilidad en un futuro de meter en un Thread
                        w.worker_send_and_insert(
                            idx=idx,
                            func_print_ok=texto_correcto,
                            func_print_error=texto_error,
                            enviar=email_manager.enviar,
                            enviar_kwargs={
                                'email_receptor': receiver,
                                'asunto': handler.get_asunto(nombre_receptor, sector, idioma, **get_sector_from_session_by_name(sector)),
                                'contenido': formatted_body,
                                'adjuntos': archivos_adjuntos,
                            },
                            index_list=idx_to_delete,
                            insert_one=gestor_sql_client_done.insert_one,
                            insert_kwargs=dict(
                                row, 
                                fecha=db.format_datetime(), # Agregamos la fecha a la base de datos
                                tipo_plantilla=tipo_plantilla, # Agregamos el tipo de plantilla que se ha usado
                                comercial=get_nombre_comercial_sesion() # Agregamos el nombre del comercial
                                ) 
                        )

                        if idx == filas_excel - 1:
                            print_final_de_bucle(start, filas_excel, idx_to_delete)
                            break
                        ## Esperamos para no causar overflow
                        texto_descriptivo(f"Esperando {descanso} segundos.")
                        time.sleep(descanso)

                ## Eliminamos del dataframe los índices gestionados correctamente
                excel_dl.remove_rows(idx_to_delete)
                ## Mostrar dataframe resultante con las filas que no se han podido gestionar si no es df vacío
                if len(excel_dl) > 0:
                    texto("Tabla con filas que no se han podido procesar")
                    st.dataframe(excel_dl.df, use_container_width=True)
                    ## Generar enlace de descarga
                    st.download_button(
                                label="Descargar Excel",
                                data=excel_dl.to_excel(),
                                file_name=f'{uploaded_file.name}_{tipo_plantilla}_{get_nombre_comercial_sesion()}.xlsx',
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                )    
    else:
        st.session_state["excel_cargado"] = False
        

def mostrar_logica_traduccion(
        handler:tm.HTMLTemplateManager,
        sector_formateo:str,
        gestor_db_plantilla:db.TemplateDBHandler,
        hay_plantilla_en_sesion:str, 
        tipo_plantilla:Literal["plantillas_prosp", "plantillas_react"], 
        idioma:Literal["fr", "es", "en"])-> None:
    """Encapsula la lógica que muestra y gestiona las traducciones de frances e ingles
    para evitar repetición de código

    Parameters
    ----------
    tipo_plantilla : Literal[&quot;plantillas_prosp&quot;, &quot;plantillas_react&quot;]
        _description_
    idioma : Literal[&quot;fr&quot;, &quot;es&quot;, &quot;en&quot;]
        _description_
    """
    if not (plantilla_traduccion_guardada:=sacar_plantilla_html_de_sesion(tipo_plantilla, idioma)):
        st.error("⛔ No dispones de traducción al **{}**".format(IDIOMAP[idioma]))
        
        if hay_plantilla_en_sesion: ## Si hay una plantilla en español guardada damos la posibildiad de traducir
            # Comprobamos primero que no se haya traducido ya:
            nombre_temporal = "plantilla_" + idioma + "_temporal"
            if (traduccion_temp:=st.session_state.get(nombre_temporal, "")):
                handler_idioma = tm.HTMLTemplateManager(
                    configuracion_plantilla, 
                    st.session_state["parametros_comercial_sesion"], 
                    template_file=traduccion_temp,
                    )
                ## Mostramos la traducción temporal
                st.markdown(
                handler_idioma.formatear_plantilla(
                    idioma=idioma,
                    **get_sector_from_session_by_name(sector_formateo), 
                    nombre_receptor="Torcuato",
                    ),
                unsafe_allow_html=True,
                )
                ## Boton para guardar
                guardar_plantilla_traduccion = st.button("Guardar la traducción")
                if guardar_plantilla_traduccion:
                    ## Metemos en db la plantilla traducida
                    try:
                        gestor_db_plantilla.insert(
                            db.Plantilla(
                                html=traduccion_temp,
                                tipo=PLANTILLA_MAP[tipo_plantilla],
                                idioma=idioma
                            )
                        )
                        st.success(f"Se ha guardado con éxito la plantilla traducida al {idioma}.")
                        logging.info(f"Se ha guardado con éxito la plantilla traducida al {idioma}.")
                        ## Borramos la plantilla temporal de la sesion
                        del st.session_state[nombre_temporal]
                        time.sleep(1)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Ha surgido el siguiente error al guardar la plantilla: {exc}")
                        logging.error(f"Se ha guardado con éxito la plantilla traducida al {idioma}.")                            

                ## Boton para borrar
                borrar_plantilla_temporal = st.button("Borrar plantilla temporal")
                if borrar_plantilla_temporal:
                    del st.session_state[nombre_temporal]
                    logging.info(f"Se ha borrado la plantilla temporal.")
                    st.rerun()

            else: ## Como no hemos traducido, damos opción para la traducción
                traducir = st.button("Traducir al {}".format(IDIOMAP[idioma]), help="Se usará una IA para la traducción.".format(IDIOMAP[idioma]))
                if traducir:
                    with st.spinner("Traduciendo al {}...".format(IDIOMAP[idioma])):
                        try:
                            ## traducimos
                            plantilla_traducida = handler.traducir(IDIOMAP[idioma]) ## TODO tb el mapping aqui
                            ## Metemos en sesión de forma temporal
                            st.session_state[nombre_temporal] = plantilla_traducida
                            st.success("Traducción realizada correctamente.")
                            logging.info(f"Se ha realizado correctamente la traducción al {idioma}.")
                            time.sleep(1)
                            st.rerun() # reruneamos para mostrar la traducción sacada de sesión
                        except Exception as exc:
                            st.error(f"Se ha producido un error al traducir: {exc}.")
                            logging.error(f"Se ha producido un error al traducir al {idioma}: {exc}.")               
        else:
            st.error("Guarda una plantilla para poder traducir.")
        añadir_salto()
    else:
        st.success("✅ Disponible traducción en **{}**.".format(IDIOMAP[idioma])) ## TODO mapping
        ## Creamos el handler para la traduccion y formateo
        handler_traduccion = tm.HTMLTemplateManager(
        configuracion_plantilla, 
        st.session_state["parametros_comercial_sesion"], 
        template_file=plantilla_traduccion_guardada)
        ## Mostrar la traducción al idioma
        if st.toggle("Previsualiza la traducción al {}".format(IDIOMAP[idioma])):     
            st.markdown(
                handler_traduccion.formatear_plantilla(
                    idioma,
                    **get_sector_from_session_by_name(sector_formateo), 
                    nombre_receptor="Torcuato",
                    ),
                unsafe_allow_html=True,
            )
        ## Mostrar boton de borrar traducción
        añadir_salto()
        borrar_traduccion_plantilla = st.button("Borrar traducción {}".format(IDIOMAP[idioma]))
        if borrar_traduccion_plantilla:
            ## Borramos la traduccion en Db
            gestor_db_plantilla.delete_one("idioma", idioma)
            ##Borramos la plantilla en sesion
            borrar_plantilla_de_sesion(tipo_plantilla, idioma)
            st.success("Plantilla borrada correctamente.")
            logging.info(f"Se ha borrado correctamente la plantilla {tipo_plantilla} en idioma {idioma}.")
            time.sleep(1)
            st.rerun()


def mostrar_interfaz_plantillas(
        tipo_plantilla:Literal["plantillas_prosp", "plantillas_react"],
        variables_para_plantilla:set,
        sector_formateo:str,
        gestor_db_plantilla:db.TemplateDBHandler,


) -> None:
    nombre_plantilla = PLANTILLA_MAP[tipo_plantilla]
    texto(f"Plantilla {nombre_plantilla} <b>Español</b>", color=configuracion_plantilla["rojo_talsa"], font_size=19)
    ## Mostramos la plantilla que habrá sido cargada en sesión
    if (hay_plantilla_en_sesion:=sacar_plantilla_html_de_sesion(tipo_plantilla, 'es')):
        ## Mostrar la plantilla en español
        plantilla:str = hay_plantilla_en_sesion
        st.success("✅ Hay una plantilla guardada en **español**.")
    else:
        ## Mostramos el uploader
        st.error("⛔ No dispones de plantilla **guardada** en español !")
        plantilla:UploadedFile = st.file_uploader(f"Carga una plantilla en Español para {nombre_plantilla}", type=["txt"])

    if plantilla is not None:
        ## Comprobamos si viene de archivo cargado para leerlo y pasarlo a bytes
        if isinstance(plantilla, UploadedFile):
            plantilla = plantilla.read()
                        
        ## Creamos el handler
        handler = tm.HTMLTemplateManager(
            configuracion_plantilla, 
            st.session_state["parametros_comercial_sesion"], 
            template_file=plantilla)
        
        ## Comprobar aqui que no haya ninguna variable que este en plantilla y no en sesión (porque daría error)
        if (variables_error:=val.verificar_existen_todas_variables_plantilla(handler, variables_para_plantilla)):
            st.error("Las variables: {} de la plantilla no son posibles ya que no están definidas. Mira el desplegable más arriba\
                        para ver las variables a incluir en la plantilla.".format(", ".join(variables_error)))
            logging.info(f"Variables no válidas para plantilla {tipo_plantilla}: {', '.join(variables_error)}")
            st.stop()        
        
        if st.toggle(f"Previsualiza la plantilla {nombre_plantilla} con el sector {sector_formateo}"):     
            st.markdown(
                handler.formatear_plantilla(
                **get_sector_from_session_by_name(sector_formateo), 
                nombre_receptor="Torcuato",
                ),
                unsafe_allow_html=True,
            )
            st.info("💡 La visualización de la plantilla en Gmail puede variar ligeramente ya que Gmail introduce algunos saltos de línea adicionales.")
        
        if st.session_state.get(tipo_plantilla, []):
            ## Significa que hay en sesion guardada y por lotanto en db
            borrar_plantilla = st.button(f"Borrar plantilla {nombre_plantilla}", help="Al hacer clic se borrará la plantilla en español.")
            if borrar_plantilla:
                try:
                    gestor_db_plantilla.delete_one("idioma", "es")
                    del st.session_state[tipo_plantilla]
                    st.success("Plantilla borrada correctamente.")
                    logging.info(f"Se ha borrado correctamemte la plantilla {tipo_plantilla}.")
                    time.sleep(1)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Se ha producido el siguiente error al borrar: {exc}.")
                    logging.error(f"Se ha producido un error al borrar la plantilla {tipo_plantilla}.")                
            
        else:
            guardar_plantilla = st.button(f"Guardar plantilla {nombre_plantilla}")
            if guardar_plantilla:
                ## Metemos en db la plantilla
                try:
                    gestor_db_plantilla.insert(
                        db.Plantilla(
                            html=handler.html,
                            tipo=PLANTILLA_MAP[tipo_plantilla],
                            idioma="es"
                        )
                    )
                    st.success("Se ha guardado con éxito la plantilla.")
                    logging.info(f"Se ha guardado con éxito la plantilla.")
                    time.sleep(1)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Ha surgido el siguiente error al guardar la plantilla: {exc}.")
                    logging.error(f"Se ha producido un error al guardar la plantilla: {exc}.")
    
    else:
        handler = tm.HTMLTemplateManager(
            configuracion_plantilla, 
            st.session_state["parametros_comercial_sesion"], 
            )

    ## Gestionar las traducciones de la plantilla.
    añadir_salto()
    
    colu1, colu2 = st.columns(2)
    ## Comprobar si hay traducción al francés y al inglés y mostrar boton
    
    with colu1: ## Columna 1 para francés.
        mostrar_logica_traduccion(
        handler,
        sector_formateo,
        gestor_db_plantilla,
        hay_plantilla_en_sesion,
        tipo_plantilla,
        'fr'
    )

    with colu2: ## Columna 1 para ingles.
        mostrar_logica_traduccion(
        handler,
        sector_formateo,
        gestor_db_plantilla,
        hay_plantilla_en_sesion,
        tipo_plantilla,
        'en',
    )


def personalizar(
        gestor_db_user:db.UserDBHandler, 
        gestor_db_sector:db.SectorDBHandler, 
        gestor_db_plantilla_prosp:db.TemplateDBHandler,
        gestor_db_plantilla_react:db.TemplateDBHandler,
        )-> None:
    texto("~ Personalizar ~", color='#c54933', formato='b', font_size=40)
    texto("1. Modifica los datos de tu <b>cuenta</b>", font_size=35)
    añadir_salto()

    ## Mostramos los valores del datos del comercial activo en la sesión
    with st.form("Modificar los datos"):
        co1, co2 = st.columns(2)

        with co1:
            user = st.text_input("Usuario", value=st.session_state.get("parametros_comercial_sesion", {}).get("usuario", ""), disabled=True)
            mail = st.text_input("Email", value=st.session_state.get("parametros_comercial_sesion", {}).get("email", ""))
            telefono = st.text_input("Teléfono", value=st.session_state.get("parametros_comercial_sesion", {}).get("telefono", ""))
        with co2:
            nombre_completo = st.text_input("Nombre Completo", value=st.session_state.get("parametros_comercial_sesion", {}).get("nombre_completo", ""))
            puesto = st.text_input("Puesto", value=st.session_state.get("parametros_comercial_sesion", {}).get("puesto", ""))
            col1, col2 = st.columns(2)
            with col1:
                añadir_salto()
                modificar = st.form_submit_button("Modificar datos")
        if modificar:
            with st.spinner("Modificando datos..."):
                ## Verificar si los datos han cambiado
                valores_modificados = {
                    "nombre_completo": nombre_completo,
                    "telefono": telefono,
                    "puesto": puesto,
                    "email": mail,
                }
                if (dict_cambios:=comprobar_campos_modificados(st.session_state.get("parametros_comercial_sesion", {}), valores_modificados)):
                    ## Validamos el mail si está
                    if "email" in dict_cambios:
                        if not val.email_valido(mail):
                            st.error("El email no tiene un formato válido.")
                            logging.info(f"Modificación de datos de usuario {user} erróneo por mail inválido.")
                            time.sleep(1)
                            st.rerun()
                        
                    ## Metemos en db el dict de cambios
                    gestor_db_user.update("usuario", user, dict_cambios)
                    ## Volver a cargar los datos en sesión
                    cargar_datos_user_en_sesion(user, gestor_db_user)
                    st.success("Datos modificados correctamente: {}".format(", ".join(dict_cambios.values())))
                    logging.info(f"Modificación de datos de usuario {user} correcta. Valores modificados: {dict_cambios}")

    ## Opción para modificar la contraseña
    with st.expander("💡 Despliega para **modificar** la contraseña"):
        with st.form("Escribe tu contraseña", clear_on_submit=True):
            pass_actual = st.text_input("Escribe tu contraseña actual", type="password")
            pass_nueva = st.text_input("Escribe la nueva contraseña", type="password")
            pass_repeat = st.text_input("Repite la nueva contraseña", type="password")
            cambiar_pass = st.form_submit_button("Cambiar la contraseña" )

            if cambiar_pass:                
                if not pass_actual or not pass_nueva or not pass_repeat:
                    st.error("Ningún campo puede estar vacío.")
                    logging.info(f"Modificación de contraseña del usuario {user} errónea por campos vacíos.")
                    time.sleep(1)
                    st.rerun()
                if pass_nueva != pass_repeat:
                    st.error("Las contraseñas no coinciden")
                    logging.info(f"Modificación de datos de usuario {user} erróneo porque las contraseñas no coinciden.")
                    time.sleep(1)
                    st.rerun()
                ## Validar contraseña nueva formato
                if (msg_validacion_pass:=val.validar_contraseña(pass_nueva)) is not None:
                    st.error(msg_validacion_pass)
                    logging.info(f"Modificación de contraseña de usuario {user} erróneo por motivo: {msg_validacion_pass}.")
                    time.sleep(1)
                    st.rerun()
                ## Validar que la contraseña actual sea correcta
                user = st.session_state.get("parametros_comercial_sesion", {}).get("usuario", "")
                if not val.verificar_contraseña(pass_actual, gestor_db_user.get_user_hashpass(user)):
                    st.error(f"La contraseña para el usuario **{user}** no es correcta.")
                    logging.info(f"Modificación de contraseña de usuario {user} erróneo porque la contraseña es incorrecta.")
                    time.sleep(2)
                    st.rerun()
                ## Reemplazar en db la contraseña hasheada
                gestor_db_user.update("usuario", user, {"contraseña": val.hashear_contraseña(pass_nueva)})
                st.success(f"Contraseña cambiada **correctamente** para el usuario {user}.")
                logging.info(f"Modificación de contraseña de usuario {user} realizada correctamente.")

    ## Opción borrar la cuenta
    with st.expander("💡 Despliega para **borrar** la cuenta"):
        st.info("⚠️ Al pulsar el botón **Borrar Todo** se borrarán todos los datos de tu cuenta.")
        borrar_cuenta = st.button("Borrar todo")
        if borrar_cuenta:
            with st.spinner("Borrando..."):
                user = st.session_state.get("parametros_comercial_sesion", {}).get("usuario", "")
                #ic(user)
                ## Hacer un delete del usuario y un rerun de la aplicación
                gestor_db_user.delete_one("usuario", user)
                ## Borramos al usuario de la sesión
                del st.session_state["parametros_comercial_sesion"]
                logging.info(f"Borrada la cuenta de {user}.")
                st.rerun()

    añadir_salto()
    texto("2. Personaliza los datos de los <b>sectores</b>", font_size=35)
    texto("Sectores guardados", color=configuracion_plantilla["rojo_talsa"], font_size=19)
    ## Mostrar los sectores guardados y sus campos en forma de tabla
    if st.toggle("Mostrar los sectores guardados y sus campos"):
        df = pd.DataFrame(st.session_state.get("sectores",[]))
        st.dataframe(
            df,
            column_config={
                "nombre_sector": "Sector",
                "nombre_sector_fr": "Nombre Francés",
                "nombre_sector_en": "Nombre Inglés",
                "enlace_img1": "Imagen 1",
                "enlace_img2": "Imagen 2",
                "clientes_satisfechos": "Número de clientes satisfechos",
                "listado_clientes": "Clientes"
            },
            hide_index=True,
            use_container_width=True,
        )
    
    añadir_salto()
    texto("Añadir sector", color=configuracion_plantilla["rojo_talsa"], font_size=19)
    with st.expander("💡 Despliega para **añadir** un nuevo sector"):
        ## Formulario para añadir un nuevo sector. Todos los campos requeridos.
        with st.form("Añade un nuevo sector", clear_on_submit=True):
            st.info("""
                    Los campos de los sectores serán utilizados en las plantillas. Ningún campo puede estar vacío.\n
                    Ingresa el nombre del sector en español y será traducido automáticamente al inglés y francés.\n
                    Si las traducciones no son de tu agrado podrás cambiarlas en el desplegable **modificar** más abajo.
                    """)
            col1, col2 = st.columns(2)
            with col1:
                nombre_sector = st.text_input(
                    "Nombre del sector en español",
                    help="Importante: Este campo saldrá en las plantillas. Se traducirá automáticamente al francés e inglés",
                    placeholder="invernaderos",
                )
                enlace_img1 = st.text_input(
                    "Enlace a perfil 1",
                    help="Enlace a una imagen en la nube, por ejemplo en Imgur."
                )
                enlace_img2 = st.text_input(
                    "Enlace a perfil 2",
                    help="Enlace a una imagen en la nube, por ejemplo en Imgur."
                )
            with col2:
                clientes_satisfechos = st.text_input(
                    "Cuantos clientes del sector están satisfechos",
                    help="Poner solo un número"
                )
                listado_clientes = st.text_input(
                    "Clientes a incluir de ejemplo en la plantilla",
                    help="Escribe los clientes separados por un espacio.",
                )
                añadir_salto()
                agregar_sector = st.form_submit_button("Agregar sector")
            
            if agregar_sector:
                ## Validación campos vacios
                if not nombre_sector or not enlace_img1 or not enlace_img2 or not clientes_satisfechos or not listado_clientes:
                    st.error("Ningún campo puede estar vacío.")
                    logging.info(f"Error al añadir sector nuevo {nombre_sector}: campos vacíos.")
                    time.sleep(1)
                    st.rerun()                
                ## Verificamos que no exista el nombre del sector en db
                if val.existe_sector(nombre_sector, gestor_db_sector): 
                    st.error("El nombre del sector ya existe.")
                    logging.info(f"Error al añadir sector nuevo {nombre_sector}: El nombre del sector ya existe.")
                    time.sleep(1)
                    st.rerun()
                ## Verificamos que el numero de clientes sea un integer
                try:
                    int(clientes_satisfechos)
                except ValueError:
                    st.error("El valor de clientes satisfechos no es correcto.")
                    logging.info(f"Error al añadir sector nuevo {nombre_sector}: El valor de clientes satisfechos no es correcto.")
                    time.sleep(1)
                    st.rerun()

                ## TODO : Validar que los clientes a iuncluir esten separados por espacio?
                
                ## Traducir y sacar {'es': 'invernaderos, 'fr': 'serres', 'en': 'greenhouses'}
                with st.spinner("Traduciendo nombre..."):
                    try:
                        translator = Translator()
                        nombre_sector_fr:str = translator.translate(nombre_sector, src='es', dest='fr').text
                        nombre_sector_en:str = translator.translate(nombre_sector, src='es', dest='en').text
                        logging.info(f"Traducción del nombre de sector {nombre_sector} correcta en francés e inglés.")
                    except Exception as exc:
                        st.error(f"""
                                 Se ha producido el siguiente error al traducir: {exc}.\n
                                 Inténtalo más tarde.
                                 """)
                        logging.error(f"Error al traducir el nombre de sector {nombre_sector}. Motivo: {exc}.")
                        time.sleep(1)
                        st.rerun()

                ## Proceder a realizar el registro en base de datos
                with st.spinner("Registrando sector..."):
                    try:            
                        gestor_db_sector.insert(
                            db.Sector(
                                nombre_sector=nombre_sector,
                                nombre_sector_fr=nombre_sector_fr.lower(),
                                nombre_sector_en=nombre_sector_en.lower(),
                                enlace_img1=enlace_img1,
                                enlace_img2=enlace_img2,
                                clientes_satisfechos=clientes_satisfechos,
                                listado_clientes=listado_clientes.split(),
                            )
                        )
                        st.success(f"""Se ha registrado correctamente el sector **{nombre_sector}**.""")
                        logging.info(f"Registro correcto de sector {nombre_sector}.")
                        time.sleep(1)
                        del st.session_state["sectores"]
                        st.rerun() ## Reiniciamos para que se cargue en sesión automáticamente

                    except Exception as exc:
                        st.error(f"No se ha podido registrar el sector {nombre_sector}. Ha ocurrido el siguiente error: {exc}")
                        logging.error(f"No se ha podido registrar el sector {nombre_sector}. Ha ocurrido el siguiente error: {exc}.")

    ## Si no hay sectores guardados no dejamos continuar
    if not get_nombre_sectores():
        st.error("No hay sectores guardados. Añade algún sector para poder continuar.")
        st.stop()

    añadir_salto()
    texto("Modificar o Borrar el sector", color=configuracion_plantilla["rojo_talsa"], font_size=19)
    ## Desplegable con el nombre de los sectores para escoger el que modificar
    sector_modificar = st.selectbox(
        "Selecciona el sector a modificar o borrar",
        get_nombre_sectores(),
    )
    dict_sector = get_sector_from_session_by_name(sector_modificar) or {}
    ## Mostrar los datos del sector seleccionado como en sección registro
    with st.expander("💡 Despliega para **modificar** los campos del sector"):
        with st.form("Modificar los campos del sector", clear_on_submit=False):
            st.info("Los campos de los sectores serán utilizados en las plantillas. Ningún campo puede estar vacío.")
            col1, col2 = st.columns(2)
            with col1:
                nombre_sector = st.text_input(
                    "Nombre del sector",
                    help="Importante: Este campo saldrá en las plantillas",
                    value=dict_sector.get("nombre_sector", ""),
                )
                nombre_sector_fr = st.text_input(
                    "Nombre del sector en francés",
                    help="Importante: Este campo saldrá en las plantillas",
                    value=dict_sector.get("nombre_sector_fr", ""),
                )
                nombre_sector_en = st.text_input(
                    "Nombre del sector en francés",
                    help="Importante: Este campo saldrá en las plantillas",
                    value=dict_sector.get("nombre_sector_en", ""),
                )
                clientes_satisfechos = st.text_input(
                    "Cuantos clientes del sector están satisfechos",
                    help="Poner solo un número",
                    value=dict_sector.get("clientes_satisfechos", ""),
                )
                
            with col2:               
                listado_clientes = st.text_input(
                    "Clientes a incluir de ejemplo en la plantilla (separados por un espacio)",
                    help="Escribe los clientes **separados por un espacio**.",
                    value=" ".join(dict_sector.get("listado_clientes", "")),
                )
                enlace_img1 = st.text_input(
                    "Enlace a perfil 1",
                    help="Enlace a una imagen en la nube, por ejemplo en Imgur.",
                    value=dict_sector.get("enlace_img1", ""),
                )
                enlace_img2 = st.text_input(
                    "Enlace a perfil 2",
                    help="Enlace a una imagen en la nube, por ejemplo en Imgur.",
                    value=dict_sector.get("enlace_img2", ""),
                )
                añadir_salto()
                modificar_sector = st.form_submit_button("Modificar los campos")
            
            if modificar_sector:
                ## Verificar si los datos han cambiado
                valores_modificados = {
                    "nombre_sector": nombre_sector,
                    "enlace_img1": enlace_img1,
                    "enlace_img2": enlace_img2,
                    "clientes_satisfechos": clientes_satisfechos,
                    "listado_clientes": listado_clientes.split(),
                    "nombre_sector_fr": nombre_sector_fr,
                    "nombre_sector_en": nombre_sector_en,
                }
                
                if (dict_cambios:=comprobar_campos_modificados(dict_sector, valores_modificados)):                    
                        ## Validamos que las url sean válidas
                        if (error_msg:=val.validar_img_url_en_dict_sector(dict_cambios)):
                            st.error(error_msg)
                            logging.error(f"Error al modificar campos del sector {nombre_sector}. Motivo: {error_msg}")
                            time.sleep(1)
                            st.rerun()
                        with st.spinner("Modificando valores..."):
                            try:
                                ## Metemos en db el dict de cambios
                                gestor_db_sector.update("nombre_sector", sector_modificar, dict_cambios)
                                ## Volver a cargar los datos en sesión
                                del st.session_state["sectores"]
                                st.success("Datos modificados correctamente.")
                                logging.info(f"Datos del sector {nombre_sector} modificados correctamente. Nuevos datos: {dict_cambios}")
                                time.sleep(1)
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Se ha producido el siguiente error al modificar los datos del sector: {exc}")
                                logging.error(f"Se ha producido el siguiente error al modificar los datos del sector: {exc}")


    with st.expander("💡 Despliega para **borrar** el sector"):
        st.info(f"⚠️ Al pulsar el botón se borrarán todos los datos del sector **{sector_modificar}**.")
        borrar_sector = st.button(
            "Borrar el sector", 
            help="Atención se borrará el sector y todos sus campos para siempre", 
            use_container_width=False)
        if borrar_sector:
            ## Borrar el sector y cargar la app
            try:
                gestor_db_sector.delete_one("nombre_sector", sector_modificar)
                st.success(f"El sector {sector_modificar} se ha borrado correctamente.")
                del st.session_state["sectores"]
                logging.info(f"Se ha borrado correctamente el secotr {sector_modificar}.")
                time.sleep(1)
                st.rerun()
            except Exception as exc:
                st.error(f"Se ha producido el siguiente error al borrar: {exc}.")
                logging.error(f"Se ha producido el siguiente error al borrar el sector {sector_modificar}: {exc}.")

    añadir_salto()
    texto("3. Personaliza tus <b>plantillas</b> HTML", font_size=35)
    añadir_salto()
    variables_para_plantilla:set = get_variables_para_plantilla()
    with st.expander("💡 Despliega para obtener información"):
        st.info("""
                - Deberás tener tu plantilla en formato código HTML en un archivo **txt**.
                - Sólo se aceptan archivos **txt**.                
                - Las variables deberán ir con el símbolo '\$' delante. Ejemplo: **$nombre_completo**.
                - Solo podrán incluirse en tu plantilla las siguientes variables:
                **{}, $nombre_receptor**.
                """.format(", ".join(variables_para_plantilla))
                )
    ## Desplegable con los sectores disponibles para formatear la plantilla
    sector_formateo = st.selectbox(
        "Elige el sector para formatear la plantilla",
        get_nombre_sectores(),
    )
    añadir_salto()
    col1, col2 = st.columns(2)
    
    with col1: # Columna 1 para prospección
        mostrar_interfaz_plantillas(
            tipo_plantilla="plantillas_prosp",
            variables_para_plantilla=variables_para_plantilla,
            sector_formateo=sector_formateo,
            gestor_db_plantilla=gestor_db_plantilla_prosp
        )
           
    with col2:
        mostrar_interfaz_plantillas(
            tipo_plantilla="plantillas_react",
            variables_para_plantilla=variables_para_plantilla,
            sector_formateo=sector_formateo,
            gestor_db_plantilla=gestor_db_plantilla_react
        )
    

def visualizar() -> None:
    texto("~ Visualizar ~", color='#c54933', formato='b', font_size=40)
    texto("🚧 Apartado en construcción", color='#f0c50d', formato='b', font_size=50)
    ## TODO Visualizar datos por comercial por ejemplo

    ## TODO Meter aqui logging también


def main():
    """Función principal dónde ocurre toda la lógica del frontend
    """
    ## Título de la página
    
    ## Inicializamos los gestores
    gestor_db_user = db.UserDBHandler("usuarios")
    gestor_db_sector = db.SectorDBHandler("sectores")
    gestor_email_admin = em.EmailManager(ADMIN_MAIL, ADMIN_API_KEY)
    gestor_db_plantilla_prosp = db.TemplateDBHandler("plantillas_prosp")
    gestor_db_plantilla_react = db.TemplateDBHandler("plantillas_react")

    ## Configuración del logging
    logging.basicConfig(
        filename=create_log_file(), 
        encoding='utf-8', 
        level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(message)s',
        datefmt='%H:%M:%S'
        )
    
    ## Cargamos la lista de sectores en sesión solo si no existe ya en sesión (para no estar haciendo todo el rato lecturas a db)
    if "sectores" not in st.session_state:
        cargar_sectores_en_sesion(gestor_db_sector)
    
    ## Cargamos cada plantilla en sesión si no existe
    if "plantilla_prosp" not in st.session_state:
        cargar_plantillas_en_sesion(gestor_db_plantilla_prosp)
    if "plantilla_react" not in st.session_state:
        cargar_plantillas_en_sesion(gestor_db_plantilla_react)

    with st.sidebar:
        beta_sign = """
        <span style="
        font-size: 10px;
        font-weight: bold;
        color: #ffffff;
        background-color: #ff5733;
        padding: 5px 10px;
        border-radius: 4px;
        ">
            BETA
        </span>
        """
        texto(f"""📮 pSK mailing {version_app} {beta_sign}""",
            font_size=25, 
            color='#005092', 
            formato='b')

        st.caption("Envía mails a tus leads de forma personalizada, rápida y atractiva. Recupera clientes mandando mails con plantillas personalizadas.")

        seleccion_menu = option_menu(
            menu_title="Menú",
            options=[
                "Autenticarse", 
                "Registrarse",
                "Personalizar",
                "Distribuir",                
                "Visualizar", #TODO visualiza stats y gráficos de correos enviados, hacer informes ? fechas etc, Visualizar el log aqui?
            ],
            default_index=0,
            icons=[ #lista de iconos aqui: https://icons.getbootstrap.com/
                "bookmark-check",
                "database-add",
                "magic",
                "envelope-at",                
                "graph-up",
            ],
            menu_icon="gear",
            )
        ## Firma
        st.caption("~ Done by STM 2023")
        
    ## Iniciar variables de sesión
    usuario_sesion = st.session_state.get("parametros_comercial_sesion",{}).get("nombre_completo", "")
    nombre_usuario = st.session_state.get("parametros_comercial_sesion",{}).get("usuario", "")

    if seleccion_menu == "Autenticarse":
        if not usuario_sesion:
            autenticarse(gestor_db_user, gestor_email_admin)
            logging.info(f"Seleción menú {seleccion_menu}. Usuario en sesión: {usuario_sesion}.")
        else:
            mostrar_msg_bienvenida(usuario_sesion, nombre_usuario)
            logging.info(f"Seleción menú {seleccion_menu}. Usuario en sesión: {usuario_sesion}.")

    if seleccion_menu == "Registrarse":
        if not usuario_sesion:
            registrarse(gestor_db_user, gestor_email_admin)
            logging.info(f"Seleción menú {seleccion_menu}. Usuario en sesión: {usuario_sesion}.")
        else:
            mostrar_msg_bienvenida(usuario_sesion, nombre_usuario)
            logging.info(f"Seleción menú {seleccion_menu}. Usuario en sesión: {usuario_sesion}.")

    elif seleccion_menu == "Distribuir":
        # Validamos que exista usuario autenticado
        if not usuario_sesion:
            mostrar_msg_autenticacion()
            logging.info(f"Seleción menú {seleccion_menu}. Usuario en sesión: {usuario_sesion}.")
        else:
            distribuir(nombre_usuario)
            logging.info(f"Seleción menú {seleccion_menu}. Usuario en sesión: {usuario_sesion}.")

    elif seleccion_menu == "Personalizar":
        # Validamos que exista usuario autenticado
        if not usuario_sesion:
            mostrar_msg_autenticacion()
            logging.info(f"Seleción menú {seleccion_menu}. Usuario en sesión: {usuario_sesion}.")
        else:
            personalizar(
                gestor_db_user, 
                gestor_db_sector, 
                gestor_db_plantilla_prosp=gestor_db_plantilla_prosp,
                gestor_db_plantilla_react=gestor_db_plantilla_react,
                )
            logging.info(f"Seleción menú {seleccion_menu}. Usuario en sesión: {usuario_sesion}.")
    
    elif seleccion_menu == "Visualizar":
        # Validamos que exista usuario autenticado
        if not usuario_sesion:
            mostrar_msg_autenticacion()
            logging.info(f"Seleción menú {seleccion_menu}. Usuario en sesión: {usuario_sesion}.")
        else:
            visualizar()
            logging.info(f"Seleción menú {seleccion_menu}. Usuario en sesión: {usuario_sesion}.")

        
if __name__ == '__main__':
    main()
    #st.session_state