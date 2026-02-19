
import dash
from dash import dcc, html, dash_table, no_update
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
import siopcalidad

# 1. Cargar y preparar los datos iniciales
df = siopcalidad.obtener_datos_procesados()
df['fechahora'] = pd.to_datetime(df['fechahora']).dt.tz_localize(None)

min_date = df['fechahora'].min().date()
max_date = df['fechahora'].max().date()

# 2. Inicializar la aplicación Dash
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
server = app.server

# 3. Definir el layout
app.layout = html.Div([
    html.H3('Calificaciones Globales (SIOP)', style={'textAlign': 'center', 'marginBottom': '20px'}),
    dcc.Store(id='memoria-df-filtrado'), # Componente para guardar el df filtrado

    html.Div([
        html.Label('Selecciona un Rango de Fechas:'),
        dcc.DatePickerRange(
            id='selector-fecha',
            min_date_allowed=min_date,
            max_date_allowed=max_date,
            start_date=min_date,
            end_date=max_date,
            display_format='DD/MM/YYYY',
            style={'marginLeft': '10px'}
        ),
    ], style={'textAlign': 'center', 'marginBottom': '30px'}),

    html.Div([
        html.Div([dcc.Graph(id='grafica-calificaciones-rango')], style={'width': '49%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        html.Div([dcc.Graph(id='grafica-promedio-mensual')], style={'width': '49%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ]),

    html.Hr(),

    html.Div([
        html.H3('Promedio por Supervisor', style={'textAlign': 'center'}),
        html.P('Haz clic en un Indicativo para ver el detalle', style={'textAlign': 'center', 'fontSize': '14px'}),
        dash_table.DataTable(
            id='tabla-supervisor',
            style_cell={'textAlign': 'left', 'padding': '5px', 'cursor': 'pointer'},
            style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
            ],
            page_size=10,
        )
    ], style={'padding': '0 40px'}),

    html.Hr(),
    html.Div(id='contenedor-tabla-detalle', style={'padding': '0 20px'})
])

# 4. Callback UNIFICADO para manejar todas las actualizaciones
@app.callback(
    Output('grafica-calificaciones-rango', 'figure'),
    Output('grafica-promedio-mensual', 'figure'),
    Output('tabla-supervisor', 'data'),
    Output('tabla-supervisor', 'columns'),
    Output('contenedor-tabla-detalle', 'children'),
    Input('selector-fecha', 'start_date'),
    Input('selector-fecha', 'end_date'),
    Input('tabla-supervisor', 'active_cell'),
    State('tabla-supervisor', 'data')
)
def actualizar_panel_completo(start_date, end_date, active_cell, data_tabla_supervisor):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Filtrar el DF principal según el rango de fechas
    mask_fechas = (df['fechahora'] >= pd.to_datetime(start_date)) & (df['fechahora'] <= pd.to_datetime(end_date))
    df_filtrado_fecha = df[mask_fechas].copy()

    # Lógica cuando se cambia la fecha (o en la carga inicial)
    if triggered_id == 'selector-fecha' or not triggered_id:
        # --- Gráficas ---
        bins = [0, 5, 6, 7, 8, 9, 10.1]; labels = ['0-5', '5-6', '6-7', '7-8', '8-9', '9-10']
        df_filtrado_fecha['rango_calificacion'] = pd.cut(df_filtrado_fecha['calificacion'], bins=bins, labels=labels, right=False)

        # 1. Cambia 'mean()' por 'size()' para contar los elementos
        conteo_por_rango = df_filtrado_fecha.groupby('rango_calificacion', observed=True).size().reset_index(name='conteo')

        # 2. Actualiza 'y', 'title' y 'text' para usar el conteo
        fig_barras = px.bar(conteo_por_rango, 
                    x='rango_calificacion', 
                    y='conteo', 
                    title='Distribución de Calificaciones', 
                    text='conteo', 
                    color='conteo', 
                    color_continuous_scale=px.colors.sequential.Teal)

        # 3. Elimina el rango fijo del eje Y y actualiza el título del eje
        fig_barras.update_layout(coloraxis_showscale=False, 
                    title_x=0.5, 
                    yaxis_title='Calificaciones'),
        fig_barras.update_traces(texttemplate='%{y:,}', textposition='outside')            

        df_filtrado_fecha['año'] = df_filtrado_fecha['fechahora'].dt.year; df_filtrado_fecha['mes'] = df_filtrado_fecha['fechahora'].dt.month
        promedio_mensual = df_filtrado_fecha.groupby(['año', 'mes'])['calificacion'].mean().reset_index()
        fig_lineas = px.line(promedio_mensual, x='mes', y='calificacion', color='año', title='Promedio Mensual', markers=True)
        fig_lineas.update_layout(xaxis=dict(tickmode='array', tickvals=list(range(1, 13)), ticktext=['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']), yaxis=dict(range=[7.5, 10]), title_x=0.5)
        
        # --- Tabla Supervisores ---
        df_tabla = df_filtrado_fecha.groupby(['Indicativo', 'Nombre Del Supervisor'])['calificacion'].mean().reset_index()
        df_tabla.rename(columns={'calificacion': 'Promedio Calificación'}, inplace=True)
        df_tabla['Promedio Calificación'] = df_tabla['Promedio Calificación'].round(2)
        df_tabla.sort_values('Promedio Calificación', ascending=True, inplace=True)
        data_tabla_out = df_tabla.to_dict('records')
        columns_tabla_out = [{'name': i, 'id': i} for i in df_tabla.columns]

        return fig_barras, fig_lineas, data_tabla_out, columns_tabla_out, [] # Limpia la tabla de detalle

    # Lógica cuando se hace clic en la tabla de supervisores
    elif triggered_id == 'tabla-supervisor' and active_cell and active_cell['column_id'] == 'Indicativo':
        row_index = active_cell['row']
        indicativo_seleccionado = data_tabla_supervisor[row_index]['Indicativo']
        
        df_detalle = df_filtrado_fecha[df_filtrado_fecha['Indicativo'] == indicativo_seleccionado].copy()
        df_detalle['Fecha'] = df_detalle['fechahora'].dt.date
        df_detalle['Hora'] = df_detalle['fechahora'].dt.strftime('%H:%M:%S')

        columnas_deseadas = [
            'Folio de Incidencia', 'Fecha', 'Hora', 'Indicativo', 'Nombre Del Supervisor', 'Línea', 'Estación', 'Latitud', 
            'Longitud', 'Tipo', 'Subtipo' , 'Causa', 'Seguimiento', 'Hora de Cierre', 'Estatus', 'Observación', 
            'Cantidad de Personas Afectadas', 'Estación Inicial', 'Estación Final', 'calificacion', 
            'cantidad_penalizaciones', 'campos_penalizados'
        ]
        df_detalle_final = df_detalle[columnas_deseadas]

        tabla_detalle = dash_table.DataTable(
            columns=[{'name': i, 'id': i} for i in df_detalle_final.columns],
            data=df_detalle_final.to_dict('records'),
            page_size=15,
            style_cell={'textAlign': 'left', 'padding': '5px', 'fontSize': '12px'},
            style_header={'backgroundColor': '#f2f2f2', 'fontWeight': 'bold'},
            style_table={'overflowX': 'auto'}
        )
        detalle_out = [
            html.H4(f'Detalle de Incidencias para: {indicativo_seleccionado}', style={'textAlign': 'center'}),
            tabla_detalle
        ]
        
        # No actualices las otras salidas
        return no_update, no_update, no_update, no_update, detalle_out

    else: # Si el clic no fue válido o fue en otra celda
        return no_update, no_update, no_update, no_update, no_update

# 5. Punto de entrada para ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
