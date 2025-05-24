import streamlit as st
from supabase import create_client
import pandas as pd
import matplotlib.pyplot as plt

# Conectar a Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("Visualización de Datos de Inundaciones y Precipitaciones")

# Cargar datos desde Supabase
def cargar_datos(tabla):
    try:
        data = supabase.table(tabla).select("*").execute().data
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error cargando {tabla}: {e}")
        return pd.DataFrame()

df_predicciones = cargar_datos("predicciones_inundacion")
df_eventos = cargar_datos("eventos_inundacion")
df_precipitaciones = cargar_datos("precipitaciones")

# Mostrar datos de predicciones
if not df_predicciones.empty:
    st.write("### Predicciones registradas")
    st.dataframe(df_predicciones)

    df_predicciones["fecha"] = pd.to_datetime(df_predicciones["fecha"])

    # Gráficos de evolución
    st.subheader("Evolución del riesgo de inundación")
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
    df_precipitaciones["fecha"] = pd.to_datetime(df_precipitaciones["fecha"])
    precipitaciones_por_fecha = df_precipitaciones.groupby("fecha")["pp"].mean().reset_index()
    st.line_chart(precipitaciones_por_fecha, x="fecha", y="pp")




