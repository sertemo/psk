
from string import Template
from typing import Union, Literal
import backend.llm_manager as lm


class CustomTemplate(Template):
    def __init__(self, tmp:str):
        if not isinstance(tmp, str):
            raise TypeError("La plantilla tiene que ser un string.")
        super().__init__(tmp)

    def extract_template_variables(self):
        pattern = self.pattern
        template = self.template
        return set(m.group('named') for m in pattern.finditer(template) if m.group('named'))


class HTMLTemplateManager:
    def __init__(
            self, 
            configuracion_plantilla:dict, 
            variables_comercial:dict, 
            template_file:Union[bytes, str, None]=None,
            ):
        
        if isinstance(template_file, bytes):
            ## Significa que han cargad un archivo, descodificamos los bytes a str
            template_file = template_file.decode('utf-8')

        if template_file is not None:
            self._template:CustomTemplate = CustomTemplate(template_file)
        else:
            self._template = template_file
        self.configuracion:dict = configuracion_plantilla
        self.variables_comercial:dict = variables_comercial
        self.llm_handler: lm.LLMHandler = lm.LLMHandler()
       

    def traducir(self, idioma:Literal["francés", "inglés"])-> str:
        """Devuelve un str que representa la plantilla traducida a un idioma

        Parameters
        ----------
        idioma : _type_
            _description_

        Returns
        -------
        str
            _description_
        """
        ## Pasar por openai en caso de que se hayan hecho cambios en la plantilla y quieras traducir
        traduccion = self.llm_handler.translate_openai(texto=self.html, idioma=idioma)
        if idioma == "francés":
            self._template_traduccion_fr = CustomTemplate(traduccion)
        elif idioma == "inglés":
            self._template_traduccion_en = CustomTemplate(traduccion)
        return traduccion

    def get_asunto(self, nombre_receptor, sector, idioma:Literal["fr", "en", "es"]="es", **kwargs) -> str:
        if idioma != 'es':
            ## Cambiamos el idioma del sector on the fly
            key_sector = f'nombre_sector_{idioma}'
            sector = kwargs[key_sector]
        mapping = {
            'es': f'🔝 {nombre_receptor}, mejora tu cadena de suministro con los perfiles especiales para {sector} de TALSA',
            'fr': f"🔝 {nombre_receptor}, Améliorez votre chaîne d'approvisionnement avec les profils spéciaux pour {sector} de TALSA",
            'en': f"🔝 {nombre_receptor}, Improve your supply chain with special profiles for {sector} from TALSA",
        }
        return mapping[idioma]

    @property
    def html(self)-> str:
        return self._template.template
    
    @property
    def variables_plantilla(self)-> set:
        return set('\$' + variable for variable in self._template.extract_template_variables())
 
    def formatear_plantilla(self, idioma:Literal["fr", "en", "es"]="es", **kwargs, )-> str:
        if idioma != 'es':
            ## Cambiamos el idioma del sector on the fly
            key_sector = f'nombre_sector_{idioma}'
            kwargs["nombre_sector"] = kwargs[key_sector]
        ## Pasamos a string la lista de clientes
        kwargs["listado_clientes"] = ", ".join(kwargs["listado_clientes"])
        return self._template.substitute(**self.configuracion, **self.variables_comercial, **kwargs) 

