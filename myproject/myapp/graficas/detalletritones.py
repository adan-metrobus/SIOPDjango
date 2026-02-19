import dash
from dash import dcc, html, dash_table, no_update
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import siopcalidad

COLUMNAS_A = [
    'fechahora',
    'Latitud',
    'Longitud',
    'Estación',
    'Hora de Cierre',
    'horacierrecorrecta',
    'Causa',
    'Tipo',
    'Subtipo',
    'Seguimiento'
]

COLUMNAS_B = [
    'Estatus',
    'Observación',
    'Cantidad de Personas Afectadas',
    'Estación Inicial',
    'Estación Final'
]

# 1. Cargar y preparar los datos iniciales
df = siopcalidad.obtener_datos_procesados()
df['fechahora'] = pd.to_datetime(df['fechahora']).dt.tz_localize(None)

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

app.layout = html.Div([
    html.H3("Análisis de Calificaciones por Indicativo"),

    html.Div([
        html.Label("Filtro por Fecha"),
        dcc.DatePickerRange(
            id='date-picker-range',
            min_date_allowed=min_date,
            max_date_allowed=max_date,
            initial_visible_month=min_date,
            start_date=min_date,
            end_date=max_date
        ),
    ], style={'width': '49%', 'display': 'inline-block'}),

    html.Div([
        html.Label("Filtro por Línea"),
        dcc.Dropdown(
            id='linea-dropdown',
            options=[{'label': i, 'value': i} for i in sorted(df['Línea'].unique())],
            placeholder='Selecciona una Línea'
        ),
    ], style={'width': '49%', 'float': 'right', 'display': 'inline-block'}),

    dcc.Graph(id='histograma-indicativo-calificacion'),

    # Contenedor para la tabla de detalle
    html.Div(id='contenedor-tabla-detalle', style={'padding': '20px'})
])

@app.callback(
    [Output('histograma-indicativo-calificacion', 'figure'),
     Output('contenedor-tabla-detalle', 'children')],
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('linea-dropdown', 'value'),
     Input('histograma-indicativo-calificacion', 'clickData')]
)
def update_graph_and_table(start_date, end_date, selected_linea, clickData):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'No-triggered'

    filtered_df = df[
        (df['fechahora'] >= pd.to_datetime(start_date)) &
        (df['fechahora'] <= pd.to_datetime(end_date))
    ]

    if selected_linea:
        filtered_df = filtered_df[filtered_df['Línea'] == selected_linea]

    # --- LÓGICA PARA LA GRÁFICA ---
    calificacion_por_indicativo = filtered_df.groupby('Indicativo')['calificacion'].mean().reset_index()
    top_20_indicativos = calificacion_por_indicativo.sort_values(by='calificacion', ascending=True).head(20)

    fig = px.bar(top_20_indicativos, x='Indicativo', y='calificacion',
                   title='Top 20 Indicativos con Calificación Promedio más Baja',
                   text='calificacion')

    color_a_usar = '#9E1C05'
    if selected_linea and selected_linea in mapa_colores:
        color_a_usar = mapa_colores[selected_linea]

    fig.update_traces(
        texttemplate='%{text:.2f}', 
        textposition='outside', 
        marker_color=color_a_usar
    )

    fig.update_layout(
        uniformtext_minsize=8, 
        uniformtext_mode='hide', 
        xaxis_tickangle=-45, 
        yaxis_title="Calificación Promedio",
        yaxis_range=[6, 10.5]
    )

    # --- LÓGICA PARA LA TABLA DE DETALLE ---
    if triggered_id == 'histograma-indicativo-calificacion' and clickData:
        indicativo_seleccionado = clickData['points'][0]['x']
        
        df_detalle = filtered_df[filtered_df['Indicativo'] == indicativo_seleccionado].copy()
        
        df_detalle['Fecha'] = df_detalle['fechahora'].dt.date
        df_detalle['Hora'] = df_detalle['fechahora'].dt.strftime('%H:%M:%S')

        columnas_base = ['Folio de Incidencia', 'Indicativo', 'Num.Empleado', 'Nombre Del Supervisor', 'Línea']
        columnas_calif = ['calificacion', 'cantidad_penalizaciones', 'campos_penalizados']
        
        columnas_deseadas = columnas_base + COLUMNAS_A + COLUMNAS_B + columnas_calif
        
        if 'fechahora' in columnas_deseadas:
            fechahora_index = columnas_deseadas.index('fechahora')
            columnas_deseadas[fechahora_index:fechahora_index+1] = ['Fecha', 'Hora']

        columnas_existentes = [col for col in columnas_deseadas if col in df_detalle.columns]
        df_detalle_final = df_detalle[columnas_existentes]

        detalle_out = html.Div([
            html.H4(f'Detalle de Incidencias para: {indicativo_seleccionado}', style={'textAlign': 'center'}),
            dash_table.DataTable(
                columns=[{'name': i, 'id': i} for i in df_detalle_final.columns],
                data=df_detalle_final.to_dict('records'),
                page_size=10,
                style_table={'overflowX': 'auto', 'minWidth': '100%'},
                style_header={'backgroundColor': '#f2f2f2', 'fontWeight': 'bold'},
                style_cell={'textAlign': 'left', 'padding': '5px', 'fontSize': '12px'},
                style_cell_conditional=[
                    {
                        'if': {'column_id': 'Observación'},
                        'whiteSpace': 'normal',
                        'height': 'auto',
                        'minWidth': '180px', 'width': '300px', 'maxWidth': '450px',
                    }
                ]
            )
        ])
        
        return no_update, detalle_out

    return fig, []

if __name__ == '__main__':
    app.run(debug=True)
