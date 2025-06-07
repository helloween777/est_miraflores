import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Monitoreo de Inundaciones - Piura", layout="wide")

# --- CONEXIÓN A SUPABASE (con manejo de errores) ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Error de conexión a Supabase: {e}")
    st.stop()

# --- BARRA LATERAL ---
st.sidebar.title("⚙️ Configuración")
visualizacion_tipo = st.sidebar.radio(
    "Seleccionar visualización:",
    ["Predicciones", "Eventos Históricos", "Precipitaciones", "Mapa de Riesgo"],
    index=3  # Mapa como opción por defecto
)

# --- CARGA DE DATOS (con caché y validación) ---
@st.cache_data(ttl=3600)  # Cache de 1 hora
def cargar_datos(tabla):
    try:
        response = supabase.table(tabla).select("*").execute()
        if hasattr(response, 'data'):
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error cargando {tabla}: {str(e)}")
        return pd.DataFrame()

# Carga de todas las tablas necesarias
with st.spinner("Cargando datos..."):
    df_estaciones = cargar_datos("estaciones")
    df_eventos = cargar_datos("eventos_inundacion")
    df_predicciones = cargar_datos("fechas_riesgo_inundacion")
    df_precipitaciones = cargar_datos("precipitaciones")

# --- VALIDACIÓN DE DATOS ---
def validar_datos():
    if df_estaciones.empty:
        st.warning("⚠️ La tabla 'estaciones' está vacía o no se pudo cargar")
    if 'nombre_estacion' not in df_estaciones.columns:
        st.error("La tabla 'estaciones' no tiene columna 'nombre_estacion'")

validar_datos()

# --- FUNCIÓN DEL MAPA (versión robusta) ---
def mostrar_mapa():
    st.subheader("📍 Mapa de Puntos de Riesgo en Piura")
    
    if df_estaciones.empty:
        st.warning("No hay datos de estaciones para mostrar")
        return
    
    # Detección automática de columnas de coordenadas
    coord_config = {
        'lat': next((c for c in df_estaciones.columns 
                    if 'lat' in c.lower()), None),
        'lon': next((c for c in df_estaciones.columns 
                     if 'lon' in c.lower() or 'long' in c.lower()), None)
    }
    
    # Verificación final
    if None in coord_config.values():
        st.error("""
        **Error:** No se detectaron columnas de coordenadas.  
        Se requieren columnas con 'lat'/'lon' en su nombre.  
        Columnas disponibles: """ + str(df_estaciones.columns.tolist()))
        return
    
    # Creación del mapa
    try:
        fig = px.scatter_mapbox(
            df_estaciones,
            lat=coord_config['lat'],
            lon=coord_config['lon'],
            hover_name="nombre_estacion",
            hover_data=df_estaciones.columns,
            zoom=12,
            color_discrete_sequence=["red"],
            height=600
        )
        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r":0,"t":0,"l":0,"b":0},
            mapbox_center={"lat": -5.195, "lon": -80.635}  # Centrado en Piura
        )
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error al generar el mapa: {str(e)}")

# --- VISTA DE PREDICCIONES ---
def vista_predicciones():
    st.subheader("📈 Modelo Predictivo de Inundaciones")
    if not df_predicciones.empty:
        df_pred = df_predicciones.copy()
        df_pred['fecha'] = pd.to_datetime(df_pred['fecha'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Días con riesgo alto", 
                     len(df_pred[df_pred['riesgo_inundacion'] > 0.7]))
        with col2:
            st.metric("Última predicción", 
                     df_pred['fecha'].max().strftime("%d/%m/%Y"))
        
        fig = px.area(
            df_pred,
            x='fecha',
            y='riesgo_inundacion',
            title="Evolución del Riesgo",
            labels={'riesgo_inundacion': 'Probabilidad de inundación'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos de predicciones")

# --- INTERFAZ PRINCIPAL ---
st.title("🌊 Sistema de Monitoreo Hidrometeorológico - Piura")

if visualizacion_tipo == "Predicciones":
    vista_predicciones()
    mostrar_mapa()  # Mapa debajo de las predicciones

elif visualizacion_tipo == "Eventos Históricos":
    st.subheader("🌊 Registro Histórico de Inundaciones")
    if not df_eventos.empty:
        df_events = df_eventos.copy()
        df_events['fecha'] = pd.to_datetime(df_events['fecha'])
        
        # Filtros interactivos
        col1, col2 = st.columns(2)
        with col1:
            fecha_min, fecha_max = st.slider(
                "Rango de fechas",
                min_value=df_events['fecha'].min(),
                max_value=df_events['fecha'].max(),
                value=(df_events['fecha'].min(), df_events['fecha'].max())
            )
        with col2:
            nivel_min, nivel_max = st.slider(
                "Rango de nivel de agua (m)",
                min_value=float(df_events['nivel_agua'].min()),
                max_value=float(df_events['nivel_agua'].max()),
                value=(float(df_events['nivel_agua'].min()), 
                       float(df_events['nivel_agua'].max()))
            )
        
        # Aplicar filtros
        filtered = df_events[
            (df_events['fecha'] >= fecha_min) & 
            (df_events['fecha'] <= fecha_max) &
            (df_events['nivel_agua'] >= nivel_min) &
            (df_events['nivel_agua'] <= nivel_max)
        ]
        
        # Visualización
        tab1, tab2 = st.tabs(["Gráfico Temporal", "Datos"])
        with tab1:
            fig = px.bar(
                filtered,
                x='fecha',
                y='nivel_agua',
                color='impacto',
                title="Niveles de Agua Registrados"
            )
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            st.dataframe(filtered.sort_values('fecha', ascending=False))
    else:
        st.warning("No hay datos históricos disponibles")

elif visualizacion_tipo == "Precipitaciones":
    st.subheader("☔ Análisis de Precipitaciones")
    if not df_precipitaciones.empty:
        df_rain = df_precipitaciones.copy()
        df_rain['fecha'] = pd.to_datetime(df_rain['fecha'])
        
        # Gráfico principal
        fig = px.line(
            df_rain,
            x='fecha',
            y='pp',
            title="Precipitación Diaria (mm)",
            labels={'pp': 'Precipitación (mm)'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Estadísticas
        st.write("### Estadísticas Mensuales")
        df_mensual = df_rain.set_index('fecha').resample('M')['pp'].sum().reset_index()
        fig2 = px.bar(
            df_mensual,
            x='fecha',
            y='pp',
            title="Precipitación Acumulada Mensual"
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("No hay datos de precipitación")

elif visualizacion_tipo == "Mapa de Riesgo":
    mostrar_mapa()

# --- FOOTER ---
st.markdown("---")
st.caption("Sistema desarrollado para el monitoreo de inundaciones en Piura | © 2023")

