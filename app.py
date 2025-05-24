import streamlit as st
from supabase import create_client
import pandas as pd
import matplotlib.pyplot as plt

# Conexión a Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Cargar datos desde Supabase
@st.cache_data
def cargar_predicciones():
    try:
        data = supabase.table("predicciones_inundacion").select("id_punto, fecha, riesgo_inundacion").execute()
        return pd.DataFrame(data.data)
    except Exception as e:
        st.error(f"Error cargando predicciones: {e}")
        return pd.DataFrame()

@st.cache_data
def cargar_eventos():
    try:
        data = supabase.table("eventos_inundacion").select("id_punto, fecha, nivel_agua, impacto").execute()
        return pd.DataFrame(data.data)
    except Exception as e:
        st.error(f"Error cargando eventos: {e}")
        return pd.DataFrame()

@st.cache_data
def cargar_puntos():
    try:
        data = supabase.table("puntos_inundacion").select("id_punto, nombre_punto, latitud, longitud").execute()
        return pd.DataFrame(data.data)
    except Exception as e:
        st.error(f"Error cargando puntos de inundación: {e}")
        return pd.DataFrame()

@st.cache_data
def cargar_precipitaciones():
    try:
        data = supabase.table("precipitaciones").select("id_estacion, fecha, pp, tmax, tmin").execute()
        return pd.DataFrame(data.data)
    except Exception as e:
        st.error(f"Error cargando precipitaciones: {e}")
        return pd.DataFrame()

# Cargar y mostrar los datos
df_predicciones = cargar_predicciones()
df_eventos = cargar_eventos()
df_puntos = cargar_puntos()
df_precipitaciones = cargar_precipitaciones()

st.title("Visualización de Datos de Inundaciones y Precipitaciones")

# Mostrar datos de predicciones
if not df_predicciones.empty:
    st.write("### Predicciones registradas")
    st.dataframe(df_predicciones)

    df_predicciones["fecha"] = pd.to_datetime(df_predicciones["fecha"])

    # Métricas clave
    st.subheader("Estadísticas de Riesgo de Inundación")
    riesgo_promedio = df_predicciones["riesgo_inundacion"].mean()
    riesgo_maximo = df_predicciones["riesgo_inundacion"].max()
    riesgo_minimo = df_predicciones["riesgo_inundacion"].min()

    col1, col2, col3 = st.columns(3)
    col1.metric("Riesgo Promedio", f"{riesgo_promedio:.2f}")
    col2.metric("Máximo Riesgo", f"{riesgo_maximo:.2f}")
    col3.metric("Mínimo Riesgo", f"{riesgo_minimo:.2f}")

    # Gráfico de riesgo por fecha
    st.subheader("Riesgo promedio por fecha")
    riesgo_por_fecha = df_predicciones.groupby("fecha")["riesgo_inundacion"].mean().reset_index()
    st.line_chart(riesgo_por_fecha, x="fecha", y="riesgo_inundacion")

# Mostrar datos de eventos
if not df_eventos.empty:
    st.write("### Eventos históricos de inundación")
    st.dataframe(df_eventos)

    # Histograma de niveles de agua
    st.subheader("Distribución del nivel de agua en eventos de inundación")
    fig, ax = plt.subplots()
    df_eventos["nivel_agua"].hist(bins=10, ax=ax, color='blue', edgecolor='black')
    ax.set_xlabel("Nivel de Agua")
    ax.set_ylabel("Frecuencia")
    st.pyplot(fig)

# Mostrar datos de precipitaciones
if not df_precipitaciones.empty:
    st.write("### Registros de precipitaciones")
    st.dataframe(df_precipitaciones)

    # Gráfico de variación de precipitaciones por fecha
    st.subheader("Variación de precipitación por fecha")
    precipitaciones_por_fecha = df_precipitaciones.groupby("fecha")["pp"].mean().reset_index()
    st.line_chart(precipitaciones_por_fecha, x="fecha", y="pp")

# Opcional: Agregar más funcionalidades como mapas interactivos o filtros




