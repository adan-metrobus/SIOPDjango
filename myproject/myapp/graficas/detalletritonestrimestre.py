
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from . import siopcalidad, config

# --- CONSTANTES ---
COLUMNAS_A = [
    'fechahora', 'Latitud', 'Longitud', 'Estación', 'Hora de Cierre',
    'horacierrecorrecta', 'Causa', 'Tipo', 'Subtipo', 'Seguimiento'
]
COLUMNAS_B = [
    'Estatus', 'Observación', 'Cantidad de Personas Afectadas',
    'Estación Inicial', 'Estación Final'
]

# --- CARGA Y PREPARACIÓN DE DATOS ---
def _preparar_datos():
    df = siopcalidad.obtener_datos_procesados()
    df['fechahora'] = pd.to_datetime(df['fechahora']).dt.tz_localize(None)
    df['year'] = df['fechahora'].dt.year
    df['month'] = df['fechahora'].dt.month
    df['quarter'] = df['fechahora'].dt.quarter
    return df

df = _preparar_datos()

# --- LÓGICA DE FILTRADO Y GRÁFICAS ---

def generar_histograma_calificacion(year=None, month=None, quarter=None, selected_linea=None):
    """
    Genera el histograma principal de calificaciones por indicativo.
    """
    filtered_df = df.copy()
    if year:
        filtered_df = filtered_df[filtered_df['year'] == year]
    if month:
        filtered_df = filtered_df[filtered_df['month'] == month]
    elif quarter:
        filtered_df = filtered_df[filtered_df['quarter'] == quarter]
    if selected_linea:
        filtered_df = filtered_df[filtered_df['Línea'] == selected_linea]

    calificacion_por_indicativo = filtered_df.groupby('Indicativo')['calificacion'].mean().reset_index()
    top_20_indicativos = calificacion_por_indicativo.sort_values(by='calificacion', ascending=True).head(20)

    color_a_usar = config.color_predeterminado
    if selected_linea and str(selected_linea) in config.mapa_colores:
        color_a_usar = config.mapa_colores[str(selected_linea)]

    fig = px.bar(top_20_indicativos, x='Indicativo', y='calificacion',
                 title='Top 20 Indicativos con Calificación Promedio más Baja', text='calificacion')
    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside', marker_color=color_a_usar)
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', xaxis_tickangle=-45,
                      yaxis_title="Calificación Promedio", yaxis_range=[6, 10.5])
    return fig

def generar_grafica_distribucion_penalizaciones(year, month, quarter, selected_linea, indicativo):
    """
    Genera la gráfica de pie con la distribución de penalizaciones.
    """
    if not indicativo:
        return go.Figure().update_layout(title_text='Selecciona un indicativo para ver los detalles')

    df_detalle = df.copy()
    if year:
        df_detalle = df_detalle[df_detalle['year'] == year]
    if month:
        df_detalle = df_detalle[df_detalle['month'] == month]
    elif quarter:
        df_detalle = df_detalle[df_detalle['quarter'] == quarter]
    if selected_linea:
        df_detalle = df_detalle[df_detalle['Línea'] == selected_linea]
    
    df_detalle = df_detalle[df_detalle['Indicativo'] == indicativo]

    penalties_expanded = df_detalle['campos_penalizados'].str.split(', ').explode().dropna()
    counts = penalties_expanded.value_counts().reset_index()
    counts.columns = ['Campo Penalizado', 'count']
    
    pie_fig = px.pie(counts, names='Campo Penalizado', values='count',
                     title=f'Distribución de Penalizaciones para {indicativo}', hole=.3)
    pie_fig.update_traces(textposition='inside', textinfo='percent+label', sort=False)
    return pie_fig

def obtener_tabla_detalle_incidencias(year, month, quarter, selected_linea, indicativo, campo_penalizado=None):
    """
    Prepara y filtra los datos para la tabla de detalle.
    Devuelve un DataFrame de pandas.
    """
    if not indicativo:
        return pd.DataFrame(), "Selecciona un indicativo"

    df_detalle = df.copy()
    if year:
        df_detalle = df_detalle[df_detalle['year'] == year]
    if month:
        df_detalle = df_detalle[df_detalle['month'] == month]
    elif quarter:
        df_detalle = df_detalle[df_detalle['quarter'] == quarter]
    if selected_linea:
        df_detalle = df_detalle[df_detalle['Línea'] == selected_linea]
        
    df_detalle = df_detalle[df_detalle['Indicativo'] == indicativo]
    
    titulo_tabla = f'Detalle de Incidencias para: {indicativo}'

    if campo_penalizado:
        titulo_tabla = f"Detalle para: {indicativo} (Filtro: {campo_penalizado})"
        if campo_penalizado == 'Sin Penalización':
            df_detalle = df_detalle[df_detalle['campos_penalizados'] == 'Sin Penalización']
        else:
            df_detalle = df_detalle[df_detalle['campos_penalizados'].str.contains(f'\\b{campo_penalizado}\\b', regex=True, na=False)]

    tabla_df = df_detalle.copy()
    tabla_df['Fecha'] = tabla_df['fechahora'].dt.date
    tabla_df['Hora'] = tabla_df['fechahora'].dt.strftime('%H:%M:%S')

    columnas_base = ['Folio de Incidencia', 'Indicativo', 'Num.Empleado', 'Nombre Del Supervisor', 'Línea']
    columnas_calif = ['calificacion', 'cantidad_penalizaciones', 'campos_penalizados']
    columnas_deseadas = columnas_base + COLUMNAS_A + COLUMNAS_B + columnas_calif

    if 'fechahora' in columnas_deseadas:
        fechahora_index = columnas_deseadas.index('fechahora')
        columnas_deseadas[fechahora_index:fechahora_index+1] = ['Fecha', 'Hora']

    columnas_existentes = [col for col in columnas_deseadas if col in tabla_df.columns]
    df_detalle_final = tabla_df[columnas_existentes]
    
    return df_detalle_final, titulo_tabla

def get_filter_options():
    """
    Devuelve las opciones para los dropdowns de los filtros.
    """
    years = sorted(df['year'].unique(), reverse=True)
    meses = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
    lineas = sorted(df['Línea'].unique())
    quarters = list(range(1, 5))
    return years, meses, lineas, quarters
