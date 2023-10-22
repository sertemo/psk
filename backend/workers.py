from typing import Callable
from icecream import ic
from threading import Lock, Thread


class IndexListWithLock(list):
    def __init__(self):
        super().__init__(self)
        self.lock = Lock()

    def append(self, idx):
        with self.lock:
            super().append(idx)

## Worker para adaptarlo más adelante a Threading
def worker_send_and_insert(
                *,
                idx:int,
                index_list:IndexListWithLock,
                func_print_ok:Callable[[str],None],
                func_print_error:Callable[[str],None],
                enviar:Callable,
                enviar_kwargs:dict,
                insert_one:Callable,
                insert_kwargs:dict,

                ):
    try: # Puede ser que la API key sea inválida. 
        enviar(**enviar_kwargs)
        func_print_ok(">> Envío correcto.")
        ## Añadimos el índice a índices a eliminar
        index_list.append(idx) ## por si se mete threading
        ## Guardamos los datos de la fila en base de datos SQLite
        insert_one(columnas=insert_kwargs)
        func_print_ok(">> Guardado correcto.")
        

    except Exception as exc:
        func_print_error(f">> Se ha producido el siguiente error: {exc}.")
        ic(exc) #! Debug