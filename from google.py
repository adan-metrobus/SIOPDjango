from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pandas as pd
import numpy as np
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import os

# Authenticate and create the PyDrive client.
gauth = GoogleAuth()

# Try to load saved client credentials
if os.path.exists("mycreds.txt"):
    gauth.LoadCredentialsFile("mycreds.txt")

if gauth.credentials is None:
    # Authenticate if they're not there
    gauth.CommandLineAuth()
elif gauth.access_token_expired:
    # Refresh them if expired
    gauth.Refresh()
else:
    # Initialize the saved creds
    gauth.Authorize()

# Save the current credentials to a file
gauth.SaveCredentialsFile("mycreds.txt")

drive = GoogleDrive(gauth)

# Search for the files in your Google Drive
file_list = drive.ListFile({'q': "title='PruebaSCIEM.csv' or title='CatCategorias.csv'"}).GetList()

file_id_prueba = None
file_id_cat = None

for file in file_list:
    if file['title'] == 'PruebaSCIEM.csv':
        file_id_prueba = file['id']
    if file['title'] == 'CatCategorias.csv':
        file_id_cat = file['id']

if not file_id_prueba or not file_id_cat:
    print("Error: Could not find 'PruebaSCIEM.csv' or 'CatCategorias.csv' in your Google Drive.")
    exit()

# Download the files
file_prueba = drive.CreateFile({'id': file_id_prueba})
file_prueba.GetContentFile('PruebaSCIEM.csv')

file_cat = drive.CreateFile({'id': file_id_cat})
file_cat.GetContentFile('CatCategorias.csv')

# Load the data into pandas DataFrames
df = pd.read_csv('PruebaSCIEM.csv')
df1 = pd.read_csv('CatCategorias.csv')

df['fecha']= pd.to_datetime(df['Fecha del reporte'],format='%d/%m/%Y')
df['año'] = df['fecha'].dt.year
df['mes'] = df['fecha'].dt.strftime('%b')
df['semana']= df['fecha'].dt.isocalendar().week
df['trimestre'] = df['fecha'].dt.quarter
df['tipo']= 'Sin tipo' # se inicia con campo para asignar Tipo de reporte coincidente tambien con el ICI
# Se elabora Diccionario pero debe ser una tabla relacionada al campo Categoria para el agrupamiento de la informacion de acuerdo a ICI
condiciones = [df['Categoría'] == row['Categoria'] for index, row in df1.iterrows()]
# Crea la lista de opciones basadas en la columna 'nomici' df1
opciones = [row['nomici'] for index, row in df1.iterrows()]
df['tipo'] = np.select(condiciones, opciones, default='Sin Tipo')

from typing import Dict
categradar = ['Accesibilidad',
              'Instalación eléctrica',
              'Instalación hidráulica',
              'Sanitarios'
             ]

df_filt = df[df['tipo'].isin(categradar)]
df_agrupado = df_filt.groupby(['tipo','linea','estacion']).size().reset_index(name='replin')
print(df_agrupado)

app = dash.Dash(__name__) # Use dash.Dash directly
server = app.server

# valores unicos para listas desplegables
lineasdisp = sorted(df_agrupado['linea'].unique())
estacionesdisp = sorted(df_agrupado['estacion'].unique())

app.layout = html.Div([
    html.H1("Reportes por Estación y Línea"),

    html.Div([
        html.Label("Línea:"),
        dcc.Dropdown(
            id='linea-dropdown',
            options=[{'label': i, 'value': i} for i in lineasdisp],
            value=None
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),

    html.Div([
        html.Label("Estación:"),
        dcc.Dropdown(
            id='estacion-dropdown',
            options=[{'label': i, 'value': i} for i in estacionesdisp],
            value=None
        ),
    ], style={'width': '48%', 'float': 'right', 'display': 'inline-block'}),

    dcc.Graph(id='polar-chart')
])

@app.callback(
    Output('polar-chart', 'figure'),
    [Input('linea-dropdown', 'value'),
     Input('estacion-dropdown', 'value')]
)
def update_graph(selected_linea, selected_estacion):
    filtered_df = df_agrupado

    sellinea = 'Sin Filtro'
    selestacion = 'Sin Filtro'

    if selected_linea and selected_estacion:
            filtered_df = filtered_df[(filtered_df['linea'] == selected_linea) & (filtered_df['estacion'] == selected_estacion)]
            sellinea = selected_linea
            selestacion = selected_estacion
    elif selected_linea:
            filtered_df = filtered_df[filtered_df['linea'] == selected_linea]
            sellinea = selected_linea
            selestacion = 'Sin Filtro'
    elif selected_estacion:
            filtered_df = filtered_df[filtered_df['estacion'] == selected_estacion]
            sellinea = 'Sin Filtro'
            selestacion = selected_estacion
    else:
            sellinea = 'Sin Filtro'
            selestacion = 'Sin Filtro'


    # Agrupamos despues de filtrar el df
    grouped_df = filtered_df.groupby('tipo')['replin'].sum().reset_index()

    print(grouped_df)

    fig = px.line_polar(grouped_df, r='replin', theta='tipo', line_close=True, title=f'Reportes para Linea: {sellinea} y Estacion: {selestacion}')

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
