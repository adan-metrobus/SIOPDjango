
import pandas as pd
import plotly.express as px
import json
from plotly.utils import PlotlyJSONEncoder
from . import siopcalidad
from datetime import datetime
from .config import columnas_deseadas, mapa_colores, ruta_logo_metrobus, color_predeterminado
from .utils import crear_columna_linea_con_logo

def generate_status_abierto_graph():
    """
    Genera la gráfica de antigüedad de folios con estatus "Abierto".
    """
    df = siopcalidad.obtener_datos_procesados()
    df['fechahora'] = pd.to_datetime(df['fechahora']).dt.tz_localize(None)
    df['Estatus'] = df['Estatus'].str.strip()

    df_abiertos = df[df['Estatus'] == 'ABIERTO'].copy()
    df_abiertos['Línea'] = df_abiertos['Línea'].astype(str)

    hoy = pd.to_datetime(datetime.now().date())
    df_abiertos.loc[:, 'antiguedad'] = (hoy - pd.to_datetime(df_abiertos['Fecha'])).dt.days

    bins = [0, 30, 60, 90, float('inf')]
    labels = ['1-30 días', '31-60 días', '61-90 días', '91+ días']
    df_abiertos['rango_antiguedad'] = pd.cut(df_abiertos['antiguedad'], bins=bins, labels=labels, right=False)

    antiguedad_por_linea = df_abiertos.groupby(['rango_antiguedad', 'Línea'], observed=False).size().reset_index(name='conteo')
    antiguedad_por_linea['rango_antiguedad'] = pd.Categorical(antiguedad_por_linea['rango_antiguedad'], categories=labels, ordered=True)
    antiguedad_por_linea = antiguedad_por_linea.sort_values('rango_antiguedad')

    fig = px.bar(antiguedad_por_linea, 
                 x='rango_antiguedad', y='conteo', color='Línea', barmode='stack',
                 title='Antigüedad de Folios con Estatus "Abierto" por Línea',
                 labels={'rango_antiguedad': 'Rango de Antigüedad', 'conteo': 'Cantidad de Folios'},
                 text='conteo',
                 color_discrete_map=mapa_colores)

    totales_por_rango = antiguedad_por_linea.groupby('rango_antiguedad', observed=False)['conteo'].sum()
    for rango, total in totales_por_rango.items():
        if total > 0:
            fig.add_annotation(x=rango, y=total, text=f"<b>{total}</b>", showarrow=False, font=dict(size=12, color="black"), yshift=5)

    fig.update_traces(texttemplate='%{text:,}', textposition='inside')
    fig.update_layout(xaxis_title="Rango de Antigüedad (días)", yaxis_title="Cantidad de Folios",
                      title_x=0.5, legend_title="Línea", margin=dict(t=100))

    graph_json = json.dumps(fig, cls=PlotlyJSONEncoder)
    df_abiertos_json = df_abiertos.to_json(orient='split')

    return graph_json, df_abiertos_json

def get_detalle_abiertos_table(df_abiertos_json, rango_seleccionado):
    df_abiertos = pd.read_json(df_abiertos_json, orient='split')
    df_filtrado = df_abiertos[df_abiertos['rango_antiguedad'] == rango_seleccionado]
    
    columnas_existentes = [col for col in columnas_deseadas if col in df_filtrado.columns]
    
    if 'Línea' not in columnas_existentes:
        df_display = df_filtrado[columnas_existentes]
    else:
        df_con_logo = crear_columna_linea_con_logo(df_filtrado, 'Línea', ruta_logo_metrobus, mapa_colores, color_predeterminado)
        df_con_logo = df_con_logo.drop(columns=['Línea'])
        df_con_logo = df_con_logo.rename(columns={'Línea_Logo': 'Línea'})
        
        final_cols = [col for col in columnas_deseadas if col in df_con_logo.columns]
        df_display = df_con_logo[final_cols]

    return df_display.to_html(classes=['table', 'table-striped', 'table-hover'], index=False, escape=False)
