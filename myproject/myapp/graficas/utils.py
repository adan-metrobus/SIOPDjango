import pandas as pd

def crear_columna_linea_con_logo(df, columna_linea, ruta_logo, mapa_colores, color_predeterminado):
    """
    Crea una columna HTML para la tabla con el logo, el nombre de la línea y el color de fondo.

    Args:
        df (pd.DataFrame): DataFrame con los datos.
        columna_linea (str): Nombre de la columna de la línea.
        ruta_logo (str): Ruta al logo.
        mapa_colores (dict): Diccionario de colores por línea.
        color_predeterminado (str): Color por defecto si la línea no está en el mapa.

    Returns:
        pd.DataFrame: DataFrame con la columna HTML.
    """
    df_mod = df.copy()
    columna_logo = f"{columna_linea}_Logo"

    def get_color(linea):
        return mapa_colores.get(str(linea), color_predeterminado)

    df_mod[columna_logo] = df_mod[columna_linea].apply(
        lambda linea: f"<div style='background-color: {get_color(linea)}; color: white; border-radius: 5px; padding: 5px; text-align: center;'>"
                      f"<img src='{ruta_logo}' width='25' style='vertical-align: middle; margin-right: 8px;'/>"
                      f"<b>{linea}</b></div>"
    )
    return df_mod
