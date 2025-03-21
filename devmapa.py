import pandas as pd
import folium
from folium.plugins import HeatMap
import simplekml


arquivo_csv = "metro.csv"
df = pd.read_csv(arquivo_csv, encoding="ISO-8859-1", sep=";")

df.columns = df.columns.str.strip()

required_cols = {"LATITUDE", "LONGITUDE", "% DEV", "CLASSE", "PRODUTO", "CLIENTE", "BAIRRO", "CIDADE"}
if not required_cols.issubset(df.columns):
    raise ValueError(f"O CSV deve conter as colunas: {', '.join(required_cols)}")


df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")
df["% DEV"] = (
    df["% DEV"]
    .astype(str)
    .str.replace("%", "")
    .str.replace(",", ".")
)
df["% DEV"] = pd.to_numeric(df["% DEV"], errors="coerce")


df = df.dropna(subset=["LATITUDE", "LONGITUDE", "% DEV", "PRODUTO", "CLASSE"])


def weight_by_class(classe):
    classe = str(classe).strip().upper()
    if classe == "A":
        return 50000
    elif classe == "B":
        return 20000
    elif classe == "C":
        return 1000
    else:
        return 0

df["HEAT_PESO"] = df["CLASSE"].apply(weight_by_class)


def marker_color_by_percent(percent_dev):
    if percent_dev < 3:
        return "green"
    elif 3 <= percent_dev < 5:
        return "orange"
    else:
        return "red"


mapa = folium.Map(
    location=[df["LATITUDE"].mean(), df["LONGITUDE"].mean()],
    zoom_start=12
)


produtos = df["PRODUTO"].unique()
for produto in produtos:
    df_prod = df[df["PRODUTO"] == produto]
    grupo_produto = folium.FeatureGroup(name=f"Produto: {produto}")


    heat_data = df_prod[["LATITUDE", "LONGITUDE", "HEAT_PESO"]].values.tolist()


    HeatMap(
         heat_data,
    radius=35,
    blur=20,
    min_opacity=0.2,
    gradient= {
        "0.0": 'blue',
    "0.5": 'yellow',
    "1.0": 'red'}
       ).add_to(grupo_produto)

    for _, row in df_prod.iterrows():
        popup_text = f"""
        <b>Cliente:</b> {row['CLIENTE']}<br>
        <b>Bairro:</b> {row['BAIRRO']}<br>
        <b>Cidade:</b> {row['CIDADE']}<br>
        <b>Produto:</b> {row['PRODUTO']}<br>
        <b>% DEV:</b> {row['% DEV']}<br>
        <b>Classe:</b> {row['CLASSE']}
        """
        color = marker_color_by_percent(row["% DEV"])
        folium.Marker(
            location=[row["LATITUDE"], row["LONGITUDE"]],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f"{row['CLIENTE']} - {row['BAIRRO']} (% DEV: {row['% DEV']})",
            icon=folium.Icon(color=color)
        ).add_to(grupo_produto)

    grupo_produto.add_to(mapa)

folium.LayerControl().add_to(mapa)


legend_html = '''
<div style="
    position: fixed;
    bottom: 50px;
    left: 50px;
    width: 250px;
    /* Remova ou ajuste a linha abaixo */
    /* height: 120px; */
    background-color: white;
    border:2px solid grey;
    z-index:9999; 
    font-size:14px;
    padding: 10px;
">
 <b>MARCADORES 📌 </b><br>
    <span style="color:green;">🟢</span>  Devolução Menor que 3%<br>
    <span style="color:orange;">🟠</span> Devolução Entre 3% e 5%<br>
    <span style="color:red;">🔴</span>  Devolução Maior ou igual a 5%
    
    <br>CALOR 🦯<br>
    🛑= RENDA ALTA, 🟡 = RENDA MEDIA, 🔵 = RENDA BAIXA<br>
</div>
'''
mapa.get_root().html.add_child(folium.Element(legend_html))

# 9️⃣ Salvar o mapa como HTML
mapa.save("devolucao_custom.html")
print("Mapa salvo como 'devolucao_custom.html'.")
