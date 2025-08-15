import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configuración de página ---
st.set_page_config(page_title="📊 Jugadores Biwenger", layout="wide")
st.title("📊 Jugadores Biwenger")

# --- URL de Dropbox ---
dropbox_url = "https://www.dropbox.com/scl/fi/33v549k09ypevy7re3fbj/jugadores_biwenger.csv?rlkey=hafbwd6i04yloigclnnv1oe0f&st=3aq68ntm&dl=1"

@st.cache_data
def load_data(url):
    df = pd.read_csv(url)
    df["Valor Actual"] = df["Valor Actual"].replace({r'[^\d]': ''}, regex=True).astype(float)
    df["Fecha de Desbloqueo"] = pd.to_datetime(df["Fecha de Desbloqueo"], errors="coerce")
    df["Horas"] = df["Horas"].astype(int)
    df["Minutos"] = df["Minutos"].astype(int)
    df["Tiempo restante (h)"] = df["Horas"] + df["Minutos"]/60
    return df

df = load_data(dropbox_url)

# --- Crear pestañas ---
tab1, tab2 = st.tabs(["📋 Cláusulas <48h", "📊 Estadísticas y gráficos"])

with tab1:
    st.subheader("Filtros de jugadores con cláusula")

    # --- Filtros dentro de la pestaña ---
    propietarios = ["Todos"] + sorted(df["Propietario"].unique())
    propietario_sel = st.selectbox("Filtrar por propietario", propietarios)
    
    posiciones = ["Todos"] + sorted(df["Posición"].dropna().unique())
    posicion_sel = st.selectbox("Filtrar por posición", posiciones)
    
    tiempo_max = st.slider("Tiempo máximo restante (horas)", 0, 48, 48)

    # --- Aplicar filtros ---
    df_filtrado = df[df["Tiempo restante (h)"] <= tiempo_max]
    if propietario_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Propietario"] == propietario_sel]
    if posicion_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Posición"] == posicion_sel]

    # --- Crear columna HTML para las imágenes ---
    image_width = 60
    df_filtrado['Foto'] = df_filtrado['Enlace_imagen'].apply(
        lambda url: f'<img src="{url}" width="{image_width}">'
    )

    # --- Ordenar columnas para mostrar ---
    cols_mostrar = ['Foto', 'Nombre', 'Equipo', 'Posición', 'Propietario', 'Valor Actual', 'Puntos', 'Horas', 'Minutos', 'Fecha de Desbloqueo']
    df_tabla = df_filtrado[cols_mostrar]

    st.subheader(f"Jugadores con cláusula <{tiempo_max}h")
    st.write(df_tabla.to_html(escape=False, index=False), unsafe_allow_html=True)

with tab2:
    st.subheader("💰 Valor total por propietario")
    valor_por_propietario = df.groupby("Propietario")["Valor Actual"].sum().reset_index()
    fig_valor_prop = px.bar(valor_por_propietario, x="Propietario", y="Valor Actual",
                            text="Valor Actual", color="Propietario",
                            title="Valor total de jugadores por propietario")
    st.plotly_chart(fig_valor_prop, use_container_width=True)

    st.subheader("📈 Valor total por equipo")
    valor_por_equipo = df.groupby("Equipo")["Valor Actual"].sum().reset_index()
    fig_valor_equipo = px.bar(valor_por_equipo, x="Equipo", y="Valor Actual",
                              text="Valor Actual", color="Equipo",
                              title="Valor total de jugadores por equipo")
    st.plotly_chart(fig_valor_equipo, use_container_width=True)

    st.subheader("🏆 Top 10 jugadores por valor")
    top_jugadores = df.sort_values(by="Valor Actual", ascending=False).head(10)
    st.dataframe(top_jugadores[["Nombre","Equipo","Propietario","Valor Actual","Puntos"]])

    st.subheader("📊 Estadísticas generales")
    st.write(f"**Total de jugadores:** {len(df)}")
    st.write(f"**Total de propietarios:** {df['Propietario'].nunique()}")
    st.write(f"**Jugador más caro:** {df.loc[df['Valor Actual'].idxmax(),'Nombre']} ({df['Valor Actual'].max():,.0f} €)")
    st.write(f"**Jugador más barato:** {df.loc[df['Valor Actual'].idxmin(),'Nombre']} ({df['Valor Actual'].min():,.0f} €)")
