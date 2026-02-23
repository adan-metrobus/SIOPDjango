import pandas as pd
import csv
import os
from functools import lru_cache

# Get the absolute path of the directory containing this script
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# ===============================
# Constantes
# ===============================
PATH_LINEAS = os.path.join(_CURRENT_DIR, "..", "data", "Lineas.csv")
PATH_ESTACIONES = os.path.join(_CURRENT_DIR, "..", "data", "Estaciones.csv")
PATH_APERTURAS = os.path.join(_CURRENT_DIR, "..", "data", "siop.csv")

CALIFICACION_INICIAL = 10.0

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
    'Estación Inicial',
    'Estación Final'
]

NA_VALUES = ["nan", "No Aplica", " ", "N/A", "","Sin Tipo","NaN"]
INVALIDAS_CAUSA_RAW = [
    "bajo revision",
    "nan",
    "sin datos (detallar en el campo observaciones)",
    "otro (detallar en el campo observaciones)"
]

# Especificar dtypes para columnas con tipos mixtos para evitar DtypeWarning
DTYPES_APERTURAS = {
    8: str, 31: str, 40: str, 64: str, 65: str, 66: str, 67: str, 68: str
}

# ===============================
# Funciones de procesamiento
# ===============================
def normalizar_columna(col: pd.Series) -> pd.Series:
    """Normaliza una columna de texto para facilitar las comparaciones."""
    return (
        col.astype(str)
           .str.lower()
           .str.normalize('NFD')
           .str.encode('ascii', 'ignore')
           .str.decode('utf-8')
           .str.replace(r'[^a-z0-9\s]', '', regex=True)
           .str.replace(r'\s+', ' ', regex=True)
           .str.strip()
    )

INVALIDAS_CAUSA = [normalizar_columna(pd.Series(c)).iloc[0] for c in INVALIDAS_CAUSA_RAW]

def cargar_datos():
    """Carga los datos desde los archivos CSV."""
    df_lineas = pd.read_csv(PATH_LINEAS, encoding="utf-8")
    df_estaciones = pd.read_csv(PATH_ESTACIONES, encoding="utf-8")
    df_aperturas = pd.read_csv(
        PATH_APERTURAS,
        encoding="utf-8",
        na_values=NA_VALUES,
        dtype=DTYPES_APERTURAS
    )
    return df_lineas, df_estaciones, df_aperturas

