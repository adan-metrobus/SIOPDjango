
import pandas as pd
import plotly.express as px
import unicodedata
from . import siopcalidad
from .config import mapa_colores, color_predeterminado, ruta_logo_metrobus
from .utils import crear_columna_linea_con_logo

# Palabras clave a buscar
PALABRAS_CLAVE = [
    'moto', 'potro', 'bici', 'percance', 'colisi','choqu', 'atropell',
    'frenado', 'emergenc', 'impact', 'vehicul', 'medic'
]

def normalizar_columna(series):
    if series is None: return pd.Series([None] * len(series), index=series.index)
    series_str = series.astype(str).str.lower()
    return series_str.apply(
        lambda x: ''.join(c for c in unicodedata.normalize('NFD', x) if unicodedata.category(c) != 'Mn') if pd.notnull(x) else x
    )

def generar_grafica_causas_otros(start_date, end_date, selected_lineas):
    """
    Genera la gráfica de barras con la frecuencia de palabras clave y devuelve 
    la figura y el dataframe filtrado.
    """
    df = siopcalidad.obtener_datos_procesados()
    df['fechahora'] = pd.to_datetime(df['fechahora']).dt.tz_localize(None)

    # Filtrado inicial por Causa
    df['Causa_norm'] = df['Causa'].str.lower().str.strip()
    causas_a_filtrar = [
        "otro (detallar en el campo observaciones)", 
        "", 
        "sin datos (detallar en el campo observaciones)"
    ]
    df_causas_otros = df[df['Causa_norm'].isin(causas_a_filtrar) | df['Causa'].isnull()].copy()
    df_causas_otros['Observacion_norm'] = normalizar_columna(df_causas_otros['Observación'])

    # Aplicar filtros de fecha y línea
    dff = df_causas_otros[
        (df_causas_otros['fechahora'] >= pd.to_datetime(start_date)) &
        (df_causas_otros['fechahora'] <= pd.to_datetime(end_date))
    ]
    if selected_lineas:
        dff = dff[dff['Línea'].isin(selected_lineas)]

    # Conteo de palabras clave
    observaciones_norm = dff['Observacion_norm']
    vacias_mask = observaciones_norm.isnull() | observaciones_norm.str.strip().isin(['', 'nan'])
    conteo_palabras = {'Vacias': vacias_mask.sum()}
    
    observaciones_no_vacias = observaciones_norm[~vacias_mask]
    for palabra in PALABRAS_CLAVE:
        conteo_palabras[palabra] = observaciones_no_vacias.str.contains(palabra, na=False).sum()

    df_conteo = pd.DataFrame(list(conteo_palabras.items()), columns=['Palabra Clave', 'Frecuencia'])
    df_conteo = df_conteo.sort_values(by='Frecuencia', ascending=False)
    
    # Creación de la figura
    fig = px.bar(
        df_conteo, x='Palabra Clave', y='Frecuencia',
        title='Frecuencia de Palabras Clave en Observaciones (Causa="Otro","Sin Datos",Vacias)',
        text='Frecuencia'
    )

    # Aplicar color (lógica simplificada para múltiples líneas)
    color_a_usar = color_predeterminado
    if len(selected_lineas) == 1 and selected_lineas[0] in mapa_colores:
        color_a_usar = mapa_colores[selected_lineas[0]]

    fig.update_traces(texttemplate='%{text:,}', textposition='outside', marker_color=color_a_usar)
    if not df_conteo.empty: fig.update_layout(yaxis_range=[0, df_conteo['Frecuencia'].max() * 1.15])

    return fig, dff.to_json(date_format='iso', orient='split')


def get_detalle_causas_otros_table(df_json, causa):
    """
    Genera una tabla HTML con el detalle de las incidencias para una causa específica.
    """
    df = pd.read_json(df_json, orient='split')
    df['fechahora'] = pd.to_datetime(df['fechahora'])

    # Normalizar observaciones en el dataframe cargado
    df['Observacion_norm'] = normalizar_columna(df['Observación'])
    
    # Filtrar el dataframe según la causa (palabra clave)
    if causa == 'Vacias':
        vacias_mask = df['Observacion_norm'].isnull() | df['Observacion_norm'].str.strip().isin(['', 'nan'])
        df_tabla_filtrada = df[vacias_mask]
    else:
        df_tabla_filtrada = df[df['Observacion_norm'].str.contains(causa, na=False)]

    # Formatear y seleccionar columnas
    dff_table = df_tabla_filtrada.copy()
    dff_table['fechahora'] = dff_table['fechahora'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Aplicar formato a la columna Línea usando utils
    dff_table = crear_columna_linea_con_logo(
        dff_table, 'Línea', ruta_logo_metrobus, mapa_colores, color_predeterminado
    )
    
    # Seleccionar y renombrar columnas para la tabla final
    dff_table_final = dff_table[['fechahora', 'Línea_Logo', 'Indicativo', 'Causa', 'Observación']]
    dff_table_final = dff_table_final.rename(columns={'Línea_Logo': 'Línea', 'fechahora': 'Fecha'})

    if dff_table_final.empty:
        return f"<p>No hay detalles para mostrar para la causa: <b>{causa}</b></p>"

    tabla_html = dff_table_final.to_html(classes=['table', 'table-striped', 'table-hover'], index=False, escape=False)
    
    return f"<h3>Detalle de Incidencias para: {causa}</h3>" + tabla_html
