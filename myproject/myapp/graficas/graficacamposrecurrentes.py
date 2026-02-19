import plotly.express as px
import pandas as pd
from . import siopcalidad
from . import config
from .utils import crear_columna_linea_con_logo

def generar_grafica_campos_recurrentes(start_date=None, end_date=None, selected_lineas=None):
    """
    Genera un histograma de campos penalizados recurrentes y devuelve el DF filtrado.
    """
    df = siopcalidad.obtener_datos_procesados()
    df['fechahora'] = pd.to_datetime(df['fechahora']).dt.tz_localize(None)
    df['campos_penalizados'] = df['campos_penalizados'].fillna('').replace('Sin penalizaciones', '')

    if start_date and end_date:
        filtered_df = df[
            (df['fechahora'] >= pd.to_datetime(start_date)) &
            (df['fechahora'] <= pd.to_datetime(end_date))
        ]
    else:
        filtered_df = df.copy()

    # Corregir el filtrado por línea para que coincida con los tipos de datos
    if selected_lineas:
        # Convertir la columna 'Línea' a string para la comparación
        filtered_df = filtered_df[filtered_df['Línea'].astype(str).isin(selected_lineas)]

    penalizaciones_series = filtered_df['campos_penalizados'].astype(str)
    campos_lista = penalizaciones_series.str.split(',')
    campos_exploded = campos_lista.explode().str.strip()
    campos_exploded = campos_exploded[campos_exploded != '']

    conteo_campos = campos_exploded.value_counts().reset_index()
    conteo_campos.columns = ['Campo Penalizado', 'Frecuencia']

    fig = px.bar(
        conteo_campos,
        x='Campo Penalizado',
        y='Frecuencia',
        title='Campos Penalizados Individualmente SIOP',
        text='Frecuencia'
    )
    
    fig.update_traces(
        texttemplate='%{text:,}', 
        textposition='outside',
        marker_color=config.color_predeterminado
    )

    max_y_value = conteo_campos['Frecuencia'].max() * 1.15 if not conteo_campos.empty else 10

    fig.update_layout(
        xaxis_tickangle=-45,
        yaxis_title="Número de Penalizaciones",
        xaxis_title="Campo Penalizado",
        yaxis_range=[0, max_y_value]
    )

    return fig, filtered_df.to_json(orient='split')

def get_detalle_campos_recurrentes_table(df_json, campo_penalizado):
    """
    Genera una tabla HTML con el detalle de los folios para un campo penalizado.
    """
    df = pd.read_json(df_json, orient='split')
    
    # Filtrar el DF para incluir solo las filas que contienen el campo penalizado
    df_filtrado = df[df['campos_penalizados'].str.contains(campo_penalizado, na=False)]

    # Seleccionar, ordenar y dar formato a las columnas para la tabla de detalle
    columnas_existentes = [col for col in config.columnas_deseadas if col in df_filtrado.columns]
    
    if 'Línea' not in columnas_existentes:
        df_display = df_filtrado[columnas_existentes]
    else:
        # Reutilizar la lógica de formato de `utils`
        df_con_logo = crear_columna_linea_con_logo(df_filtrado, 'Línea', config.ruta_logo_metrobus, config.mapa_colores, config.color_predeterminado)
        df_con_logo = df_con_logo.drop(columns=['Línea'])
        df_con_logo = df_con_logo.rename(columns={'Línea_Logo': 'Línea'})
        
        # Reordenar las columnas para que 'Línea' aparezca donde se espera
        final_cols = [col for col in config.columnas_deseadas if col in df_con_logo.columns]
        df_display = df_con_logo[final_cols]

    return df_display.to_html(classes=['table', 'table-striped', 'table-hover'], index=False, escape=False)
