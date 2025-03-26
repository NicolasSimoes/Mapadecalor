import pandas as pd
import folium
from folium.plugins import HeatMap
import simplekml
import json

# Carrega os dados
arquivo_csv = "tudo.csv"
df = pd.read_csv(arquivo_csv, encoding="ISO-8859-1", sep=";")
df.columns = df.columns.str.strip()

# Verifica se as colunas necessárias existem
required_cols = {"LATITUDE", "LONGITUDE", "% DEV", "CLASSE", "PRODUTO", "CLIENTE", "BAIRRO", "CIDADE", "VENDA"}
if not required_cols.issubset(df.columns):
    raise ValueError(f"O CSV deve conter as colunas: {', '.join(required_cols)}")

# Converte as colunas para os tipos corretos
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
    .str.replace(r"\.", "", regex=True)       # remove pontos (separador de milhar)
    .str.replace(",", ".")                    # troca vírgula por ponto
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

df = df.dropna(subset=["LATITUDE", "LONGITUDE", "% DEV", "PRODUTO", "CLASSE", "VENDA"])

# Função para definir o peso do HeatMap de acordo com a classe
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

# Função para definir a cor do marcador com base no % DEV
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
    width="100%",      # ocupa 100% da largura
    height="100vh"     # altura da viewport
)

# Adiciona a meta tag viewport para responsividade
meta_viewport = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
mapa.get_root().html.add_child(folium.Element(meta_viewport))

# Dicionário para armazenar a contagem de marcadores vermelhos por produto
red_counts = {}

# Adiciona os dados ao mapa, agrupando por produto
produtos = df["PRODUTO"].unique()
for produto in produtos:
    df_prod = df[df["PRODUTO"] == produto]
    layer_name = f"Produto: {produto}"
    
    # Cria o FeatureGroup para cada produto como overlay (desligado inicialmente)
    grupo_produto = folium.FeatureGroup(
        name=layer_name,
        show=False,
        overlay=True
    )
    grupo_produto.overlay = True  # força a ser overlay
    
    # Calcula a contagem de marcadores vermelhos para este produto
    red_counts[layer_name] = int(len(df_prod[( df_prod["% DEV"] >= 5)]))
    
    # Adiciona o HeatMap
    heat_data = df_prod[["LATITUDE", "LONGITUDE", "HEAT_PESO"]].values.tolist()
    HeatMap(
        heat_data,
        radius=35,
        blur=20,
        min_opacity=0.2,
        gradient={"0.0": 'blue', "0.5": 'yellow', "1.0": 'red'}
    ).add_to(grupo_produto)
    
    # Adiciona os marcadores
    for _, row in df_prod.iterrows():
        popup_text = f"""
        <b>Cliente:</b> {row['CLIENTE']}<br>
        <b>Bairro:</b> {row['BAIRRO']}<br>
        <b>Cidade:</b> {row['CIDADE']}<br>
        <b>Produto:</b> {row['PRODUTO']}<br>
        <b>Venda:</b> {row['VENDA']}<br>
        <b>% DEV:</b> {row['% DEV']}<br>
        <b>Classe:</b> {row['CLASSE']}
        """
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
    
    # Adiciona o grupo de marcadores para este produto ao mapa
    grupo_produto.add_to(mapa)

# Adiciona o controle de camadas **apenas uma vez** fora do loop
folium.LayerControl(collapsed=False).add_to(mapa)

# Legenda customizada
legend_html = '''
<style>
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
    <span style="color:gray;">⚫</span>  Sem Venda (cinza)<br>
    <br>CALOR 🦯<br>
    🛑= RENDA ALTA, 🟡 = RENDA MÉDIA, 🔵 = RENDA BAIXA<br>
</div>
'''
mapa.get_root().html.add_child(folium.Element(legend_html))

# Caixa fixa centralizada no topo para exibir a contagem de marcadores vermelhos
red_box_html = '''
<div id="redBox" style="
    position: fixed;
    top: 10px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999;
    background-color: rgba(255,255,255,0.8);
    padding: 10px;
    border: 2px solid red;
    border-radius: 5px;
    font-size: 16px;
    display: none;
">
<b>Marcadores Vermelhos:</b> 0
</div>
'''
mapa.get_root().html.add_child(folium.Element(red_box_html))

name = mapa.get_name()  # ex: map_b21181f301d219ba0ab19a951fd0d56c

js_code = f"""
<script>
document.addEventListener("DOMContentLoaded", function() {{
    var redCounts = {json.dumps(red_counts)};
    var totalRedCount = 0;

    function updateRedCount() {{
        document.getElementById("redBox").innerHTML = "<b>Marcadores Vermelhos:</b> " + totalRedCount;
    }}

    // O objeto Leaflet é diretamente o window.{name}
    var mapObject = window.{name};

    mapObject.on('overlayadd', function(e) {{
        if (redCounts.hasOwnProperty(e.name)) {{
            totalRedCount += redCounts[e.name];
            updateRedCount();
            document.getElementById("redBox").style.display = "block";
        }}
    }});

    mapObject.on('overlayremove', function(e) {{
        if (redCounts.hasOwnProperty(e.name)) {{
            totalRedCount -= redCounts[e.name];
            updateRedCount();
            if (totalRedCount <= 0) {{
                document.getElementById("redBox").style.display = "none";
            }}
        }}
    }});
}});
</script>
"""

mapa.get_root().html.add_child(folium.Element(js_code))
mapa.save("devolucao_custom.html")
print("salvo")
