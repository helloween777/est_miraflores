import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import pydeck as pdk
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np



# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Sistema de Inundaciones - Piura", 
    layout="wide",
    page_icon="🌊"
)

# --- CONEXIÓN SUPABASE ---
@st.cache_resource
def init_connection():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

supabase = init_connection()

# --- CARGA DE DATOS ---
@st.cache_data(ttl=600)
def load_data(table_name):
    try:
        response = supabase.table(table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            df.dropna(subset=['fecha'], inplace=True)
        return df
    except Exception as e:
        st.error(f"Error cargando {table_name}: {e}")
        return pd.DataFrame()

# Cargar las 5 tablas
df_estaciones = load_data("estaciones")
df_eventos = load_data("eventos_inundacion")
df_predicciones = load_data("fechas_riesgo_inundacion")
df_precipitaciones = load_data("precipitaciones")
df_puntos = load_data("puntos_inundacion")

# --- VERIFICACIÓN DE COORDENADAS ESTACIONES ---
def verify_coordinates():
    if not df_estaciones.empty:
        for col in ['latitud', 'longitud']:
            if col not in df_estaciones.columns:
                st.error(f"La tabla 'estaciones' no tiene la columna '{col}'")
                st.stop()

verify_coordinates()

# --- MAPA DE ESTACIONES ---
def show_map():
    st.subheader(" Mapa de Estaciones Meteorológicas")
    df_map = df_estaciones.copy()
    df_map['color'] = df_map['nombre_estacion'].apply(lambda x: "red" if "Miraflores" in str(x) else "blue")
    fig = px.scatter_mapbox(
        df_map,
        lat="latitud",
        lon="longitud",
        hover_name="nombre_estacion",
        color="color",
        zoom=12,
        height=600,
        color_discrete_map={"red": "red", "blue": "blue"}
    )
    fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("📋 Ver datos completos de estaciones"):
        st.dataframe(df_estaciones)

# --- MAPA DE CALOR DE RIESGO ---
def show_heatmap():
    st.subheader("Mapa de Calor del Riesgo de Inundación (Ene–Abr)")

    if not df_predicciones.empty and not df_puntos.empty:
        # Agrupamos riesgo por punto (promedio por punto en los primeros meses)
        df_riesgo_prom = (
            df_predicciones
            .groupby("id_punto", as_index=False)["riesgo_inundacion"]
            .mean()
            .rename(columns={"riesgo_inundacion": "riesgo_promedio"})
        )

        # Merge completo con todos los puntos (para asegurar que estén todos)
        df_map = df_puntos.merge(df_riesgo_prom, on="id_punto", how="left")

        # Rellenar los riesgos faltantes con 0 para visualización
        df_map["riesgo_promedio"] = df_map["riesgo_promedio"].fillna(0)
        
        # Asegurar tipo numérico
        df_map["latitud"] = pd.to_numeric(df_map["latitud"], errors="coerce")
        df_map["longitud"] = pd.to_numeric(df_map["longitud"], errors="coerce")

        # Mapa de calor
        heat_layer = pdk.Layer(
            "HeatmapLayer",
            data=df_map,
            get_position='[longitud, latitud]',
            get_weight="riesgo_promedio",
            radiusPixels=60,
        )

        # Marcadores en los puntos
        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_map,
            get_position='[longitud, latitud]',
            get_radius=100,
            get_fill_color='[255, 100, 0, 180]'
        )

        # Vista del mapa
        view_state = pdk.ViewState(
            latitude=df_map["latitud"].mean(),
            longitude=df_map["longitud"].mean(),
            zoom=12,
            pitch=40
        )

        # Mostrar el mapa
        st.pydeck_chart(pdk.Deck(
            layers=[heat_layer, scatter_layer],
            initial_view_state=view_state,
            tooltip={"text": "{nombre_punto}\nRiesgo: {riesgo_promedio}"}
        ))

        # Mostrar tabla con riesgos
        with st.expander("Tabla de Riesgos Promedio por Zona"):
            st.dataframe(df_map[["nombre_punto", "riesgo_promedio"]].sort_values("riesgo_promedio", ascending=False))
    else:
        st.warning("No hay datos suficientes para mostrar el mapa de calor.")


# --- PREDICCIONES ---
def show_predictions():
    st.subheader("Predicciones de Inundación")
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
            title="Evolución del Riesgo de Inundación",
            labels={'riesgo_inundacion': 'Riesgo (0-1)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos de predicción disponibles.")

# --- PUNTOS DE INUNDACIÓN ---
def show_risk_points():
    st.subheader("Puntos de Inundación")
    if not df_puntos.empty:
        if {'latitud', 'longitud'}.issubset(df_puntos.columns):
            fig = px.scatter_mapbox(
                df_puntos,
                lat="latitud",
                lon="longitud",
                hover_name="nombre_punto" if "nombre_punto" in df_puntos.columns else "id_punto",
                zoom=12,
                color_discrete_sequence=["orange"],
                height=600
            )
            fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_puntos)
    else:
        st.warning("No hay puntos de inundación registrados.")

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
    st.subheader("Precipitaciones")
    if not df_precipitaciones.empty:
        if "pp" not in df_precipitaciones.columns:
            st.error("Falta la columna 'pp' en la tabla de precipitaciones.")
            return
        fig1 = px.line(df_precipitaciones, x="fecha", y="pp", title="Precipitación Diaria")
        st.plotly_chart(fig1, use_container_width=True)

        if "tmax" in df_precipitaciones.columns:
            fig2 = px.scatter(
                df_precipitaciones.dropna(subset=['pp', 'tmax']),
                x="tmax",
                y="pp",
                trendline="lowess",
                labels={"pp": "Precipitación (mm)", "tmax": "Temperatura Máxima (°C)"},
                title="Relación Precipitación vs Temperatura Máxima"
            )
            st.plotly_chart(fig2, use_container_width=True)

        with st.expander("📊 Estadísticas mensuales"):
            df_mensual = df_precipitaciones.set_index('fecha').resample('M').agg({
                'pp': 'sum',
                'tmax': 'mean' if 'tmax' in df_precipitaciones.columns else None
            }).reset_index()
            st.dataframe(df_mensual)
    else:
        st.warning("No hay datos de precipitaciones.")

