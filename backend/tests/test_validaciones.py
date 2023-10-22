from backend.validaciones import (verificar_existen_todas_variables_plantilla,
                                validar_gmail_key_fake,
                                is_valid_image_url,
                                validar_img_url_en_dict_sector,
                                email_valido,
                                validar_contraseña,
                                PASS_LEN,
                                PASS_NUMS,
                                PASS_SPECIAL,
                                PASS_CHAR,
                                verificar_contraseña,
                                hashear_contraseña,
                                crear_contraseña_valida
                                  )

import backend.template_manager as tm

def test_verificar_existen_todas_variables_plantilla() -> None:
    plantilla_fake = """Hola $nombre_receptor, me llamo $nombre y quiero venderte el producto $producto."""
    config_plantilla = {'producto': 'limpia botas'}
    variables_comercial = {'nombre': 'Sergio'}
    template_manager = tm.HTMLTemplateManager(config_plantilla, variables_comercial, plantilla_fake)
    variables_que_existen:set = {'\$producto', '\$nombre'}
    assert verificar_existen_todas_variables_plantilla(template_manager, variables_que_existen) == set()

def test_verificar_existen_todas_variables_plantilla_no() -> None:
    plantilla_fake = """Hola $nombre_receptor, me llamo $nombre y quiero venderte el producto $producto."""
    config_plantilla = {'producto': 'limpia botas'}
    variables_comercial = {'nombre': 'Sergio'}
    template_manager = tm.HTMLTemplateManager(config_plantilla, variables_comercial, plantilla_fake)
    variables_que_existen:set = {'\$nombre'}
    assert verificar_existen_todas_variables_plantilla(template_manager, variables_que_existen) == {'\$producto'}

def test_validar_gmail_key_fake_default() -> None:
    api_key = "kkk kkk kkk"
    assert validar_gmail_key_fake(api_key) == False

def test_validar_gmail_key_fake_pass() -> None:
    api_key = "kkkgkkkgkkkgkkkg"
    assert validar_gmail_key_fake(api_key) == True

def test_is_valid_image_url_1() -> None:
    url = 'https://www.misimagenes.com/imagen.jpeg'
    assert is_valid_image_url(url) == True

def test_is_valid_image_url_2() -> None:
    url = 'https://www.misimagenes.com'
    assert is_valid_image_url(url) == False

def test_is_valid_image_url_3() -> None:
    url = 'https://www.misimagenes.com/imagen.gif'
    assert is_valid_image_url(url) == True

def test_validar_img_url_en_dict_sector() -> None:
    dict_sector = {
    'enlace_img1': 'https://i.imgur.com/Fv0NpWX.jpg',
    'enlace_img2': 'https://i.imgur.com/TnStO8u.jpg',
    'azul_talsa': "#005092",
    'rojo_talsa': "#c54933",
    }
    assert validar_img_url_en_dict_sector(dict_sector) == ""

def test_validar_img_url_en_dict_sector_2() -> None:
    dict_sector = {
    'enlace_img1': 'https://i.imgur.com',
    'enlace_img2': 'https://i.imgur.com/TnStO8u.jpg',
    'azul_talsa': "#005092",
    'rojo_talsa': "#c54933",
    }
    assert validar_img_url_en_dict_sector(dict_sector) == "La URL en enlace_img1 no es válida o no es una imagen."

def test_validar_img_url_en_dict_sector_3() -> None:
    dict_sector = {
    'azul_talsa': "#005092",
    'rojo_talsa': "#c54933",
    }
    assert validar_img_url_en_dict_sector(dict_sector) == ""

def test_email_valido() -> None:
    email = "tejedor.m@.com"
    assert email_valido(email) == False

def test_email_valido_2() -> None:
    email = "tejedor.m@gmail.com"
    assert email_valido(email) == True

def test_validar_contraseña() -> None:
    password = '12345abcd@'
    assert validar_contraseña(password) == None

def test_validar_contraseña_char() -> None:
    password = '12345abcd'
    assert validar_contraseña(password) == f"La contraseña debe tener al menos {PASS_SPECIAL} caracteres especiales '!@#$%^&*(),.?\":|<>'. Tiene 0."

def test_validar_contraseña_len() -> None:
    password = '12345'
    assert validar_contraseña(password) == f"La contraseña debe tener al menos {PASS_LEN} caracteres. Tiene 5."

def test_validar_contraseña_letras() -> None:
    password = '1234567890345324212234343452'
    assert validar_contraseña(password) == f"La contraseña debe tener al menos {PASS_CHAR} letras. Tiene 0."

def test_validar_contraseña_numeros() -> None:
    password = 'abchdjjjdkdlsdlksddjfg'
    assert validar_contraseña(password) == f"La contraseña debe tener al menos {PASS_NUMS} dígitos. Tiene 0."

def test_verificar_contraseña() -> None:
    password = "2222dddd@&"
    pass_hasheada = hashear_contraseña(password)
    assert verificar_contraseña(password, pass_hasheada) == True

def test_verificar_contraseña_fail() -> None:
    password = "2222dddd@&"
    pass_hasheada = hashear_contraseña(password)
    assert verificar_contraseña("hghgjk88dkd9@dl00dfkj", pass_hasheada) == False

def test_contraseña_creada_valida() -> None:
    assert validar_contraseña(crear_contraseña_valida()) == None