def preparar_datos(df_lineas, df_estaciones, df_aperturas):
    """Prepara y limpia los DataFrames para el análisis."""
    df_aperturas = df_aperturas[df_aperturas["Línea"] != "T"].copy()

    df_aperturas['Latitud'] = pd.to_numeric(df_aperturas['Latitud'], errors='coerce')
    df_aperturas['Longitud'] = pd.to_numeric(df_aperturas['Longitud'], errors='coerce')
    df_lineas['NomLinea'] = normalizar_columna(df_lineas['NomLinea'])
    df_estaciones['nombreestacion'] = normalizar_columna(df_estaciones['nombreestacion'])
    df_estaciones['NomLinea'] = normalizar_columna(df_estaciones['NomLinea'])
    df_aperturas['Línea'] = normalizar_columna(df_aperturas['Línea'])
    df_aperturas['Indicativo'] = normalizar_columna(df_aperturas['Indicativo'])
    df_aperturas['Estación'] = normalizar_columna(df_aperturas['Estación'])
    df_aperturas['Causa_norm'] = normalizar_columna(df_aperturas['Causa'])
    df_aperturas['Estatus_norm'] = normalizar_columna(df_aperturas['Estatus'])
    df_aperturas['Observacion_norm'] = normalizar_columna(df_aperturas['Observación'])
    df_aperturas['fechahora'] = pd.to_datetime(df_aperturas['Fecha'], errors='coerce') + pd.to_timedelta(df_aperturas['Hora'], errors='coerce')
    df_aperturas['Hora'] = pd.to_datetime(df_aperturas['Hora'], format='%H:%M:%S', errors='coerce').dt.time
    df_aperturas['Hora de Cierre'] = pd.to_datetime(df_aperturas['Hora de Cierre'], format='%H:%M:%S', errors='coerce').dt.time
    df_aperturas['horacierrecorrecta'] = df_aperturas['Hora de Cierre'] < df_aperturas['Hora']
    prefixes = [
        "https://metrobus.workplace.com/groups/",
        "https://chat.google.com/room/AAQA_d_ePWg/",
        "https://siop-mb.app-metrobus.com/Seguimiento/"
    ]
    seguimiento_str = df_aperturas['Seguimiento'].astype(str)
    cond_seguimiento_valido = seguimiento_str.str.startswith(tuple(prefixes))
    df_aperturas['seguimiento_valido'] = cond_seguimiento_valido
    cond_subtipo_es_A1 = df_aperturas['Subtipo'] == 'A1-Colisión (ambos vehículos en movimiento)'
    keywords_subtipo = ['moto', 'potro', 'potra', 'bici']
    cond_keywords_subtipo_presentes = df_aperturas['Observacion_norm'].str.contains('|'.join(keywords_subtipo), na=False)
    df_aperturas['penalizar_subtipo_por_obs'] = cond_subtipo_es_A1 & cond_keywords_subtipo_presentes
    cond_tipo_es_B = df_aperturas['Tipo'] == 'B-Apoyo médico'
    cond_frenado_presente = df_aperturas['Observacion_norm'].str.contains('frenado', na=False)
    df_aperturas['penalizar_tipo_por_obs'] = cond_tipo_es_B & cond_frenado_presente
    cond_subtipo_es_C2 = df_aperturas['Subtipo'] == 'C2-Bloqueo / Interrupción del servicio'
    personas_afectadas_str = df_aperturas['Cantidad de Personas Afectadas'].astype(str)
    cond_personas_vacio = df_aperturas['Cantidad de Personas Afectadas'].isna() | personas_afectadas_str.str.strip().eq('') | personas_afectadas_str.str.lower().eq('nan')
    df_aperturas['penalizar_subtipo_por_c2'] = cond_subtipo_es_C2 & cond_personas_vacio

    return df_lineas, df_estaciones, df_aperturas

