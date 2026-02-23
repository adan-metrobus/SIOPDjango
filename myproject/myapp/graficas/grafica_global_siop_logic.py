
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from . import siopcalidad
import json
from plotly.utils import PlotlyJSONEncoder
from . import config
from .utils import crear_columna_linea_con_logo
from datetime import datetime
import unicodedata

# --- Lógica para "Causas Otros" ---
PALABRAS_CLAVE = [
    'moto', 'potro', 'bici', 'percance', 'colisi','choqu', 'atropell',
    'frenado', 'emergenc', 'impact', 'vehicul', 'medic'
]

def _normalizar_columna(series):
    if series is None: return pd.Series([None] * len(series), index=series.index)
    series_str = series.astype(str).str.lower()
    return series_str.apply(
        lambda x: ''.join(c for c in unicodedata.normalize('NFD', x) if unicodedata.category(c) != 'Mn') if pd.notnull(x) else x
    )

def _generate_causas_otros_graph(df_filtrado_fechas, selected_lineas):
    df = df_filtrado_fechas.copy()
    df['Causa_norm'] = df['Causa'].str.lower().str.strip()
    causas_a_filtrar = [
        "otro (detallar en el campo observaciones)", 
        "", 
        "sin datos (detallar en el campo observaciones)"
    ]
    df_causas_otros = df[df['Causa_norm'].isin(causas_a_filtrar) | df['Causa'].isnull()].copy()
    df_causas_otros['Observacion_norm'] = _normalizar_columna(df_causas_otros['Observación'])

    if selected_lineas:
        df_causas_otros = df_causas_otros[df_causas_otros['Línea'].isin(selected_lineas)]

    observaciones_norm = df_causas_otros['Observacion_norm']
    vacias_mask = observaciones_norm.isnull() | observaciones_norm.str.strip().isin(['', 'nan'])
    conteo_palabras = {'Vacias': vacias_mask.sum()}
    
    observaciones_no_vacias = observaciones_norm[~vacias_mask]
    for palabra in PALABRAS_CLAVE:
        conteo_palabras[palabra] = observaciones_no_vacias.str.contains(palabra, na=False).sum()

    df_conteo = pd.DataFrame(list(conteo_palabras.items()), columns=['Palabra Clave', 'Frecuencia'])
    df_conteo = df_conteo.sort_values(by='Frecuencia', ascending=False)
    
    fig = px.bar(df_conteo, x='Palabra Clave', y='Frecuencia', title='Frecuencia de Palabras Clave en Observaciones (Causa="Otro","Sin Datos",Vacias)', text='Frecuencia')

    color_a_usar = config.color_predeterminado
    if selected_lineas and len(selected_lineas) == 1 and selected_lineas[0] in config.mapa_colores:
        color_a_usar = config.mapa_colores[selected_lineas[0]]

    fig.update_traces(texttemplate='%{text:,}', textposition='outside', marker_color=color_a_usar)
    if not df_conteo.empty: fig.update_layout(yaxis_range=[0, df_conteo['Frecuencia'].max() * 1.15])

    graph_json = json.dumps(fig, cls=PlotlyJSONEncoder)
    df_json = df_causas_otros.to_json(date_format='iso', orient='split')

    return graph_json, df_json

def get_detalle_causas_otros_table(df_json, causa):
    df = pd.read_json(df_json, orient='split')
    df['fechahora'] = pd.to_datetime(df['fechahora'])
    df['Observacion_norm'] = _normalizar_columna(df['Observación'])
    
    if causa == 'Vacias':
        df_filtrado = df[df['Observacion_norm'].isnull() | df['Observacion_norm'].str.strip().isin(['', 'nan жела'])]
    else:
        df_filtrado = df[df['Observacion_norm'].str.contains(causa, na=False)]

    df_con_logo = crear_columna_linea_con_logo(df_filtrado.copy(), 'Línea', config.ruta_logo_metrobus, config.mapa_colores, config.color_predeterminado)
    df_con_logo = df_con_logo.drop(columns=['Línea'])
    df_con_logo = df_con_logo.rename(columns={'Línea_Logo': 'Línea'})
    
    columnas_finales = ['fechahora', 'Línea', 'Indicativo', 'Causa', 'Observación']
    df_display = df_con_logo[[col for col in columnas_finales if col in df_con_logo.columns]]

    return df_display.to_html(classes=['table', 'table-striped', 'table-hover'], index=False, escape=False)

