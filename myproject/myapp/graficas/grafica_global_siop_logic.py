
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from . import siopcalidad
import json
from plotly.utils import PlotlyJSONEncoder

def generate_global_siop_graphs(start_date, end_date, indicativo=None):
    """
    Genera las gráficas y tablas para el reporte global SIOP.
    """
    df = siopcalidad.obtener_datos_procesados()
    df['fechahora'] = pd.to_datetime(df['fechahora']).dt.tz_localize(None)

    # Convertir start_date y end_date a datetime
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Filtrar el DF principal según el rango de fechas
    mask_fechas = (df['fechahora'] >= start_date) & (df['fechahora'] <= end_date)
    df_filtrado_fecha = df[mask_fechas].copy()

    # --- Gráfica 1: Distribución de Calificaciones (Barras) ---
    bins = [0, 5, 6, 7, 8, 9, 10.1]
    labels = ['0-5', '5-6', '6-7', '7-8', '8-9', '9-10']
    df_filtrado_fecha['rango_calificacion'] = pd.cut(df_filtrado_fecha['calificacion'], bins=bins, labels=labels, right=False)
    conteo_por_rango = df_filtrado_fecha.groupby('rango_calificacion', observed=True).size().reset_index(name='conteo')
    
    fig_barras = px.bar(conteo_por_rango, 
                x='rango_calificacion', 
                y='conteo', 
                title='Distribución de Calificaciones', 
                text='conteo', 
                color='conteo', 
                color_continuous_scale=px.colors.sequential.Teal)
    fig_barras.update_layout(coloraxis_showscale=False, title_x=0.5, yaxis_title='Cantidad de Calificaciones')
    fig_barras.update_traces(texttemplate='%{y:,}', textposition='outside')

    # --- Gráfica 2: Promedio Mensual (Líneas) ---
    df_filtrado_fecha['año'] = df_filtrado_fecha['fechahora'].dt.year
    df_filtrado_fecha['mes'] = df_filtrado_fecha['fechahora'].dt.month
    promedio_mensual = df_filtrado_fecha.groupby(['año', 'mes'])['calificacion'].mean().reset_index()
    
    fig_lineas = px.line(promedio_mensual, x='mes', y='calificacion', color='año', title='Promedio Mensual de Calificación', markers=True)
    fig_lineas.update_layout(
        xaxis=dict(tickmode='array', tickvals=list(range(1, 13)), ticktext=['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']),
        yaxis=dict(range=[max(7.5, promedio_mensual['calificacion'].min() - 0.5), min(10, promedio_mensual['calificacion'].max() + 0.5)]) if not promedio_mensual.empty else dict(range=[7.5, 10]),
        title_x=0.5
    )
    
    # --- Tabla de Supervisores ---
    df_tabla = df_filtrado_fecha.groupby(['Indicativo', 'Nombre Del Supervisor'])['calificacion'].mean().reset_index()
    df_tabla.rename(columns={'calificacion': 'Promedio Calificación'}, inplace=True)
    df_tabla['Promedio Calificación'] = df_tabla['Promedio Calificación'].round(2)
    df_tabla.sort_values('Promedio Calificación', ascending=True, inplace=True)
    df_tabla.columns = [col.replace(' ', '_') for col in df_tabla.columns]

    # --- Tabla de Detalle (si se seleccionó un indicativo) ---
    tabla_detalle_html = None
    titulo_detalle = None
    if indicativo:
        df_detalle = df_filtrado_fecha[df_filtrado_fecha['Indicativo'] == indicativo].copy()
        df_detalle['Fecha'] = df_detalle['fechahora'].dt.date
        df_detalle['Hora'] = df_detalle['fechahora'].dt.strftime('%H:%M:%S')
        
        columnas_deseadas = ['Folio de Incidencia', 'Fecha', 'Hora', 'Indicativo', 'Nombre Del Supervisor', 'calificacion', 'campos_penalizados']
        df_detalle_final = df_detalle[[col for col in columnas_deseadas if col in df_detalle.columns]]
        
        tabla_detalle_html = df_detalle_final.to_html(classes='table table-striped table-sm', index=False, border=0)
        titulo_detalle = f'Detalle de Incidencias para: {indicativo}'

    # Convertir a JSON
    fig_barras_json = json.dumps(fig_barras, cls=PlotlyJSONEncoder)
    fig_lineas_json = json.dumps(fig_lineas, cls=PlotlyJSONEncoder)
    
    return {
        "fig_barras_json": fig_barras_json,
        "fig_lineas_json": fig_lineas_json,
        "supervisores_data": df_tabla.to_dict('records'),
        "tabla_detalle_html": tabla_detalle_html,
        "titulo_detalle": titulo_detalle
    }

def get_date_range():
    """
    Obtiene el rango de fechas mínimo y máximo de los datos.
    """
    df = siopcalidad.obtener_datos_procesados()
    df['fechahora'] = pd.to_datetime(df['fechahora']).dt.tz_localize(None)
    min_date = df['fechahora'].min().date()
    max_date = df['fechahora'].max().date()
    return min_date, max_date

def get_lineas():
    """
    Obtiene la lista de todas las líneas únicas.
    """
    df = siopcalidad.obtener_datos_procesados()
    lineas = df['Línea'].dropna().astype(str).unique()
    lineas.sort()
    return list(lineas)