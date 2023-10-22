try: # Puede ser que la API key sea inválida. 
                            email_manager.enviar(
                                email_receptor=receiver,
                                asunto=handler.get_asunto(nombre_receptor, sector, idioma, **get_sector_from_session_by_name(sector)),
                                contenido=formatted_body,
                                adjuntos=archivos_adjuntos
                            )
                            texto_correcto(">> Envío correcto.")
                            ## Añadimos el índice a índices a eliminar                            
                            idx_to_delete.append(idx)
                            ## Guardamos los datos de la fila en base de datos SQLite
                            gestor_sql_client_done.insert_one(
                                columnas=dict(
                                    row, 
                                    fecha=db.format_datetime(), # Agregamos la fecha a la base de datos
                                    tipo_plantilla=tipo_plantilla, # Agregamos el tipo de plantilla que se ha usado
                                    comercial=get_nombre_comercial_sesion() # Agregamos el nombre del comercial
                                    ) 
                            )
                            texto_correcto(">> Guardado correcto.")

                        except Exception as exc:
                            texto_error(f">> Se ha producido el siguiente error: {exc} para el mail {receiver}.")
                            ic(exc) #! Debug    