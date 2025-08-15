import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="📊 Jugadores Biwenger", layout="wide")

st.title("📊 Jugadores Biwenger")

# URL de Dropbox: convierte enlace compartido en descarga directa
# Ejemplo: https://www.dropbox.com/s/xxxxxx/archivo.xlsx?dl=0  → cambiar dl=0 por dl=1
dropbox_url = "https://www.dropbox.com/scl/fi/pmu8u65lcmlcwpxhizw9l/clausulas_que_expiran_menos_48_h.xlsx?rlkey=xfbtdw10urjo71wkwh59rajrg&st=4hg404ew&dl=1"

@st.cache_data
def load_data(url):
    df = pd.read_excel(url)
    # Limpiar datos
    df["Valor Actual"] = df["Valor Actual"].replace({r'[^\d]': ''}, regex=True).astype(float)
    df["Fecha de Desbloqueo"] = pd.to_datetime(df["Fecha de Desbloqueo"], errors="coerce")
    return df

df = load_data(dropbox_url)

# Filtros
col1, col2 = st.columns(2)
propietarios = ["Todos"] + sorted(df["Propietario"].unique())
propietario_sel = col1.selectbox("Filtrar por propietario", propietarios)

if propietario_sel != "Todos":
    df = df[df["Propietario"] == propietario_sel]

# Tabla
st.subheader("📋 Tabla de jugadores")
st.dataframe(df.sort_values(by="Valor Actual", ascending=False))

# Gráfica de valores por jugador
st.subheader("💰 Valor actual por jugador")
fig_valor = px.bar(df, x="Nombre", y="Valor Actual", color="Propietario", 
                   title="Valor actual por jugador", 
                   text="Valor Actual")
st.plotly_chart(fig_valor, use_container_width=True)

# Gráfica de valor total por propietario
st.subheader("📈 Valor total por propietario")
valor_por_propietario = df.groupby("Propietario")["Valor Actual"].sum().reset_index()
fig_propietario = px.bar(valor_por_propietario, x="Propietario", y="Valor Actual", 
                         title="Valor total por propietario", 
                         text="Valor Actual")
st.plotly_chart(fig_propietario, use_container_width=True)
