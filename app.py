import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px

# Conectar a Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configurar la barra lateral
st.sidebar.title("📊 Configuración de Visualización")
visualizacion_tipo = st.sidebar.radio(
    "Selecciona qué datos visualizar:",
    ["Predicciones de Inundaciones", "Eventos Históricos", "Precipitaciones"]
)

# Guía rápida (tooltip)
st.sidebar.expander("ℹ️ Guía Rápida").write("""
- **Predicciones**: Riesgo calculado por modelo XGBoost.
- **Eventos Históricos**: Nivel de agua e impacto.
- **Precipitaciones**: Datos diarios en mm.
""")

st.title("🌊 Análisis de Inundaciones y Precipitaciones")

# Función para cargar datos
def cargar_datos(tabla):
    try:
        data = supabase.table(tabla).select("*").execute().data
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error cargando {tabla}: {e}")
        return pd.DataFrame()

# Cargar datos
df_predicciones = cargar_datos("fechas_riesgo_inundacion")
df_eventos = cargar_datos("eventos_inundacion")
df_precipitaciones = cargar_datos("precipitaciones")
df_estaciones = cargar_datos("estaciones")  # Para el mapa

# Convertir fechas a formato correcto
for df in [df_predicciones, df_eventos, df_precipitaciones]:
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

# Filtrar eventos sin fechas válidas
df_eventos = df_eventos.dropna(subset=["fecha"])

# --- CONTENIDO PRINCIPAL ---
if visualizacion_tipo == "Predicciones de Inundaciones":
    st.subheader("📈 Evolución del Riesgo de Inundación")
    if not df_predicciones.empty:
        # Métricas resumen
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total de días con riesgo", len(df_predicciones[df_predicciones["riesgo_inundacion"] > 0.5]))
        with col2:
            st.metric("Precipitación máxima registrada", f"{df_precipitaciones['pp'].max()} mm")
        
        # Gráfico de predicciones
        fig = px.line(df_predicciones, x="fecha", y="riesgo_inundacion", 
                      title="Riesgo de Inundación a lo largo del tiempo")
        st.plotly_chart(fig)

elif visualizacion_tipo == "Eventos Históricos":
    st.subheader("🌊 Eventos Históricos de Inundación")
    
    min_fecha = df_eventos["fecha"].min()
    max_fecha = df_eventos["fecha"].max()

    if pd.notnull(min_fecha) and pd.notnull(max_fecha):
        # Filtro de fechas
        fecha_seleccionada = st.sidebar.slider(
            "Selecciona un rango de fechas",
            min_value=min_fecha.to_pydatetime(),
            max_value=max_fecha.to_pydatetime(),
            value=(min_fecha.to_pydatetime(), max_fecha.to_pydatetime())
        )
        df_eventos_filtrado = df_eventos[
            (df_eventos["fecha"] >= fecha_seleccionada[0]) & 
            (df_eventos["fecha"] <= fecha_seleccionada[1])
        ]
        
        # Tabla y gráfico
        st.write("### Datos Filtrados")
        st.dataframe(df_eventos_filtrado)

        fig_eventos = px.histogram(df_eventos_filtrado, x="nivel_agua", nbins=20, 
                                  title="Distribución del Nivel de Agua en Eventos de Inundación")
        st.plotly_chart(fig_eventos)

        # Mapa de estaciones (si hay datos geo)
        if not df_estaciones.empty and "latitud" in df_estaciones.columns:
            st.write("### Mapa de Estaciones con Eventos Históricos")
            fig_mapa = px.scatter_mapbox(df_estaciones, lat="latitud", lon="longitud", 
                                       hover_name="nombre_estacion", zoom=10)
            fig_mapa.update_layout(mapbox_style="open-street-map")
            st.plotly_chart(fig_mapa)

elif visualizacion_tipo == "Precipitaciones":
    st.subheader("☔ Variación de Precipitación por Fecha")
    if not df_precipitaciones.empty:
        # Filtro de fechas
        min_fecha = df_precipitaciones["fecha"].min()
        max_fecha = df_precipitaciones["fecha"].max()
        fecha_seleccionada = st.sidebar.slider(
            "Selecciona rango de fechas (Precipitaciones)",
            min_value=min_fecha.to_pydatetime(),
            max_value=max_fecha.to_pydatetime(),
            value=(min_fecha.to_pydatetime(), max_fecha.to_pydatetime())
        )
        df_precip_filtrado = df_precipitaciones[
            (df_precipitaciones["fecha"] >= fecha_seleccionada[0]) & 
            (df_precipitaciones["fecha"] <= fecha_seleccionada[1])
        
        # Gráfico de precipitaciones
        fig_precipitaciones = px.line(df_precip_filtrado, x="fecha", y="pp", 
                                     title="Precipitaciones a lo largo del tiempo")
        st.plotly_chart(fig_precipitaciones)

        # Gráfico combinado con eventos (opcional)
        st.write("### Relación entre Precipitaciones y Eventos de Inundación")
        df_combinado = pd.merge(df_precip_filtrado, df_eventos, on="fecha", how="left")
        df_combinado["inundacion"] = df_combinado["nivel_agua"].apply(lambda x: 1 if not pd.isna(x) else 0)
        
        fig_combinado = px.line(df_combinado, x="fecha", y="pp", 
                               title="Precipitaciones vs Inundaciones")
        fig_combinado.add_scatter(x=df_combinado["fecha"], 
                                 y=df_combinado["inundacion"]*df_combinado["pp"].max(), 
                                 mode="markers", name="Inundaciones", marker_color="red")
        st.plotly_chart(fig_combinado)

