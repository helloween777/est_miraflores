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

# --- CARGA DE DATOS ---
@st.cache_data(ttl=600)
def load_data(table_name):
    try:
        response = supabase.table(table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            df = df.dropna(subset=['fecha'])
        
        return df
    except Exception as e:
        st.error(f"Error cargando {table_name}: {str(e)}")
        return pd.DataFrame()

# Carga de todas las tablas necesarias
df_estaciones = load_data("estaciones")
df_eventos = load_data("eventos_inundacion")
df_predicciones = load_data("fechas_riesgo_inundacion")
df_precipitaciones = load_data("precipitaciones")
df_puntos = load_data("puntos_inundacion")  # NUEVA TABLA

# --- VERIFICACIÓN DE COORDENADAS ESTACIONES ---
def verify_coordinates():
    if not df_estaciones.empty:
        required_coords = ['latitud', 'longitud']
        missing = [col for col in required_coords if col not in df_estaciones.columns]
        if missing:
            st.error(f"Error: La tabla 'estaciones' no tiene las columnas: {', '.join(missing)}")
            st.stop()

verify_coordinates()

# --- MAPA DE ESTACIONES ---
def show_map():
    st.subheader("📍 Mapa de Estaciones Meteorológicas en Piura")
    
    df_map = df_estaciones.copy()
    df_map['color'] = ['Miraflores' if 'Miraflores' in str(n) else 'Otras' for n in df_map['nombre_estacion']]
    
    fig = px.scatter_mapbox(
        df_map,
        lat="latitud",
        lon="longitud",
        hover_name="nombre_estacion",
        color="color",
        zoom=12,
        height=600,
        color_discrete_map={"Miraflores": "red", "Otras": "blue"}
    )
    
    fig.update_layout(
        mapbox_style="open-street-map",
        margin={"r":0,"t":0,"l":0,"b":0},
        mapbox_center={"lat": -5.18, "lon": -80.63}
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("📋 Ver datos completos de estaciones"):
        st.dataframe(df_estaciones)

# --- NUEVO: MAPA DE PUNTOS DE INUNDACIÓN ---
def show_risk_points():
    st.subheader("📌 Puntos Críticos de Inundación en Piura")
    
    if not df_puntos.empty:
        if 'latitud' in df_puntos.columns and 'longitud' in df_puntos.columns:
            fig = px.scatter_mapbox(
                df_puntos,
                lat="latitud",
                lon="longitud",
                hover_name="nombre_punto" if "nombre_punto" in df_puntos.columns else "id_punto",
                color_discrete_sequence=["orange"],
                zoom=12,
                height=600
            )
            fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay coordenadas geográficas disponibles.")
        
        st.write("📋 Tabla de puntos de inundación")
        st.dataframe(df_puntos)
    else:
        st.warning("No hay datos de puntos de inundación registrados")

# --- PREDICCIONES ---
def show_predictions():
    st.subheader("📈 Predicciones de Inundación")
    
    if not df_predicciones.empty:
        col1, col2 = st.columns(2)
        with col1:
            high_risk = len(df_predicciones[df_predicciones['riesgo_inundacion'] > 0.7])
            st.metric("Días con riesgo alto", high_risk)
        with col2:
            last_date = df_predicciones['fecha'].max().strftime("%d/%m/%Y")
            st.metric("Última actualización", last_date)
        
        fig = px.line(
            df_predicciones,
            x="fecha",
            y="riesgo_inundacion",
            title="Evolución del Riesgo de Inundación (0-1)",
            labels={'riesgo_inundacion': 'Probabilidad'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos de predicción disponibles")

# --- EVENTOS HISTÓRICOS ---
def show_historical():
    st.subheader("🌊 Eventos Históricos")
    
    if not df_eventos.empty:
        col1, col2 = st.columns(2)
        with col1:
            min_date = df_eventos['fecha'].min().to_pydatetime()
            max_date = df_eventos['fecha'].max().to_pydatetime()
            date_range = st.slider("Rango de fechas", min_value=min_date, max_value=max_date, value=(min_date, max_date))
        with col2:
            min_level = float(df_eventos['nivel_agua'].min())
            max_level = float(df_eventos['nivel_agua'].max())
            level_range = st.slider("Nivel de agua (m)", min_value=min_level, max_value=max_level, value=(min_level, max_level))
        
        filtered = df_eventos[
            (df_eventos['fecha'].between(*date_range)) & 
            (df_eventos['nivel_agua'].between(*level_range))
        ]
        
        tab1, tab2 = st.tabs(["Gráfico", "Datos"])
        with tab1:
            fig = px.bar(
                filtered,
                x="fecha",
                y="nivel_agua",
                color="impacto",
                title="Niveles de Agua en Eventos Históricos"
            )
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            st.dataframe(filtered.sort_values("fecha", ascending=False))
    else:
        st.warning("No hay eventos históricos registrados")

# --- PRECIPITACIONES ---
def show_precipitation():
    st.subheader("☔ Precipitaciones")
    
    if not df_precipitaciones.empty:
        if "pp" not in df_precipitaciones.columns:
            st.error("Falta la columna 'pp' (precipitación) en la tabla.")
            return
        
        fig1 = px.line(
            df_precipitaciones,
            x="fecha",
            y="pp",
            title="Precipitación Diaria (mm)"
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        if "tmax" in df_precipitaciones.columns:
            st.write("### Relación con Temperatura Máxima")
            fig2 = px.scatter(
                df_precipitaciones.dropna(subset=['pp', 'tmax']),
                x="tmax",
                y="pp",
                trendline="lowess",
                labels={"pp": "Precipitación (mm)", "tmax": "Temperatura Máxima (°C)"}
            )
            st.plotly_chart(fig2, use_container_width=True)
        
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

option = st.sidebar.radio(
    "Seleccione una vista:",
    ["Mapa", "Predicciones", "Histórico", "Precipitaciones", "Puntos de Inundación"],
    index=0
)

if option == "Mapa":
    show_map()
elif option == "Predicciones":
    show_predictions()
    st.markdown("---")
    show_map()
elif option == "Histórico":
    show_historical()
elif option == "Precipitaciones":
    show_precipitation()
    st.markdown("---")
    show_map()
elif option == "Puntos de Inundación":
    show_risk_points()

st.markdown("---")
st.caption("Sistema desarrollado para el monitoreo de inundaciones en Piura | © 2025")


