# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)

SPECIALS = str.maketrans({
    'á': 'a', 'Á': 'A',
    'é': 'e', 'É': 'E',
    'í': 'i', 'Í': 'I',
    'ó': 'o', 'Ó': 'O',
    'ú': 'u', 'Ú': 'U',
    'ñ': 'n', 'Ñ': 'N',
})


class AbstractMethodError(Exception):
    """Excepción para métodos abstractos no implementados"""
    def __str__(self):
        return 'Abstract Method'

    def __repr__(self):
        return 'Abstract Method'


class GeneratorType(type):
    """Metaclase para gestionar generadores de nómina electrónica."""
    _generators = {}

    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)

        if getattr(cls, 'code', None):
            if cls.code in mcs._generators:
                _logger.warning(f"⚠️ El generador con código '{cls.code}' ya está registrado. Se sobrescribirá.")
            mcs._generators[cls.code] = cls

        return cls

    @classmethod
    def get(mcs, code, *args, **kwargs):
        """Obtiene un generador por código."""
        if code not in mcs._generators:
            raise KeyError(f"El generador con código '{code}' no está registrado.")
        return mcs._generators[code](*args, **kwargs)


class GeneratorInterface(metaclass=GeneratorType):
    """Clase base para generadores de nómina electrónica.
    
    Para crear un nuevo generador, extiende esta clase y define:
    - `code`: Identificador único del generador
    - `name`: Nombre visible del generador
    - `generate_txt`: Método que debe ser implementado en cada generador
    """

    code = None  # Identificador único del generador
    name = None  # Nombre del generador
    description = 'Pago de Nómina'

    def remove_accent(self, word):
        """Elimina acentos de una cadena de texto usando `str.translate()`."""
        return word.translate(SPECIALS)

    def generate_txt(self, obj):
        """Método abstracto para generar archivos TXT de nómina."""
        raise AbstractMethodError()
