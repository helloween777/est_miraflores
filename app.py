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

# Cargar tablas necesarias
df_estaciones = load_data("estaciones")
df_eventos = load_data("eventos_inundacion")

# --- VERIFICACIÓN DE COLUMNAS ---
if not df_eventos.empty and not df_estaciones.empty:
    # Limpiar espacios en nombres de columnas
    df_eventos.columns = df_eventos.columns.str.strip()
    df_estaciones.columns = df_estaciones.columns.str.strip()

    # Revisar existencia de la columna "id_estacion"
    if "id_estacion" in df_eventos.columns and "id_estacion" in df_estaciones.columns:
        df_eventos = df_eventos.merge(df_estaciones, on="id_estacion", how="left")
    else:
        st.error("Error: La columna 'id_estacion' no existe en una de las tablas.")
        st.write("Columnas en df_eventos:", df_eventos.columns.tolist())
        st.write("Columnas en df_estaciones:", df_estaciones.columns.tolist())
        st.stop()

# --- MAPA DE CALOR ---
def show_heatmap():
    st.subheader("🔥 Mapa de Calor de Inundaciones en Piura")

    if not df_eventos.empty:
        fig = px.density_mapbox(
            df_eventos,
            lat="latitud",
            lon="longitud",
            z="nivel_agua",  # Intensidad basada en nivel de agua
            radius=20,  # Ajustar el radio para mejorar la visibilidad
            opacity=0.8,
            zoom=12,
            height=600
        )
        
        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r":0,"t":0,"l":0,"b":0},
            mapbox_center={"lat": -5.18, "lon": -80.63}  # Centro en Piura
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("No hay datos suficientes para generar el mapa de calor.")

# --- INTERFAZ PRINCIPAL ---
st.title("🌧️ Sistema de Monitoreo de Inundaciones - Piura")

# Barra lateral de navegación
option = st.sidebar.radio(
    "Seleccione una vista:",
    ["Mapa de Calor", "Eventos Históricos"],
    index=0
)

# Mostrar sección seleccionada
if option == "Mapa de Calor":
    show_heatmap()
elif option == "Eventos Históricos":
    st.write("Aquí podríamos añadir más análisis de eventos históricos.")

# --- FOOTER ---
st.markdown("---")
st.caption("Sistema desarrollado para el monitoreo de inundaciones en Piura | © 2025")

