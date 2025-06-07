import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Sistema de Inundaciones - Piura", 
    layout="wide",
    page_icon="🌊"
)

# --- CONEXIÓN SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        return create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"]
        )
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
        st.stop()

supabase = init_connection()

# --- CARGA DE DATOS CON VALIDACIÓN ---
@st.cache_data(ttl=600)
def load_data(table_name):
    try:
        response = supabase.table(table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        
        # Conversión de fechas para tablas relevantes
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            df = df.dropna(subset=['fecha'])
        
        return df
    except Exception as e:
        st.error(f"Error cargando {table_name}: {str(e)}")
        return pd.DataFrame()

# Carga todas las tablas necesarias
df_estaciones = load_data("estaciones")
df_eventos = load_data("eventos_inundacion")
df_predicciones = load_data("fechas_riesgo_inundacion")
df_precipitaciones = load_data("precipitaciones")

# --- VERIFICACIÓN DE COORDENADAS ---
def verify_coordinates():
    if not df_estaciones.empty:
        required_coords = ['latitud', 'longitud']
        missing = [col for col in required_coords if col not in df_estaciones.columns]
        
        if missing:
            st.error(f"Error: La tabla 'estaciones' no tiene las columnas: {', '.join(missing)}")
            st.write("Columnas disponibles:", df_estaciones.columns.tolist())
            st.stop()

verify_coordinates()

# --- MAPA DE CALOR INTERACTIVO ---
def show_map():
    st.subheader("🔥 Mapa de Calor de Riesgo en Piura")
    
    # Preparar datos combinados de estaciones y eventos
    df_map = df_estaciones.copy()
    
    # Corregir formato de coordenadas (reemplazar ":" por ".")
    df_map['latitud'] = df_map['latitud'].astype(str).str.replace(":", ".").astype(float)
    df_map['longitud'] = df_map['longitud'].astype(str).str.replace(":", ".").astype(float)
    
    # Calcular riesgo basado en eventos históricos (si existen)
    if not df_eventos.empty:
        riesgo_por_estacion = df_eventos.groupby('id_estacion').agg({
            'nivel_agua': 'mean',
            'id_evento': 'count'
        }).rename(columns={'id_evento': 'frecuencia'})
        
        # Normalizar valores para el mapa de calor (0-1)
        riesgo_por_estacion['riesgo'] = (
            riesgo_por_estacion['nivel_agua'] * riesgo_por_estacion['frecuencia']
        ).rank(pct=True)
        
        df_map = df_map.merge(riesgo_por_estacion, on='id_estacion', how='left')
    else:
        # Si no hay eventos, usar valores predeterminados basados en posición
        df_map['riesgo'] = 0.5  # Valor medio por defecto
    
    # Crear mapa de calor
    fig = px.density_mapbox(
        df_map,
        lat='latitud',
        lon='longitud',
        z='riesgo',
        radius=20,
        zoom=13,
        center={"lat": -5.18, "lon": -80.63},
        mapbox_style="open-street-map",
        color_continuous_scale="hot",
        range_color=[0, 1],
        hover_name="nombre_estacion",
        hover_data=["riesgo"],
        title="Intensidad de Riesgo de Inundación"
    )
    
    # Personalizar barra de color
    fig.update_layout(
        coloraxis_colorbar={
            'title': 'Nivel de Riesgo',
            'tickvals': [0, 0.5, 1],
            'ticktext': ['Bajo', 'Medio', 'Alto']
        },
        margin={"r":0,"t":40,"l":0,"b":0}
    )
    
    # Añadir marcadores de puntos para las estaciones
    fig.add_scattermapbox(
        lat=df_map['latitud'],
        lon=df_map['longitud'],
        mode='markers+text',
        marker=dict(size=10, color='black'),
        text=df_map['nombre_estacion'],
        textposition="top right",
        hoverinfo='text'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Mostrar tabla de datos
    with st.expander("📊 Datos de riesgo por estación"):
        st.dataframe(df_map.sort_values('riesgo', ascending=False))

# --- PREDICCIONES ---
def show_predictions():
    st.subheader("📈 Predicciones de Inundación")
    
    if not df_predicciones.empty:
        # Métricas resumen
        col1, col2 = st.columns(2)
        with col1:
            high_risk = len(df_predicciones[df_predicciones['riesgo_inundacion'] > 0.7])
            st.metric("Días con riesgo alto", high_risk)
        
        with col2:
            last_date = df_predicciones['fecha'].max().strftime("%d/%m/%Y")
            st.metric("Última actualización", last_date)
        
        # Gráfico interactivo
        fig = px.line(
            df_predicciones,
            x="fecha",
            y="riesgo_inundacion",
            title="Evolución del Riesgo (0-1)",
            labels={'riesgo_inundacion': 'Probabilidad'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos de predicciones disponibles")

# --- EVENTOS HISTÓRICOS ---
def show_historical():
    st.subheader("🌊 Eventos Históricos")
    
    if not df_eventos.empty:
        # Filtros interactivos
        col1, col2 = st.columns(2)
        with col1:
            min_date = df_eventos['fecha'].min().to_pydatetime()
            max_date = df_eventos['fecha'].max().to_pydatetime()
            date_range = st.slider(
                "Rango de fechas",
                min_value=min_date,
                max_value=max_date,
                value=(min_date, max_date)
            )
        
        with col2:
            min_level = float(df_eventos['nivel_agua'].min())
            max_level = float(df_eventos['nivel_agua'].max())
            level_range = st.slider(
                "Rango de nivel (m)",
                min_value=min_level,
                max_value=max_level,
                value=(min_level, max_level)
            )
        
        # Aplicar filtros
        filtered = df_eventos[
            (df_eventos['fecha'].between(*date_range)) & 
            (df_eventos['nivel_agua'].between(*level_range))
        ]
        
        # Visualización en pestañas
        tab1, tab2 = st.tabs(["Gráfico", "Datos"])
        
        with tab1:
            fig = px.bar(
                filtered,
                x="fecha",
                y="nivel_agua",
                color="impacto",
                title="Niveles de Agua Registrados"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.dataframe(filtered.sort_values('fecha', ascending=False))
    else:
        st.warning("No hay datos históricos disponibles")

# --- PRECIPITACIONES ---
def show_precipitation():
    st.subheader("☔ Precipitaciones")
    
    if not df_precipitaciones.empty:
        # Verificar columnas requeridas
        required_cols = {'pp': 'Precipitación', 'tmax': 'Temperatura máxima'}
        missing_cols = [col for col in required_cols if col not in df_precipitaciones.columns]
        
        if missing_cols:
            st.error(f"Columnas faltantes en 'precipitaciones': {', '.join(missing_cols)}")
            st.write("Columnas disponibles:", df_precipitaciones.columns.tolist())
        else:
            # Gráfico de precipitación principal
            fig1 = px.line(
                df_precipitaciones,
                x="fecha",
                y="pp",
                title=f"Precipitación Diaria (mm)",
                labels={'pp': 'Precipitación (mm)'}
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            # Gráfico de relación con temperatura (solo si existen ambas columnas)
            st.write("### Relación con Temperatura")
            try:
                fig2 = px.scatter(
                    df_precipitaciones.dropna(subset=['pp', 'tmax']),
                    x="tmax",
                    y="pp",
                    trendline="lowess",
                    title=f"Precipitación vs Temperatura Máxima",
                    labels={
                        'pp': 'Precipitación (mm)',
                        'tmax': 'Temperatura máxima (°C)'
                    }
                )
                st.plotly_chart(fig2, use_container_width=True)
            except Exception as e:
                st.warning(f"No se pudo generar el gráfico de relación: {str(e)}")
                
            # Estadísticas adicionales
            with st.expander("📊 Estadísticas mensuales"):
                df_mensual = df_precipitaciones.set_index('fecha').resample('M').agg({
                    'pp': 'sum',
                    'tmax': 'mean' if 'tmax' in df_precipitaciones.columns else None
                }).reset_index()
                st.dataframe(df_mensual)
    else:
        st.warning("No hay datos de precipitación disponibles")

# --- INTERFAZ PRINCIPAL ---
st.title("🌧️ Sistema de Monitoreo de Inundaciones - Piura")

# Barra lateral de navegación
option = st.sidebar.radio(
    "Seleccione una vista:",
    ["Mapa", "Predicciones", "Histórico", "Precipitaciones"],
    index=0
)

# Mostrar sección seleccionada
if option == "Mapa":
    show_map()
elif option == "Predicciones":
    show_predictions()
    st.markdown("---")
    show_map()  # Mapa también en predicciones
elif option == "Histórico":
    show_historical()
elif option == "Precipitaciones":
    show_precipitation()
    st.markdown("---")
    show_map()  # Mapa también en precipitaciones

# --- FOOTER ---
st.markdown("---")
st.caption("Sistema desarrollado para el monitoreo de inundaciones en Piura | © 2023")