# -----ENTRENAMIENTO DEL MODELO------

from scipy.spatial import cKDTree

def show_model_training():
    st.subheader("Entrenamiento del Modelo de Predicción de Inundaciones (Random Forest)")

    # Validaciones iniciales
    if df_predicciones.empty or df_puntos.empty or df_precipitaciones.empty or df_estaciones.empty:
        st.warning("Faltan datos para entrenar el modelo.")
        return

    # Copias locales para evitar modificar originales
    df_model = df_predicciones.copy()
    puntos = df_puntos.copy()
    estaciones = df_estaciones.copy()
    precip = df_precipitaciones.copy()

    # Normalizar nombres de columnas
    for df in [df_model, puntos, estaciones, precip]:
        df.columns = df.columns.str.strip().str.lower()

    # Asegurar columnas necesarias
    for df, cols, name in [
        (puntos, {"latitud", "longitud"}, "puntos_inundacion"),
        (estaciones, {"latitud", "longitud"}, "estaciones"),
        (precip, {"id_estacion", "fecha", "pp"}, "precipitaciones"),
        (df_model, {"id_punto", "fecha", "riesgo_inundacion"}, "predicciones")
    ]:
        missing = cols - set(df.columns)
        if missing:
            st.error(f" Faltan columnas en {name}: {', '.join(missing)}")
            return

    # Emparejar cada punto con la estación más cercana
    estaciones_coords = estaciones[["latitud", "longitud"]].values
    puntos_coords = puntos[["latitud", "longitud"]].values
    tree = cKDTree(estaciones_coords)
    _, indices = tree.query(puntos_coords, k=1)
    puntos["id_estacion"] = estaciones.iloc[indices]["id_estacion"].values

    # Merge de predicciones con puntos y luego con precipitaciones
    df_model = df_model.merge(puntos[["id_punto", "latitud", "longitud", "id_estacion"]],
                              on="id_punto", how="left")
    df_model = df_model.merge(precip[["id_estacion", "fecha", "pp"]],
                              on=["id_estacion", "fecha"], how="left")

    # Validar columnas finales necesarias
    required_cols = ["riesgo_inundacion", "pp", "latitud", "longitud"]
    for col in required_cols:
        df_model[col] = pd.to_numeric(df_model[col], errors="coerce")
    df_model.dropna(subset=required_cols, inplace=True)

    if df_model.empty:
        st.error("No hay datos suficientes para entrenar el modelo.")
        return

    # Variables predictoras y objetivo
    X = df_model[["pp", "latitud", "longitud"]]
    y = df_model["riesgo_inundacion"]

    # Entrenamiento
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestRegressor(random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    # Métricas
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    st.success("Evaluación inicial del modelo")
    st.write(f"**RMSE:** {rmse:.4f}")
    st.write(f"**R² Score:** {r2:.4f}")

    # Validación cruzada
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="neg_mean_squared_error")
    st.info(f"**Validación cruzada (RMSE promedio):** {np.sqrt(-cv_scores.mean()):.4f}")

    # Sesgo-Varianza
    y_train_pred = model.predict(X_train)
    train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
    st.write("Análisis de Sesgo-Varianza")
    st.write(f"- Train RMSE: {train_rmse:.4f}")
    st.write(f"- Test RMSE: {rmse:.4f}")

    # Optimización
    st.write("Buscando mejores hiperparámetros con GridSearch...")
    param_grid = {
        "n_estimators": [100, 200],
        "max_depth": [5, 10, None],
        "min_samples_split": [2, 5]
    }

    grid = GridSearchCV(RandomForestRegressor(random_state=42), param_grid, cv=3, scoring="neg_mean_squared_error")
    grid.fit(X, y)

    st.success("Modelo optimizado:")
    st.write(grid.best_params_)

    best_model = grid.best_estimator_
    importancias = pd.Series(best_model.feature_importances_, index=X.columns)
    st.write("📊 Importancia de variables")
    st.bar_chart(importancias.sort_values(ascending=True))











# --- INTERFAZ PRINCIPAL ---
st.title("Sistema de Monitoreo de Inundaciones - Piura")

# Menú lateral
option = st.sidebar.radio(
    "Seleccione una vista:",
    ["Mapa", "Predicciones", "Histórico", "Precipitaciones", "Puntos de Inundación", "Mapa de Calor", "Entrenamiento de Modelo"],
    index=0
)


# Vista seleccionada
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
elif option == "Mapa de Calor":
    show_heatmap()
elif option == "Entrenamiento de Modelo":
    show_model_training()


# Footer
st.markdown("---")
st.caption("Sistema desarrollado para el monitoreo de inundaciones en Piura | © 2025")