def _obtener_penalizaciones(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula un DataFrame booleano de penalizaciones para cada campo."""
    penalizaciones = pd.DataFrame(index=df.index)
    cols_std_check = [col for col in COLUMNAS_A if col not in ['Causa', 'horacierrecorrecta', 'Seguimiento', 'Subtipo', 'Tipo']]
    for col in cols_std_check:
        penalizaciones[col] = df[col].isna() | df[col].astype(str).str.strip().eq('')
    penalizaciones['horacierrecorrecta'] = df['horacierrecorrecta']
    cond_estatus_cerrado = df['Estatus_norm'] == 'cerrado'
    cond_causa_invalida = df['Causa_norm'].isin(INVALIDAS_CAUSA)
    penalizaciones['Causa'] = cond_estatus_cerrado & cond_causa_invalida
    penalizaciones['Seguimiento'] = ~df['seguimiento_valido']
    penalidad_estandar_subtipo = df['Subtipo'].isna() | df['Subtipo'].astype(str).str.strip().eq('')
    penalizaciones['Subtipo'] = penalidad_estandar_subtipo | df['penalizar_subtipo_por_obs'] | df['penalizar_subtipo_por_c2']
    penalidad_estandar_tipo = df['Tipo'].isna() | df['Tipo'].astype(str).str.strip().eq('')
    penalizaciones['Tipo'] = penalidad_estandar_tipo | df['penalizar_tipo_por_obs']
    for col in COLUMNAS_B:
        penalizaciones[col] = df[col].isna() | df[col].astype(str).str.strip().eq('')
    return penalizaciones

def calcular_calificacion(df: pd.DataFrame, penalizaciones: pd.DataFrame) -> pd.Series:
    """Calcula la calificación final basada en las penalizaciones."""
    descuento_a = CALIFICACION_INICIAL / len(COLUMNAS_A)
    descuento_ab = CALIFICACION_INICIAL / (len(COLUMNAS_A) + len(COLUMNAS_B))
    es_c3 = df['Subtipo'] == 'C3-Marcha'
    columnas_penalizables = COLUMNAS_A.copy()
    if any(es_c3):
        columnas_penalizables.extend(COLUMNAS_B)
    calificacion = pd.Series(CALIFICACION_INICIAL, index=df.index)
    calificacion.loc[~es_c3] -= (penalizaciones[COLUMNAS_A].loc[~es_c3].sum(axis=1)) * descuento_a
    calificacion.loc[es_c3] -= (penalizaciones[columnas_penalizables].loc[es_c3].sum(axis=1)) * descuento_ab
    return calificacion.clip(lower=0)

def obtener_detalle_penalizaciones(df: pd.DataFrame, penalizaciones: pd.DataFrame) -> pd.Series:
    """Obtiene una lista de los campos penalizados para cada fila."""
    es_c3 = df['Subtipo'] == 'C3-Marcha'
    detalles = []
    for idx in df.index:
        penalizados = [col for col in COLUMNAS_A if penalizaciones.loc[idx, col]]
        if es_c3.loc[idx]:
            penalizados.extend([col for col in COLUMNAS_B if penalizaciones.loc[idx, col]])
        detalles.append(penalizados)
    return pd.Series(detalles, index=df.index)

# ===============================
# Nueva función principal
# ===============================
@lru_cache(maxsize=None)
def obtener_datos_procesados():
    """Función principal que carga, procesa y devuelve el DataFrame de aperturas."""
    # 1. Cargar y preparar los datos
    df_lineas, df_estaciones, df_aperturas = cargar_datos()
    df_lineas, df_estaciones, df_aperturas = preparar_datos(df_lineas, df_estaciones, df_aperturas)

    # 2. Calcular penalizaciones
    penalizaciones_df = _obtener_penalizaciones(df_aperturas)

    # 3. Realizar cálculos de calificación y detalles
    df_aperturas['calificacion'] = calcular_calificacion(df_aperturas, penalizaciones_df)
    detalles_penalizaciones = obtener_detalle_penalizaciones(df_aperturas, penalizaciones_df)

    # LÓGICA DE CORRECCIÓN EN EL ORIGEN
    # Primero, calcular la cantidad real de penalizaciones desde la lista original
    df_aperturas['cantidad_penalizaciones'] = detalles_penalizaciones.apply(len)
    
    # Segundo, crear la columna de texto para visualización, reemplazando las vacías.
    # Esto asegura que no habrá más valores '1', '', o problemáticos.
    def format_penalties(penalty_list):
        if not penalty_list:
            return 'Sin Penalización'
        else:
            # Convertimos cada item a string por si acaso hay algo que no lo sea
            return ', '.join(map(str, penalty_list))

    df_aperturas['campos_penalizados'] = detalles_penalizaciones.apply(format_penalties)


    # 4. Limpiar columnas temporales
    df_aperturas.drop(columns=[
        'Causa_norm', 'Estatus_norm', 'Observacion_norm', 'seguimiento_valido', 
        'penalizar_subtipo_por_obs', 'penalizar_tipo_por_obs', 'penalizar_subtipo_por_c2'
    ], inplace=True)

    return df_aperturas

# ===============================
# Bloque de ejecución directa
# ===============================
if __name__ == "__main__":
    # Procesar los datos
    df_final = obtener_datos_procesados()

    # Guardar los resultados en un archivo CSV
    df_final.to_csv(
        "siop_calificaciones.csv",
        index=False,
        encoding="utf-8-sig",
        quoting=csv.QUOTE_ALL
    )

    print("El script 'siopcalidad.py' ha sido ejecutado y 'siop_calificaciones.csv' ha sido generado exitosamente.")
