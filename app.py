import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Monitoreo Miraflores - Piura", 
    layout="wide",
    page_icon="🌧️"
)

# --- CONEXIÓN SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        supabase = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"]
        )
        return supabase
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
        st.stop()

supabase = init_connection()

# --- FUNCIÓN PARA CARGAR DATOS ---
@st.cache_data(ttl=600)
def load_data(table_name):
    try:
        response = supabase.table(table_name).select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error cargando {table_name}: {str(e)}")
        return pd.DataFrame()

# --- VERIFICACIÓN DE ESTRUCTURA DE TABLAS ---
def check_table_structure():
    df_estaciones = load_data("estaciones")
    
    required_columns = {
        'estaciones': ['id_estacion', 'nombre_estacion', 'latitud', 'longitud'],
        'eventos_inundacion': ['id_evento', 'fecha', 'nivel_agua'],
        'precipitaciones': ['fecha', 'pp']
    }
    
    for table, columns in required_columns.items():
        df = load_data(table)
        missing = [col for col in columns if col not in df.columns]
        if missing:
            st.error(f"Tabla '{table}' falta columnas: {', '.join(missing)}")
            st.stop()

check_table_structure()

# --- MAPA INTERACTIVO ---
def show_map():
    st.subheader("📍 Mapa de la Estación Miraflores")
    
    df = load_data("estaciones")
    miraflores = df[df['nombre_estacion'].str.contains('Miraflores', case=False)]
    
    if miraflores.empty:
        st.warning("No se encontró la estación Miraflores")
        return
    
    # Configuración del mapa centrado en Miraflores
    fig = px.scatter_mapbox(
        miraflores,
        lat="latitud",
        lon="longitud",
        hover_name="nombre_estacion",
        hover_data=["latitud", "longitud"],
        zoom=15,
        height=600,
        color_discrete_sequence=["red"]
    )
    
    fig.update_layout(
        mapbox_style="open-street-map",
        margin={"r":0,"t":0,"l":0,"b":0},
        mapbox_center={
            "lat": float(miraflores.iloc[0]['latitud']),
            "lon": float(miraflores.iloc[0]['longitud'])
        }
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Mostrar datos técnicos
    with st.expander("📊 Datos técnicos de la estación"):
        st.dataframe(miraflores)

# --- INTERFAZ PRINCIPAL ---
st.title("🌊 Monitoreo Hidrometeorológico - Estación Miraflores")

tab1, tab2, tab3 = st.tabs(["Mapa", "Datos Históricos", "Precipitaciones"])

with tab1:
    show_map()

with tab2:
    st.subheader("📅 Eventos Históricos")
    df_eventos = load_data("eventos_inundacion")
    
    if not df_eventos.empty:
        df_eventos['fecha'] = pd.to_datetime(df_eventos['fecha'])
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            fecha_min = df_eventos['fecha'].min().to_pydatetime()
            fecha_max = df_eventos['fecha'].max().to_pydatetime()
            rango_fechas = st.date_input(
                "Rango de fechas",
                value=(fecha_min, fecha_max),
                min_value=fecha_min,
                max_value=fecha_max
            )
        
        # Aplicar filtros
        if len(rango_fechas) == 2:
            filtered = df_eventos[
                (df_eventos['fecha'] >= pd.to_datetime(rango_fechas[0])) & 
                (df_eventos['fecha'] <= pd.to_datetime(rango_fechas[1]))
            ]
            st.dataframe(filtered.sort_values('fecha', ascending=False))
        else:
            st.warning("Seleccione un rango de fechas válido")
    else:
        st.warning("No hay datos históricos disponibles")

with tab3:
    st.subheader("☔ Precipitaciones")
    df_lluvia = load_data("precipitaciones")
    
    if not df_lluvia.empty:
        df_lluvia['fecha'] = pd.to_datetime(df_lluvia['fecha'])
        
        # Gráfico anual
        st.write("### Acumulado Anual")
        df_anual = df_lluvia.set_index('fecha').resample('Y')['pp'].sum().reset_index()
        df_anual['año'] = df_anual['fecha'].dt.year
        fig1 = px.bar(df_anual, x='año', y='pp', labels={'pp': 'Precipitación (mm)'})
        st.plotly_chart(fig1, use_container_width=True)
        
        # Gráfico mensual
        st.write("### Variación Mensual")
        df_mensual = df_lluvia.set_index('fecha').resample('M')['pp'].sum().reset_index()
        df_mensual['mes'] = df_mensual['fecha'].dt.strftime('%Y-%m')
        fig2 = px.line(df_mensual, x='mes', y='pp', labels={'pp': 'Precipitación (mm)'})
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("No hay datos de precipitación")

# --- FOOTER ---
st.markdown("---")
st.caption("Sistema desarrollado para el monitoreo de la estación Miraflores, Piura | Datos actualizados a 2023")

