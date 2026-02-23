
import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.express as px
import pandas as pd
import siopcalidad

# 1. Cargar y preparar los datos
df = siopcalidad.obtener_datos_procesados()
# Asegurarse de que la columna de fecha sea del tipo datetime
df['fechahora'] = pd.to_datetime(df['fechahora']).dt.tz_localize(None)

# Obtener el rango de fechas para el selector
min_date = df['fechahora'].min().date()
max_date = df['fechahora'].max().date()

# Definir el mapa de colores para las líneas
mapa_colores = {
    '1': '#a4343a',
    '2': '#87189d',
    '3': '#7a9a01',
    '4': '#fe5000',
    '5': '#001e60',
    '6': '#e10098',
    '7': '#046a38'
}

# 2. Inicializar la aplicación Dash
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
server = app.server

# 3. Definir el layout de la aplicación
app.layout = html.Div([
    html.H1('Promedio de Calificación Linea (SIOP)', style={'textAlign': 'center','fontSize': '2.5rem'}),

    # Componente para seleccionar el rango de fechas
    html.Div([
        html.Label('Selecciona un Rango de Fechas:', style={'fontWeight': 'bold'}),
        dcc.DatePickerRange(
            id='selector-fecha',
            min_date_allowed=min_date,
            max_date_allowed=max_date,
            start_date=min_date,
            end_date=max_date,
            display_format='DD/MM/YYYY',
        )
    ], style={'width': '100%', 'textAlign': 'center', 'padding': '20px'}),

    # Gráfica principal (ahora interactiva)
    dcc.Graph(id='grafica-promedio'),

    # Contenedor para la tabla de detalle (aparece al hacer clic)
    html.Div(id='contenedor-tabla-detalle', children=[
        dash_table.DataTable(
            id='tabla-detalle-supervisor',
            style_cell={'textAlign': 'left'},
            style_header={'fontWeight': 'bold'},
            sort_action="native",
            page_size=20,
        )
    ], style={'padding': '20px'})
])

# 4. Callback unificado para actualizar gráfica y tabla
@app.callback(
    Output('grafica-promedio', 'figure'),
    Output('tabla-detalle-supervisor', 'data'),
    Output('tabla-detalle-supervisor', 'columns'),
    Input('selector-fecha', 'start_date'),
    Input('selector-fecha', 'end_date'),
    Input('grafica-promedio', 'clickData')
)
def actualizar_grafica_y_tabla(start_date, end_date, clickData):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'No-triggered'

    # Filtrar el DataFrame según el rango de fechas (necesario para ambas lógicas)
    mask = (df['fechahora'] >= pd.to_datetime(start_date)) & (df['fechahora'] <= pd.to_datetime(end_date))
    df_filtrado = df.loc[mask]

    # --- LÓGICA PARA LA GRÁFICA PRINCIPAL ---
    if df_filtrado.empty:
        fig = {
            "layout": {
                "title": "No hay datos para el rango de fechas seleccionado",
                "xaxis": {"visible": False}, "yaxis": {"visible": False}
            }
        }
        # Si no hay datos, no mostrar nada en la tabla
        return fig, [], []
    
    promedio_por_linea = df_filtrado.groupby('Línea')['calificacion'].mean().round(2).reset_index()
    try:
        lineas_ordenadas = sorted(promedio_por_linea['Línea'].unique(), key=int)
    except (ValueError, TypeError):
        lineas_ordenadas = sorted(promedio_por_linea['Línea'].unique())

    fig = px.bar(
        promedio_por_linea, x='Línea', y='calificacion', title='Promedio de Calificación por Línea',
        text='calificacion', labels={'calificacion': 'Promedio de Calificación'},
        color='Línea', color_discrete_map=mapa_colores,
        category_orders={'Línea': lineas_ordenadas}
    )
    fig.update_traces(textposition='inside')
    fig.update_layout(yaxis_title='Promedio', xaxis_title='Línea')

    # --- LÓGICA PARA LA TABLA DE DETALLE ---
    if triggered_id == 'grafica-promedio' and clickData:
        # Si se hizo clic en una barra, generar datos para la tabla
        clicked_linea = str(clickData['points'][0]['x'])
        
        df_linea_filtrada = df_filtrado[df_filtrado['Línea'] == clicked_linea]
        
        df_detalle = df_linea_filtrada.groupby(['Indicativo', 'Nombre Del Supervisor'])['calificacion'].mean().round(2).reset_index()
        df_detalle.rename(columns={'calificacion': 'Promedio Calificacion'}, inplace=True)
        
        # Ordenar la tabla por el promedio de calificación de forma ascendente
        df_detalle.sort_values('Promedio Calificacion', ascending=True, inplace=True)

        columns = [{"name": i, "id": i} for i in df_detalle.columns]
        data = df_detalle.to_dict('records')
        
        return fig, data, columns

    # Si no hubo clic (solo cambio de fecha), mostrar la gráfica y una tabla vacía
    return fig, [], []

# 5. Ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True)
