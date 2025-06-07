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

# Carga las tablas necesarias
df_estaciones = load_data("estaciones")
df_eventos = load_data("eventos_inundacion")

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

# --- MAPA DE CALOR MEJORADO ---
def show_heatmap():
    st.subheader("🔥 Mapa de Calor de Inundaciones Históricas")
    
    # 1. Preparar datos de estaciones
    df_estaciones['latitud'] = df_estaciones['latitud'].astype(str).str.replace(":", ".").astype(float)
    df_estaciones['longitud'] = df_estaciones['longitud'].astype(str).str.replace(":", ".").astype(float)
    
    # 2. Calcular densidad de eventos por proximidad geográfica
    heat_data = df_estaciones.copy()
    heat_data['eventos'] = 0
    
    if not df_eventos.empty:
        # Asumimos que los eventos están georreferenciados
        for idx, estacion in df_estaciones.iterrows():
            # Radio aproximado de 1km (0.01 grados)
            cerca = df_eventos[
                (abs(df_eventos['latitud'].astype(float) - estacion['latitud']) < 0.01 &
                (abs(df_eventos['longitud'].astype(float) - estacion['longitud']) < 0.01)
            ]
            heat_data.at[idx, 'eventos'] = len(cerca)
    
    # Normalizar riesgo (0-1)
    max_eventos = heat_data['eventos'].max() if not heat_data.empty else 1
    heat_data['riesgo'] = heat_data['eventos'] / max_eventos
    
    # 3. Crear mapa de calor
    fig = px.density_mapbox(
        heat_data,
        lat='latitud',
        lon='longitud',
        z='riesgo',
        radius=40,
        zoom=14,
        center={"lat": -5.18, "lon": -80.63},
        mapbox_style="open-street-map",
        color_continuous_scale="hot",
        range_color=[0, 1],
        hover_name="nombre_estacion",
        hover_data={"eventos": True, "riesgo": ":.0%"},
        title="Densidad de Eventos de Inundación"
    )
    
    # 4. Añadir marcadores de estaciones
    fig.add_scattermapbox(
        lat=heat_data['latitud'],
        lon=heat_data['longitud'],
        mode='markers+text',
        marker=dict(size=12, color='black'),
        text=heat_data['nombre_estacion'],
        textposition="top center"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 5. Mostrar datos
    with st.expander("📊 Datos de riesgo por estación"):
        st.dataframe(heat_data.sort_values('riesgo', ascending=False))

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
    st.subheader("🌊 Eventos Históricos")
    if not df_eventos.empty:
        st.dataframe(df_eventos.sort_values('fecha', ascending=False))
    else:
        st.warning("No hay datos históricos disponibles")

# --- FOOTER ---
st.markdown("---")
st.caption("Sistema desarrollado para el monitoreo de inundaciones en Piura | © 2025")

