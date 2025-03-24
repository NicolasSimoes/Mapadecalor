import pandas as pd
import folium
from folium.plugins import HeatMap
import simplekml


arquivo_csv = "tudo.csv"
df = pd.read_csv(arquivo_csv, encoding="ISO-8859-1", sep=";")

df.columns = df.columns.str.strip()

required_cols = {"LATITUDE", "LONGITUDE", "% DEV", "CLASSE", "PRODUTO", "CLIENTE", "BAIRRO", "CIDADE","VENDA","DEVOLUCAO"}
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

df["VENDA"] = (
    df["VENDA"]
    .astype(str)
    .str.replace(r"R\$\s*", "", regex=True)  # remove "R$ "
    .str.replace(r"\.", "", regex=True)      # remove pontos (separador de milhar)
    .str.replace(",", ".")                   # troca vírgula por ponto
)
df["VENDA"] = pd.to_numeric(df["VENDA"], errors="coerce").fillna(0)

df["DEVOLUCAO"] = (
    df["DEVOLUCAO"]
    .astype(str)
    .str.replace(r"R\$\s*", "", regex=True)  # remove "R$ "
    .str.replace(r"\.", "", regex=True)      # remove pontos (separador de milhar)
    .str.replace(",", ".")                   # troca vírgula por ponto
)
df["DEVOLUCAO"] = pd.to_numeric(df["DEVOLUCAO"], errors="coerce").fillna(0)


df = df.dropna(subset=["LATITUDE", "LONGITUDE", "% DEV", "PRODUTO", "CLASSE", "VENDA", "DEVOLUCAO", "CODIGO"])


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


# Cria o mapa com tamanho responsivo
mapa = folium.Map(
    location=[df["LATITUDE"].mean(), df["LONGITUDE"].mean()],
    zoom_start=12,
    width="100%",      # utiliza 100% da largura disponível
    height="100vh"     # altura ajustada para 100% da viewport
)

# Adiciona a meta tag viewport para responsividade em dispositivos móveis
meta_viewport = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
mapa.get_root().html.add_child(folium.Element(meta_viewport))


produtos = df["PRODUTO"].unique()
for produto in produtos:
    df_prod = df[df["PRODUTO"] == produto]
    grupo_produto = folium.FeatureGroup(name=f"Produto: {produto}", show=False)


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
        <b>Código:</b> {row['CODIGO']}<br>
        <b>Bairro:</b> {row['BAIRRO']}<br>
        <b>Cidade:</b> {row['CIDADE']}<br>
        <b>Produto:</b> {row['PRODUTO']}<br>
         <b>Venda:</b> {row['VENDA']}<br>
        <b>% DEV:</b> {row['% DEV']}<br>
        <b>Classe:</b> {row['CLASSE']}
        """
         # Se VENDA == 0, marcador cinza; caso contrário, cor pelo % DEV
        if row["VENDA"] == 0 and row["DEVOLUCAO"] == 0:
            color = "gray"
        else:
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
<style>
  /* Ajustes de estilo para telas menores */
  @media (max-width: 600px) {
    .legend {
      width: 180px !important;
      font-size: 12px !important;
      left: 10px !important;
      bottom: 10px !important;
      padding: 5px !important;
    }
  }
</style>
<div class="legend" style="
    position: fixed;
    bottom: 50px;
    left: 50px;
    width: 250px;
    background-color: white;
    border:2px solid grey;
    z-index:9999; 
    font-size:14px;
    padding: 10px;
">
 <b>MARCADORES</b><br>
    <span style="color:green;">🟢</span>  Devolução Menor que 3%<br>
    <span style="color:orange;">🟠</span> Devolução Entre 3% e 5%<br>
    <span style="color:red;">🔴</span>  Devolução Maior ou igual a 5%<br>
    <span style="color:gray;">⚫</span>  Sem Venda  (cinza)<br>
    
    <br>CALOR 🦯<br>
    🛑= RENDA ALTA, 🟡 = RENDA MÉDIA, 🔵 = RENDA BAIXA<br>
</div>
'''
mapa.get_root().html.add_child(folium.Element(legend_html))

# 9️⃣ Salvar o mapa como HTML
mapa.save("devolucao_custom.html")
print("Mapa salvo como 'devolucao_custom.html'.")
