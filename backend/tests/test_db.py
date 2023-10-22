from unittest.mock import Mock, patch
from backend.db import (SQLContext,
                Usuario,
                Sector,
                Plantilla,
                ApiKey,
                )
import pytest
from pydantic import ValidationError

from icecream import ic


def test_Usuario_fecha_bloqueo() -> None:
    user = Usuario(
    nombre_completo='Rebeca García',
    usuario='rebequita',
    contraseña='44444456',
    telefono='666 666 666',
    puesto='administrativo',
    email='rebe.k@technocom.es',
    )

    assert user.fecha_bloqueo == None

def test_Usuario_activo() -> None:
    user = Usuario(
    nombre_completo='Rebeca García',
    usuario='rebequita',
    contraseña='44444456',
    telefono='666 666 666',
    puesto='administrativo',
    email='rebe.k@technocom.es',
    )

    assert user.activo == False

def test_Plantilla_tipo_bad() -> None:
    
    with pytest.raises(ValidationError):
        plantilla = Plantilla(
        html="""Esta es la plantilla de $nombre.""",
        tipo='perro',
        idioma='en',
        )
    