# --- Lógica para "Estatus Abierto" ---
def _generate_status_abierto_graph():
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

    fig = px.bar(antiguedad_por_linea, x='rango_antiguedad', y='conteo', color='Línea', barmode='stack', title='Antigüedad de Folios con Estatus "Abierto" por Línea', labels={'rango_antiguedad': 'Rango de Antigüedad', 'conteo': 'Cantidad de Folios'}, text='conteo', color_discrete_map=config.mapa_colores)

    totales_por_rango = antiguedad_por_linea.groupby('rango_antiguedad', observed=False)['conteo'].sum()
    for rango, total in totales_por_rango.items():
        if total > 0:
            fig.add_annotation(x=rango, y=total, text=f"<b>{total}</b>", showarrow=False, font=dict(size=12, color="black"), yshift=5)

    fig.update_traces(texttemplate='%{text:,}', textposition='inside')
    fig.update_layout(xaxis_title="Rango de Antigüedad (días)", yaxis_title="Cantidad de Folios", title_x=0.5, legend_title="Línea", margin=dict(t=100))

    graph_json = json.dumps(fig, cls=PlotlyJSONEncoder)
    df_abiertos_json = df_abiertos.to_json(orient='split')
    return graph_json, df_abiertos_json

def get_detalle_abiertos_table(df_abiertos_json, rango_seleccionado):
    df_abiertos = pd.read_json(df_abiertos_json, orient='split')
    df_filtrado = df_abiertos[df_abiertos['rango_antiguedad'] == rango_seleccionado]
    df_con_logo = crear_columna_linea_con_logo(df_filtrado.copy(), 'Línea', config.ruta_logo_metrobus, config.mapa_colores, config.color_predeterminado)
    df_con_logo = df_con_logo.drop(columns=['Línea'])
    df_con_logo = df_con_logo.rename(columns={'Línea_Logo': 'Línea'})
    final_cols = [col for col in config.columnas_deseadas if col in df_con_logo.columns]
    df_display = df_con_logo[final_cols]
    return df_display.to_html(classes=['table', 'table-striped', 'table-hover'], index=False, escape=False)

# --- Lógica Global y de Campos Recurrentes ---

