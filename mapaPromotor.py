import pandas as pd
import folium

# 1) Ler e preparar o DataFrame
df = pd.read_csv('PROMOTORESCLIENTES.csv', delimiter=';')

# Converter colunas de coordenadas para valores numéricos
df['LATITUDE CASA']   = pd.to_numeric(df['LATITUDE CASA'], errors='coerce')
df['LONGITUDE CASA']  = pd.to_numeric(df['LONGITUDE CASA'], errors='coerce')
df['LATITUDE']        = pd.to_numeric(df['LATITUDE'], errors='coerce')
df['LONGITUDE']       = pd.to_numeric(df['LONGITUDE'], errors='coerce')

# Filtra linhas que têm ao menos alguma informação de promotor
df = df.dropna(subset=['NOVO PROMOTOR'])

# 2) Identificar todos os promotores distintos
promotores = df['NOVO PROMOTOR'].unique()

# 3) Criar um mapa base, por exemplo, centralizado no Brasil
mapa = folium.Map(location=[-3.7424091, -38.4867581], zoom_start=13)

# 4) Para cada promotor, cria uma FeatureGroup (camada)
for promotor in promotores:
    # Filtra somente as linhas desse promotor com dados válidos
    df_promotor = df[
        (df['NOVO PROMOTOR'] == promotor) &
        (df['LATITUDE CASA'].notna()) &
        (df['LONGITUDE CASA'].notna()) &
        (df['LATITUDE'].notna()) &
        (df['LONGITUDE'].notna())
    ]
    
    if df_promotor.empty:
        continue  # pula se não há dados válidos

    # Pegamos a primeira linha para achar a casa do promotor
    casa_row = df_promotor.iloc[0]
    casa_coords = [casa_row['LATITUDE CASA'], casa_row['LONGITUDE CASA']]
    
    # Criamos um FeatureGroup para esse promotor
    fg = folium.FeatureGroup(name=f"Promotor {promotor}",show=False)
    
    # Adicionamos o marcador da casa do promotor
    folium.Marker(
        location=casa_coords,
        popup=f"Casa do Promotor {promotor}",
        icon=folium.Icon(color='blue')
    ).add_to(fg)
    
    # Criamos a rota (lista de pontos) começando pela casa
    rota = [casa_coords]
    
    # Percorre cada linha para criar marcadores dos clientes
    for idx, row in df_promotor.iterrows():
        coords_cliente = [row['LATITUDE'], row['LONGITUDE']]
        folium.Marker(
            location=coords_cliente,
            popup=row['NOME FANTASIA'],
            icon=folium.Icon(color='red')
        ).add_to(fg)
        rota.append(coords_cliente)
    
    # Desenha a rota se houver pelo menos dois pontos
    if len(rota) > 1:
        folium.PolyLine(rota, color='green', weight=2.5).add_to(fg)
    
    # Adiciona o FeatureGroup ao mapa
    fg.add_to(mapa)

# 5) Adiciona o controle de camadas
folium.LayerControl().add_to(mapa)

# 6) Salva o resultado em HTML
mapa.save("mapa_promotores.html")
print("salvo")