from django.shortcuts import render
from django.http import HttpResponse
import json
from plotly.utils import PlotlyJSONEncoder
from .graficas import detalletritonestrimestre as dtt, grafica_global_siop_logic as ggsl
import datetime
from .graficas.utils import crear_columna_linea_con_logo
from .graficas.config import mapa_colores, color_predeterminado, ruta_logo_metrobus

def detalle_tritones_trimestre_view(request):
    years, meses, lineas, quarters = dtt.get_filter_options()
    year = request.GET.get('year', years[0] if years else None)
    month = request.GET.get('month', None)
    quarter = request.GET.get('quarter', None)
    selected_linea = request.GET.get('linea', None)
    indicativo = request.GET.get('indicativo', None)
    campo_penalizado = request.GET.get('campo_penalizado', None)
    
    if year: year = int(year)
    if month: month = int(month)
    if quarter: quarter = int(quarter)

    fig_hist = dtt.generar_histograma_calificacion(year, month, quarter, selected_linea)
    fig_pie_json, tabla_html, titulo_tabla = None, None, None
    
    if indicativo:
        fig_pie = dtt.generar_grafica_distribucion_penalizaciones(year, month, quarter, selected_linea, indicativo)
        fig_pie_json = json.dumps(fig_pie, cls=PlotlyJSONEncoder)
        df_tabla, titulo_tabla = dtt.obtener_tabla_detalle_incidencias(year, month, quarter, selected_linea, indicativo, campo_penalizado)
        if not df_tabla.empty and 'Línea' in df_tabla.columns:
            df_tabla = crear_columna_linea_con_logo(df_tabla, 'Línea', ruta_logo_metrobus, mapa_colores, color_predeterminado)
            df_tabla['Línea'] = df_tabla['Línea_Logo']
            df_tabla = df_tabla[list(df_tabla.columns)]
        tabla_html = df_tabla.to_html(classes=['table', 'table-striped', 'table-hover'], index=False, escape=False)

    context = {
        'fig_hist_json': json.dumps(fig_hist, cls=PlotlyJSONEncoder), 'fig_pie_json': fig_pie_json,
        'tabla_html': tabla_html, 'titulo_tabla': titulo_tabla, 'years': years, 'meses': meses,
        'lineas': lineas, 'quarters': quarters, 'selected_year': year, 'selected_month': month,
        'selected_quarter': quarter, 'selected_linea': selected_linea, 'selected_indicativo': indicativo
    }
    return render(request, 'myapp/detalletritonestrimestre.html', context)

def grafica_global_siop(request):
    # --- Callbacks AJAX para tablas de detalle ---
    if 'campo_penalizado' in request.GET and request.session.get('df_filtrado_json'):
        return HttpResponse(ggsl.get_detalle_campos_recurrentes_table(request.session['df_filtrado_json'], request.GET['campo_penalizado']))
    if 'rango_antiguedad' in request.GET and request.session.get('df_abiertos_json'):
        return HttpResponse(ggsl.get_detalle_abiertos_table(request.session['df_abiertos_json'], request.GET['rango_antiguedad']))
    if 'causa_otro' in request.GET and request.session.get('df_causas_otros_json'):
        return HttpResponse(ggsl.get_detalle_causas_otros_table(request.session['df_causas_otros_json'], request.GET['causa_otro']))

    # --- Lógica principal ---
    min_date, max_date = ggsl.get_date_range()
    lineas = ggsl.get_lineas()
    start_date = request.GET.get('start_date', min_date.strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', max_date.strftime('%Y-%m-%d'))
    
    # Filtros
    selected_lineas = request.GET.getlist('linea') or None 
    indicativo = request.GET.get('indicativo')

    graphs_data = ggsl.generate_global_siop_graphs(start_date, end_date, indicativo, selected_lineas)

    # Guardar DFs en sesión
    request.session['df_filtrado_json'] = graphs_data['df_filtrado_json']
    request.session['df_abiertos_json'] = graphs_data['df_abiertos_json']
    request.session['df_causas_otros_json'] = graphs_data['df_causas_otros_json']

    context = {
        'min_date': min_date.strftime('%Y-%m-%d'), 'max_date': max_date.strftime('%Y-%m-%d'),
        'start_date': start_date, 'end_date': end_date, 'lineas': lineas,
        'selected_lineas': selected_lineas or [],
        'selected_indicativo': indicativo, 'fig_barras_json': graphs_data['fig_barras_json'],
        'fig_lineas_json': graphs_data['fig_lineas_json'], 'fig_campos_recurrentes_json': graphs_data['fig_campos_recurrentes_json'],
        'fig_status_abierto_json': graphs_data['fig_status_abierto_json'], 'fig_causas_otros_json': graphs_data['fig_causas_otros_json'],
        'supervisores_data': graphs_data['supervisores_data'], 'tabla_detalle_html': graphs_data['tabla_detalle_html'],
        'titulo_detalle': graphs_data['titulo_detalle']
    }
    return render(request, 'myapp/graficaglobalsiop.html', context)
