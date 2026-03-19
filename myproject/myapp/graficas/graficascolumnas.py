import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import siopcalidad
from config import columnas_deseadas

color_predeterminado = '#9E1C05'
mapa_colores = {
    '1': '#a4343a',
    '2': '#87189d',
    '3': '#7a9a01',
    '4': '#fe5000',
    '5': '#001e60',
    '6': '#e10098',
    '7': '#046a38'
}
# Cargar y preparar los datos iniciales
# La función obtener_datos_procesados de siopcalidad ya limpia y prepara los datos.
# No es necesario rellenar o modificar 'campos_penalizados' aquí.
df = siopcalidad.obtener_datos_procesados()
df['fechahora'] = pd.to_datetime(df['fechahora']).dt.tz_localize(None)

min_date = df['fechahora'].min().date()
max_date = df['fechahora'].max().date()

# Inicializar la aplicación Dash
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
server = app.server

app.layout = html.Div([
    html.H3("Análisis de Penalizaciones SIOP"),

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
            multi=True,
            placeholder='Selecciona una o más líneas'
        ),
    ], style={'width': '49%', 'float': 'right', 'display': 'inline-block'}),

    dcc.Graph(id='histograma-cantidad-penalizaciones'),
    dcc.Graph(id='histograma-campos-penalizados'),
    html.Div(id='tabla-detalle-container', children=[
        html.H4('Detalles de la Selección'),
        dash_table.DataTable(
            id='tabla-detalle',
            columns=[{"name": i, "id": i} for i in columnas_deseadas],
            data=[],
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={
                'height': 'auto',
                'minWidth': '100px', 'width': '150px', 'maxWidth': '200px',
                'whiteSpace': 'normal'
            }
        )
    ], style={'display': 'none'}) # Initially hidden
])

@app.callback(
    [Output('histograma-cantidad-penalizaciones', 'figure'),
     Output('histograma-campos-penalizados', 'figure')],
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('linea-dropdown', 'value')]
)
def update_histograms(start_date, end_date, selected_lineas):
    base_df = df[
        (df['fechahora'] >= pd.to_datetime(start_date)) &
        (df['fechahora'] <= pd.to_datetime(end_date))
    ]

    if selected_lineas:
        filtered_df = base_df[base_df['Línea'].isin(selected_lineas)]
    else:
        filtered_df = base_df

    # --- Histograma para cantidad_penalizaciones ---
    if selected_lineas:
        fig_cantidad = px.histogram(filtered_df, x='cantidad_penalizaciones',
                                    title='Histograma de Cantidad de Penalizaciones',
                                    text_auto=True,
                                    color='Línea',
                                    color_discrete_map=mapa_colores,
                                    barmode='stack')
        fig_cantidad.update_traces(texttemplate='%{y:,}', textposition='outside')
    else:
        fig_cantidad = px.histogram(filtered_df, x='cantidad_penalizaciones',
                                    title='Histograma de Cantidad de Penalizaciones',
                                    text_auto=True)
        fig_cantidad.update_traces(texttemplate='%{y:,}', textposition='outside', marker_color=color_predeterminado)

    fig_cantidad.update_layout(bargap=0.2, yaxis_title="Conteo")

    if not filtered_df.empty:
        counts_df = filtered_df.groupby('cantidad_penalizaciones').size().reset_index(name='counts')
        max_y_cantidad = counts_df['counts'].max() * 1.15 if not counts_df.empty else 10
        fig_cantidad.update_layout(yaxis_range=[0, max_y_cantidad])

    # --- Histograma para campos_penalizados (Top 20) ---
    # Se filtra para excluir la categoría 'Sin Penalización' de la gráfica, según lo solicitado.
    df_penalizados = filtered_df[filtered_df['campos_penalizados'] != 'Sin Penalización']
    
    top_20_counts = df_penalizados['campos_penalizados'].value_counts().nlargest(20)
    top_20_campos = top_20_counts.index
    df_top_20 = df_penalizados[df_penalizados['campos_penalizados'].isin(top_20_campos)]
    
    if selected_lineas:
        fig_campos = px.histogram(df_top_20, x='campos_penalizados',
                                  title='Top 20 Campos Penalizados',
                                  text_auto=True,
                                  color='Línea',
                                  color_discrete_map=mapa_colores,
                                  barmode='stack',
                                  category_orders={'campos_penalizados': list(top_20_campos)})
        fig_campos.update_traces(texttemplate='%{y:,}', textposition='outside')
    else:
        fig_campos = px.histogram(df_top_20, x='campos_penalizados',
                                  title='Top 20 Campos Penalizados',
                                  text_auto=True,
                                  category_orders={'campos_penalizados': list(top_20_campos)})
        fig_campos.update_traces(texttemplate='%{y:,}', textposition='outside', marker_color=color_predeterminado)
                              
    fig_campos.update_layout(bargap=0.2, xaxis_title="Combinación de Campos Penalizados", yaxis_title="Conteo", xaxis_tickangle=-45)

    if not top_20_counts.empty:
        max_y_campos = top_20_counts.max() * 1.15
        fig_campos.update_layout(yaxis_range=[0, max_y_campos])

    return fig_cantidad, fig_campos

@app.callback(
    [Output('tabla-detalle-container', 'style'),
     Output('tabla-detalle', 'data')],
    [Input('histograma-campos-penalizados', 'clickData')],
    [State('date-picker-range', 'start_date'),
     State('date-picker-range', 'end_date'),
     State('linea-dropdown', 'value')]
)
def display_click_data(clickData, start_date, end_date, selected_lineas):
    if clickData is None:
        return {'display': 'none'}, []

    base_df = df[
        (df['fechahora'] >= pd.to_datetime(start_date)) &
        (df['fechahora'] <= pd.to_datetime(end_date))
    ]
    if selected_lineas:
        filtered_df = base_df[base_df['Línea'].isin(selected_lineas)]
    else:
        filtered_df = base_df

    selected_campo = clickData['points'][0]['x']
    table_df = filtered_df[filtered_df['campos_penalizados'] == selected_campo]
    table_data = table_df[columnas_deseadas].to_dict('records')

    return {'display': 'block'}, table_data

if __name__ == '__main__':
    app.run(debug=True)