def generate_global_siop_graphs(start_date, end_date, indicativo=None, selected_lineas=None):
    df = siopcalidad.obtener_datos_procesados()
    df['fechahora'] = pd.to_datetime(df['fechahora']).dt.tz_localize(None)
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    mask_fechas = (df['fechahora'] >= start_date) & (df['fechahora'] <= end_date)
    df_filtrado_fechas = df[mask_fechas].copy()

    df_filtrado_glob = df_filtrado_fechas.copy()
    if selected_lineas:
        df_filtrado_glob = df_filtrado_glob[df_filtrado_glob['Línea'].isin(selected_lineas)]

    # Gráficas globales (Distribución, Promedio, Supervisores)
    bins = [0, 5, 6, 7, 8, 9, 10.1]
    labels = ['0-5', '5-6', '6-7', '7-8', '8-9', '9-10']
    df_filtrado_glob['rango_calificacion'] = pd.cut(df_filtrado_glob['calificacion'], bins=bins, labels=labels, right=False)
    conteo_por_rango = df_filtrado_glob.groupby('rango_calificacion', observed=True).size().reset_index(name='conteo')
    fig_barras = px.bar(conteo_por_rango, x='rango_calificacion', y='conteo', title='Distribución de Calificaciones', text='conteo', color='conteo', color_continuous_scale=px.colors.sequential.Teal)
    fig_barras.update_layout(coloraxis_showscale=False, title_x=0.5, yaxis_title='Cantidad de Calificaciones')
    fig_barras.update_traces(texttemplate='%{y:,}', textposition='outside')

    df_filtrado_glob['año'] = df_filtrado_glob['fechahora'].dt.year
    df_filtrado_glob['mes'] = df_filtrado_glob['fechahora'].dt.month
    promedio_mensual = df_filtrado_glob.groupby(['año', 'mes'])['calificacion'].mean().reset_index()
    fig_lineas = px.line(promedio_mensual, x='mes', y='calificacion', color='año', title='Promedio Mensual de Calificación', markers=True)
    fig_lineas.update_layout(xaxis=dict(tickmode='array', tickvals=list(range(1, 13)), ticktext=['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']), yaxis=dict(range=[max(7.5, promedio_mensual['calificacion'].min() - 0.5) if not promedio_mensual.empty else 7.5, min(10, promedio_mensual['calificacion'].max() + 0.5) if not promedio_mensual.empty else 10]), title_x=0.5)

    df_tabla = df_filtrado_glob.groupby(['Indicativo', 'Nombre Del Supervisor'])['calificacion'].mean().reset_index()
    df_tabla.rename(columns={'calificacion': 'Promedio Calificación'}, inplace=True)
    df_tabla['Promedio Calificación'] = df_tabla['Promedio Calificación'].round(2)
    df_tabla.sort_values('Promedio Calificación', ascending=True, inplace=True)
    df_tabla.columns = [col.replace(' ', '_') for col in df_tabla.columns]

    tabla_detalle_html, titulo_detalle = None, None
    if indicativo:
        df_detalle = df_filtrado_glob[df_filtrado_glob['Indicativo'] == indicativo].copy()
        df_detalle['Fecha'] = df_detalle['fechahora'].dt.date
        df_detalle['Hora'] = df_detalle['fechahora'].dt.strftime('%H:%M:%S')
        columnas_deseadas = ['Folio de Incidencia', 'Fecha', 'Hora', 'Indicativo', 'Nombre Del Supervisor', 'calificacion', 'campos_penalizados']
        df_detalle_final = df_detalle[[col for col in columnas_deseadas if col in df_detalle.columns]]
        tabla_detalle_html = df_detalle_final.to_html(classes='table table-striped table-sm', index=False, border=0)
        titulo_detalle = f'Detalle de Incidencias para: {indicativo}'

    # Gráfica de Campos Penalizados
    df_filtrado_glob['campos_penalizados'] = df_filtrado_glob['campos_penalizados'].fillna('').replace('Sin penalizaciones', '')
    campos_lista = df_filtrado_glob['campos_penalizados'].astype(str).str.split(',').explode().str.strip()
    conteo_campos = campos_lista[campos_lista != ''].value_counts().reset_index()
    conteo_campos.columns = ['Campo Penalizado', 'Frecuencia']
    fig_campos_recurrentes = px.bar(conteo_campos, x='Campo Penalizado', y='Frecuencia', title='Campos Penalizados Individualmente SIOP', text='Frecuencia')
    fig_campos_recurrentes.update_traces(marker_color=config.color_predeterminado)
    max_y_value = conteo_campos['Frecuencia'].max() * 1.15 if not conteo_campos.empty else 10
    fig_campos_recurrentes.update_layout(xaxis_tickangle=-45, yaxis_title="Número de Penalizaciones", xaxis_title="Campo Penalizado", yaxis_range=[0, max_y_value])

    # Gráficas independientes
    fig_status_abierto_json, df_abiertos_json = _generate_status_abierto_graph()
    fig_causas_otros_json, df_causas_otros_json = _generate_causas_otros_graph(df_filtrado_fechas, selected_lineas)

    # Conversión a JSON
    return {
        "fig_barras_json": json.dumps(fig_barras, cls=PlotlyJSONEncoder),
        "fig_lineas_json": json.dumps(fig_lineas, cls=PlotlyJSONEncoder),
        "fig_campos_recurrentes_json": json.dumps(fig_campos_recurrentes, cls=PlotlyJSONEncoder),
        "fig_status_abierto_json": fig_status_abierto_json,
        "fig_causas_otros_json": fig_causas_otros_json,
        "supervisores_data": df_tabla.to_dict('records'),
        "tabla_detalle_html": tabla_detalle_html,
        "titulo_detalle": titulo_detalle,
        "df_filtrado_json": df_filtrado_glob.to_json(orient='split'),
        "df_abiertos_json": df_abiertos_json,
        "df_causas_otros_json": df_causas_otros_json,
    }

def get_detalle_campos_recurrentes_table(df_json, campo_penalizado):
    df = pd.read_json(df_json, orient='split')
    df_filtrado = df[df['campos_penalizados'].str.contains(campo_penalizado, na=False)]
    df_con_logo = crear_columna_linea_con_logo(df_filtrado.copy(), 'Línea', config.ruta_logo_metrobus, config.mapa_colores, config.color_predeterminado)
    df_con_logo = df_con_logo.drop(columns=['Línea'])
    df_con_logo = df_con_logo.rename(columns={'Línea_Logo': 'Línea'})
    final_cols = [col for col in config.columnas_deseadas if col in df_con_logo.columns]
    df_display = df_con_logo[final_cols]
    return df_display.to_html(classes=['table', 'table-striped', 'table-hover'], index=False, escape=False)

def get_date_range():
    df = siopcalidad.obtener_datos_procesados()
    df['fechahora'] = pd.to_datetime(df['fechahora']).dt.tz_localize(None)
    return df['fechahora'].min().date(), df['fechahora'].max().date()

def get_lineas():
    df = siopcalidad.obtener_datos_procesados()
    lineas = df['Línea'].dropna().astype(str).unique()
    lineas.sort()
    return list(lineas)
