
import dash
from dash import dcc, html, dash_table, Input, Output
import plotly.express as px
import pandas as pd
import siopcalidad
from datetime import datetime

# Importar configuraciones y la nueva función de utilidad
from config import columnas_deseadas, mapa_colores, ruta_logo_metrobus
from utils import crear_columna_linea_con_logo

# --- 1. CARGA Y PREPARACIÓN DE DATOS ---
df = siopcalidad.obtener_datos_procesados()
df['fechahora'] = pd.to_datetime(df['fechahora']).dt.tz_localize(None)
df['Estatus'] = df['Estatus'].str.strip()

# --- 2. LÓGICA DE ANTIGÜEDAD DE SALDOS ---
df_abiertos = df[df['Estatus'] == 'ABIERTO'].copy()
df_abiertos['Línea'] = df_abiertos['Línea'].astype(str)

hoy = pd.to_datetime(datetime.now().date())
df_abiertos.loc[:, 'antiguedad'] = (hoy - pd.to_datetime(df_abiertos['Fecha'])).dt.days

bins = [0, 30, 60, 90, float('inf')]
labels = ['1-30 días', '31-60 días', '61-90 días', '91+ días']
df_abiertos['rango_antiguedad'] = pd.cut(df_abiertos['antiguedad'], bins=bins, labels=labels, right=False)

# --- 3. PREPARACIÓN DE DATOS PARA LA GRÁFICA ---
antiguedad_por_linea = df_abiertos.groupby(['rango_antiguedad', 'Línea'], observed=False).size().reset_index(name='conteo')
antiguedad_por_linea['rango_antiguedad'] = pd.Categorical(antiguedad_por_linea['rango_antiguedad'], categories=labels, ordered=True)
antiguedad_por_linea = antiguedad_por_linea.sort_values('rango_antiguedad')

# --- 4. CREACIÓN DE LA GRÁFICA ---
fig = px.bar(antiguedad_por_linea, 
             x='rango_antiguedad', y='conteo', color='Línea', barmode='stack',
             title='Antigüedad de Folios con Estatus "Abierto" por Línea',
             labels={'rango_antiguedad': 'Rango de Antigüedad', 'conteo': 'Cantidad de Folios'},
             text='conteo', color_discrete_map=mapa_colores)

# --- 4.1 AÑADIR ETIQUETAS DE TOTALES ---
totales_por_rango = antiguedad_por_linea.groupby('rango_antiguedad', observed=False)['conteo'].sum()
for rango, total in totales_por_rango.items():
    if total > 0:
        fig.add_annotation(x=rango, y=total, text=f"<b>{total}</b>", showarrow=False, font=dict(size=12, color="black"), yshift=5)

fig.update_traces(texttemplate='%{text:,}', textposition='inside')
fig.update_layout(xaxis_title="Rango de Antigüedad (días)", yaxis_title="Cantidad de Folios",
                  title_x=0.5, legend_title="Línea", margin=dict(t=100))

# --- 5. LAYOUT DE LA APLICACIÓN DASH ---
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'], assets_folder='assets')
server = app.server

app.layout = html.Div([
    html.H3("Análisis de Antigüedad de Folios Abiertos", style={'textAlign': 'center', 'fontweight': 'bold', 'fontStyle': 'italic'}),
    dcc.Graph(id='grafica-antiguedad', figure=fig),
    html.Div(id='tabla-detalle-container')
])

# --- 6. CALLBACK PARA LA TABLA DE DETALLE ---
@app.callback(
    Output('tabla-detalle-container', 'children'),
    Input('grafica-antiguedad', 'clickData')
)
def mostrar_tabla_detalle(clickData):
    if clickData is None: return []

    rango_seleccionado = clickData['points'][0]['x']
    df_filtrado = df_abiertos[df_abiertos['rango_antiguedad'] == rango_seleccionado]
    columnas_existentes = [col for col in columnas_deseadas if col in df_filtrado.columns]
    
    if not 'Línea' in df_filtrado.columns:
        df_display = df_filtrado[columnas_existentes]
        table_columns = [{'name': i, 'id': i} for i in columnas_existentes]
        style_data_conditional = []
    else:
        # Usar la función de utilidad para crear la columna con logo
        df_display = crear_columna_linea_con_logo(df_filtrado, 'Línea', ruta_logo_metrobus)
        df_display = df_display[columnas_existentes + ['Línea_Logo']]

        table_columns = []
        for col in columnas_existentes:
            if col == 'Línea':
                table_columns.append({'name': 'Línea', 'id': 'Línea_Logo', 'presentation': 'markdown'})
            else:
                table_columns.append({'name': col, 'id': col})

        style_data_conditional = []
        for linea, color in mapa_colores.items():
            style_data_conditional.append({
                'if': {'filter_query': f'{{Línea}} = "{linea}"', 'column_id': 'Línea_Logo'},
                'backgroundColor': color, 'color': 'white'
            })

    return [
        html.H3(f"Detalle de Folios por Rango de días: {rango_seleccionado}", style={'textAlign': 'center', 'font-weight': 'bold'}),
        dash_table.DataTable(
            id='tabla-datos', data=df_display.to_dict('records'),
            columns=table_columns, page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={'height': 'auto', 'minWidth': '100px', 'width': '150px', 'maxWidth': '200px', 'whiteSpace': 'normal', 'textAlign': 'left'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=style_data_conditional, markdown_options={"html": True}
        )
    ]

# --- 7. EJECUTAR LA APLICACIÓN ---
if __name__ == '__main__':
    app.run(debug=True)
