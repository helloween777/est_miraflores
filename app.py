import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px

# Conectar a Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📊 Visualización de Datos de Inundaciones y Precipitaciones")

# Función para cargar datos
def cargar_datos(tabla):
    try:
        data = supabase.table(tabla).select("*").execute().data
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error cargando {tabla}: {e}")
        return pd.DataFrame()

# Cargar datos
df_predicciones = cargar_datos("predicciones_inundacion")
df_eventos = cargar_datos("eventos_inundacion")
df_precipitaciones = cargar_datos("precipitaciones")

# Convertir fechas a formato correcto
df_predicciones["fecha"] = pd.to_datetime(df_predicciones["fecha"], errors="coerce")
df_eventos["fecha"] = pd.to_datetime(df_eventos["fecha"], errors="coerce")
df_precipitaciones["fecha"] = pd.to_datetime(df_precipitaciones["fecha"], errors="coerce")

# Filtrar eventos sin fechas válidas
df_eventos = df_eventos.dropna(subset=["fecha"])

# Mostrar métricas clave
st.subheader("📌 Indicadores clave")
col1, col2, col3 = st.columns(3)
col1.metric("Promedio Riesgo", f"{df_predicciones['riesgo_inundacion'].mean():.2f}")
col2.metric("Máximo Riesgo", f"{df_predicciones['riesgo_inundacion'].max():.2f}")
col3.metric("Mínimo Riesgo", f"{df_predicciones['riesgo_inundacion'].min():.2f}")

# Gráfico interactivo de evolución de riesgo
if not df_predicciones.empty:
    st.subheader("📈 Evolución del Riesgo de Inundación")
    fig = px.line(df_predicciones, x="fecha", y="riesgo_inundacion", title="Riesgo de Inundación a lo largo del tiempo")
    st.plotly_chart(fig)

# Filtro y visualización de eventos históricos
if not df_eventos.empty:
    st.subheader("🌊 Eventos Históricos de Inundación")
    
    # Manejo seguro de valores mínimos y máximos
    min_fecha = df_eventos["fecha"].min()
    max_fecha = df_eventos["fecha"].max()

    if pd.notnull(min_fecha) and pd.notnull(max_fecha):
        fecha_seleccionada = st.slider(
            "Selecciona un rango de fechas",
            min_value=min_fecha, max_value=max_fecha,
            value=(min_fecha, max_fecha)
        )
        df_eventos_filtrado = df_eventos[(df_eventos["fecha"] >= fecha_seleccionada[0]) & (df_eventos["fecha"] <= fecha_seleccionada[1])]
        
        st.write("### Datos Filtrados")
        st.dataframe(df_eventos_filtrado)

        # Gráfico de nivel de agua en eventos
        fig_eventos = px.histogram(df_eventos_filtrado, x="nivel_agua", nbins=20, title="Distribución del Nivel de Agua en Eventos de Inundación")
        st.plotly_chart(fig_eventos)
    else:
        st.warning("No hay valores válidos para el filtro de fechas en eventos.")

# Visualización de precipitaciones
if not df_precipitaciones.empty:
    st.subheader("☔ Variación de Precipitación por Fecha")
    fig_precipitaciones = px.line(df_precipitaciones, x="fecha", y="pp", title="Precipitaciones a lo largo del tiempo")
    st.plotly_chart(fig_precipitaciones)


