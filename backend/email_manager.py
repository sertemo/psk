import yagmail
import backend.validaciones as val

class EmailManager:
    def __init__(self, email:str, api_key:str ):
        self.email = email
        self.api_key = api_key
        self.yag = yagmail.SMTP(email, api_key)

    def enviar(self,
            email_receptor:str,
            contenido:str,
            asunto:str="",
            adjuntos:list[str]=None,
            )-> None:
        
        ## Validamos mail del receptor
        if not val.email_valido(email_receptor):
            print("El formato del email no es válido")
            return False
        self.yag.send(
            to=email_receptor,
            subject=asunto,
            contents=contenido,
            attachments=adjuntos,
        )

