from django.shortcuts import render
from django.http import HttpResponse
import json
from plotly.utils import PlotlyJSONEncoder
from .graficas import graficacamposrecurrentes, detalletritonestrimestre as dtt, grafica_global_siop_logic as ggsl, grafica_status_abierto_logic as gsal, graficacausasotros as gco
import datetime
from .graficas.utils import crear_columna_linea_con_logo
from .graficas.config import mapa_colores, color_predeterminado, ruta_logo_metrobus

def index(request):
    campo_penalizado = request.GET.get('campo_penalizado')
    df_json = request.session.get('df_campos_recurrentes_json')

    if campo_penalizado and df_json:
        tabla_html = graficacamposrecurrentes.get_detalle_campos_recurrentes_table(df_json, campo_penalizado)
        return HttpResponse(tabla_html)

    min_date, max_date = ggsl.get_date_range()
    lineas = ggsl.get_lineas()

    start_date = request.GET.get('start_date', min_date.strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', max_date.strftime('%Y-%m-%d'))
    selected_lineas = request.GET.getlist('linea')

    fig_campos_recurrentes, df_json = graficacamposrecurrentes.generar_grafica_campos_recurrentes(
        start_date=start_date,
        end_date=end_date,
        selected_lineas=selected_lineas
    )
    request.session['df_campos_recurrentes_json'] = df_json

    grafica_json = json.dumps(fig_campos_recurrentes, cls=PlotlyJSONEncoder)
    
    context = {
        'grafica_json': grafica_json,
        'min_date': min_date.strftime('%Y-%m-%d'),
        'max_date': max_date.strftime('%Y-%m-%d'),
        'start_date': start_date,
        'end_date': end_date,
        'lineas': lineas,
        'selected_lineas': selected_lineas,
    }
    return render(request, 'myapp/index.html', context)

def detalle_tritones_trimestre_view(request):
    # Obtener opciones para los filtros
    years, meses, lineas, quarters = dtt.get_filter_options()

    # Obtener parámetros de la URL (si existen)
    year = request.GET.get('year', years[0] if years else None)
    month = request.GET.get('month', None)
    quarter = request.GET.get('quarter', None)
    selected_linea = request.GET.get('linea', None)
    indicativo = request.GET.get('indicativo', None)
    campo_penalizado = request.GET.get('campo_penalizado', None)
    
    # Conversión de tipos para los parámetros
    if year: year = int(year)
    if month: month = int(month)
    if quarter: quarter = int(quarter)

    # Generar la figura principal
    fig_hist = dtt.generar_histograma_calificacion(year, month, quarter, selected_linea)

    # Generar figura de pie y tabla si hay un indicativo seleccionado
    fig_pie_json = None
    tabla_html = None
    titulo_tabla = None
    if indicativo:
        fig_pie = dtt.generar_grafica_distribucion_penalizaciones(year, month, quarter, selected_linea, indicativo)
        fig_pie_json = json.dumps(fig_pie, cls=PlotlyJSONEncoder)
        
        df_tabla, titulo_tabla = dtt.obtener_tabla_detalle_incidencias(year, month, quarter, selected_linea, indicativo, campo_penalizado)
        
        if not df_tabla.empty and 'Línea' in df_tabla.columns:
            original_cols = list(df_tabla.columns)
            # Aplicar formato de logo y color
            df_tabla = crear_columna_linea_con_logo(
                df_tabla, 'Línea', ruta_logo_metrobus, mapa_colores, color_predeterminado
            )
            # Reemplazar el contenido de la columna original con el nuevo contenido HTML
            df_tabla['Línea'] = df_tabla['Línea_Logo']
            # Asegurar el orden original de las columnas y eliminar la columna auxiliar
            df_tabla = df_tabla[original_cols]

        tabla_html = df_tabla.to_html(classes=['table', 'table-striped', 'table-hover'], index=False, escape=False)

    context = {
        'fig_hist_json': json.dumps(fig_hist, cls=PlotlyJSONEncoder),
        'fig_pie_json': fig_pie_json,
        'tabla_html': tabla_html,
        'titulo_tabla': titulo_tabla,
        'years': years,
        'meses': meses,
        'lineas': lineas,
        'quarters': quarters,
        'selected_year': year,
        'selected_month': month,
        'selected_quarter': quarter,
        'selected_linea': selected_linea,
        'selected_indicativo': indicativo
    }
    return render(request, 'myapp/detalletritonestrimestre.html', context)

def grafica_global_siop(request):
    min_date, max_date = ggsl.get_date_range()

    # Usar fechas de la petición o las por defecto
    start_date_str = request.GET.get('start_date', min_date.strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end_date', max_date.strftime('%Y-%m-%d'))
    indicativo = request.GET.get('indicativo', None)
    
    # Generar las gráficas y tablas
    graphs_data = ggsl.generate_global_siop_graphs(start_date_str, end_date_str, indicativo)

    context = {
        'min_date': min_date.strftime('%Y-%m-%d'),
        'max_date': max_date.strftime('%Y-%m-%d'),
        'start_date': start_date_str,
        'end_date': end_date_str,
        'selected_indicativo': indicativo,
        'fig_barras_json': graphs_data['fig_barras_json'],
        'fig_lineas_json': graphs_data['fig_lineas_json'],
        'supervisores_data': graphs_data['supervisores_data'],
        'tabla_detalle_html': graphs_data['tabla_detalle_html'],
        'titulo_detalle': graphs_data['titulo_detalle'],
    }
    
    return render(request, 'myapp/graficaglobalsiop.html', context)

def grafica_status_abierto(request):
    """
    Vista para la gráfica de antigüedad de folios con estatus "Abierto".
    """
    rango_seleccionado = request.GET.get('rango_antiguedad')
    df_abiertos_json = request.session.get('df_abiertos_json')

    if rango_seleccionado and df_abiertos_json:
        tabla_html = gsal.get_detalle_abiertos_table(df_abiertos_json, rango_seleccionado)
        return HttpResponse(tabla_html)

    graph_json, df_abiertos_json = gsal.generate_status_abierto_graph()
    request.session['df_abiertos_json'] = df_abiertos_json  # Guardar en sesión

    context = {
        'fig_json': graph_json,
    }
    return render(request, 'myapp/graficastatusabierto.html', context)

def grafica_causas_otros(request):
    causa = request.GET.get('causa')
    df_json = request.session.get('df_causas_otros_json')

    if causa and df_json:
        tabla_html = gco.get_detalle_causas_otros_table(df_json, causa)
        return HttpResponse(tabla_html)

    min_date, max_date = ggsl.get_date_range()
    lineas = ggsl.get_lineas()

    start_date = request.GET.get('start_date', min_date.strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', max_date.strftime('%Y-%m-%d'))
    selected_lineas = request.GET.getlist('linea')

    fig, df_json = gco.generar_grafica_causas_otros(
        start_date=start_date,
        end_date=end_date,
        selected_lineas=selected_lineas
    )
    request.session['df_causas_otros_json'] = df_json

    grafica_json = json.dumps(fig, cls=PlotlyJSONEncoder)
    
    context = {
        'grafica_json': grafica_json,
        'min_date': min_date.strftime('%Y-%m-%d'),
        'max_date': max_date.strftime('%Y-%m-%d'),
        'start_date': start_date,
        'end_date': end_date,
        'lineas': lineas,
        'selected_lineas': selected_lineas,
    }
    return render(request, 'myapp/graficacausasotros.html', context)
