from langchain.schema.output_parser import StrOutputParser
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv

load_dotenv()


llm = ChatOpenAI(
    temperature = 0,
    openai_api_key=os.environ["OPENAI_API_KEY"], #Sergio
    model_name="gpt-3.5-turbo",
    #request_timeout=180,
)

class LLMHandler:
    def __init__(self, llm:ChatOpenAI=llm):
        self.llm = llm

    def translate_openai(self, *, texto:str, idioma:str):
        prompt = ChatPromptTemplate.from_template('''
        Eres un asistente muy útil y obediente especializado en la traducción de manuales del español al {idioma} técnico.
        Dominas el sector metalúrgico y en concreto la laminación de perfiles metálicos.

        Se te van a pasar unos textos en formato HTML que pertenecen a una plantilla para una campaña de mailing para hacer prospección.
        Tu misión es traducir solo los textos del español al {idioma} dejando todas las etiquetas intactas.
        La plantilla tiene nombres de variables que empiezan con el símbolo $. NO traduzcas el nombre de las variables
        El lenguaje debe ser cordial y cercano.

        %Ejemplos%
        input: <p style='font-size: $tamaño_letra; color: $color_talsa; margin-top: 10px; margin-bottom: 10px;'>Buenos días <span style='font-weight: bold;'>Felix</span>,</p>
        traducción al francés: <p style='font-size: $tamaño_letra; color: $color_talsa; margin-top: 10px; margin-bottom: 10px;'>Bonjour <span style='font-weight: bold;'>Felix</span>,</p>
        traducción al inglés: <p style='font-size: $tamaño_letra; color: $color_talsa; margin-top: 10px; margin-bottom: 10px;'>Good morning <span style='font-weight: bold;'>Felix</span>,</p>

        Haz las traducciones paso a paso y con calidad.
        Devuelve solo la traducción del texto, nada más.

        %TEXTO%
        {texto}
        '''
        )

        chain = (
        prompt
        | self.llm
        | StrOutputParser()
        )

        return chain.invoke({
            "idioma": idioma,
            "texto": texto,
        })