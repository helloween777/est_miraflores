import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px

# --- CONEXIÓN A SUPABASE ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CONFIGURACIÓN DE LA BARRA LATERAL ---
st.sidebar.title("📊 Configuración de Visualización")
visualizacion_tipo = st.sidebar.radio(
    "Selecciona qué datos visualizar:",
    ["Predicciones de Inundaciones", "Eventos Históricos", "Precipitaciones", "Mapa de Puntos Críticos"]
)

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos(tabla):
    try:
        data = supabase.table(tabla).select("*").execute().data
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error cargando {tabla}: {e}")
        return pd.DataFrame()

# Cargar todas las tablas
df_estaciones = cargar_datos("estaciones")  # Contiene nombres y coordenadas
df_eventos = cargar_datos("eventos_inundacion")
df_predicciones = cargar_datos("fechas_riesgo_inundacion")
df_precipitaciones = cargar_datos("precipitaciones")

# Procesamiento de datos
for df in [df_eventos, df_predicciones, df_precipitaciones]:
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')

# --- MAPA INTERACTIVO DE PUNTOS CRÍTICOS ---
def mostrar_mapa_piura():
    st.subheader("📍 Mapa de Puntos Críticos de Inundación en Piura")
    if not df_estaciones.empty:
        # Verificar nombres de columnas de coordenadas
        lat_col = [c for c in df_estaciones.columns if 'lat' in c.lower()][0]
        lon_col = [c for c in df_estaciones.columns if 'lon' in c.lower() or 'long' in c.lower()][0]
        
        fig = px.scatter_mapbox(
            df_estaciones,
            lat=lat_col,
            lon=lon_col,
            hover_name="nombre_estacion",
            zoom=12,
            color_discrete_sequence=["red"],
            height=500
        )
        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r":0,"t":0,"l":0,"b":0}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No se encontraron datos de estaciones para el mapa.")

# --- INTERFAZ PRINCIPAL ---
st.title("🌧️ Sistema de Monitoreo de Inundaciones - Piura")

if visualizacion_tipo == "Predicciones de Inundaciones":
    st.subheader("📈 Predicciones de Riesgo")
    if not df_predicciones.empty:
        fig = px.line(
            df_predicciones, 
            x="fecha", 
            y="riesgo_inundacion",
            title="Riesgo de Inundación (0-1)"
        )
        st.plotly_chart(fig)

elif visualizacion_tipo == "Eventos Históricos":
    st.subheader("🌊 Eventos Históricos de Inundación")
    if not df_eventos.empty:
        # Filtro por rango de fechas (CORRECCIÓN APPLICADA AQUÍ)
        min_date = df_eventos['fecha'].min()
        max_date = df_eventos['fecha'].max()
        date_range = st.slider(
            "Selecciona rango de fechas",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date)  # <-- Se cerró el paréntesis correctamente
        )
        
        filtered_data = df_eventos[
            (df_eventos['fecha'] >= date_range[0]) & 
            (df_eventos['fecha'] <= date_range[1])
        ]
        
        # Gráfico de nivel de agua
        fig = px.bar(
            filtered_data,
            x='fecha',
            y='nivel_agua',
            color='impacto',
            title="Nivel de Agua en Eventos Históricos"
        )
        st.plotly_chart(fig)

elif visualizacion_tipo == "Precipitaciones":
    st.subheader("☔ Datos de Precipitación")
    if not df_precipitaciones.empty:
        # Gráfico de precipitación acumulada
        fig = px.area(
            df_precipitaciones,
            x='fecha',
            y='pp',
            title="Precipitación Diaria (mm)"
        )
        st.plotly_chart(fig)
        
        # Relación con temperatura máxima
        fig2 = px.scatter(
            df_precipitaciones,
            x='tmax',
            y='pp',
            trendline="lowess",
            title="Relación Precipitación vs Temperatura Máxima"
        )
        st.plotly_chart(fig2)

elif visualizacion_tipo == "Mapa de Puntos Críticos":
    mostrar_mapa_piura()

# Mostrar el mapa en todas las secciones excepto en su propia pestaña
if visualizacion_tipo != "Mapa de Puntos Críticos":
    st.markdown("---")
    mostrar_mapa_piura()

