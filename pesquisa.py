import base64
import json

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title=f"Dados Em FOCO! - Pesquisa", page_icon="bar_chart", layout="wide")
st.title('Pesquisa de Preços 💰')

col1, col2 = st.columns(2)

# Adicionar texto personalizado acima do botão de upload
col1.markdown("""
### Carregue arquivo EXCEL com códigos de barras:
**ATENÇÃO PARA OS PONTOS ABAIXO:**

**-Lembre-se de nomear coluna com EANS de "git";**

**-Limite de 500 linhas por arquivo • XLSX.**
""")

uploaded_file = col1.file_uploader("", type=["xlsx"])

if uploaded_file is not None:
    # Ler o arquivo EXCEL
    df = pd.read_excel(uploaded_file, dtype={'gtin': str})
    
    # Lista para armazenar todos os dados coletados
    all_data = []

    # URL base da API
    base_url = "http://api.sefaz.al.gov.br/sfz-economiza-alagoas-api/api/public/produto/pesquisa"

    # Token de acesso fornecido pela SEFAZ/AL
    app_token = "e58ba7b6df2c658d6f9c47768053b79a8b540678"

    # Construindo o cabeçalho da requisição
    headers = {
        "AppToken": app_token,
        "Content-Type": "application/json"
    }

    # Iterar sobre cada código EAN no DataFrame
    for title in df['gtin']:
        body_data = {
            "produto": {
                "gtin": title
            },
            "estabelecimento": {
                "geolocalizacao": {
                    "latitude": -9.568061100000001,
                    "longitude": -35.79424830000001,
                    "raio": 15
                }
            },
            "dias": 7,
            "pagina": 1,
            "registrosPorPagina": 500
        }

        json_data = json.dumps(body_data)
        response = requests.post(base_url, headers=headers, data=json_data)

        # Verifica se a resposta é bem-sucedida
        if response.status_code == 200:
            response_data = response.json()
            try:
                conteudo = response_data['conteudo']
                all_data.extend(conteudo)
            except KeyError:
                st.warning(f"Não foi possível obter dados para código: {title}")
        else:
            st.error(f"Erro ao consultar API para código: {title}. Status Code: {response.status_code}")

    # Criar DataFrame com todos os dados coletados
    df_vendas = pd.json_normalize(all_data)
    
    # Converter a coluna 'produto.venda.valorVenda' para numérica
    df_vendas['produto.venda.valorVenda'] = pd.to_numeric(df_vendas['produto.venda.valorVenda'], errors='coerce')

    df_grouped1 = None
    df_grouped2 = None

    # Compartilhar a lógica para evitar duplicação
    def export_excel(df, file_name):
        with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        with open(file_name, 'rb') as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{file_name}">Download {file_name}</a>'
            st.markdown(href, unsafe_allow_html=True)

    # Seu código de filtragem e agrupamento aqui...

    if st.checkbox('Filtrar grandes Redes', True):
        grandes_redes = ['EMPREENDIMENTOS PAGUE MENOS S/A', 'RAIA DROGASIL S/A']
        df_vendas_filtered1 = df_vendas[df_vendas['estabelecimento.razaoSocial'].isin(grandes_redes)]
        df_grouped1 = df_vendas_filtered1.groupby(['produto.gtin', 'estabelecimento.razaoSocial']).agg(
            precoMinimo=('produto.venda.valorVenda', 'min'),
            precoMaximo=('produto.venda.valorVenda', 'max'),
            precoMedio=('produto.venda.valorVenda', 'mean'),
            precoModa=('produto.venda.valorVenda', lambda x: x.mode().iloc[0] if not x.mode().empty else None)
        ).reset_index()

    if st.checkbox('Filtrar Trabalhador de Alagoas', True):
        trabalhador = 'FARMACIA DO TRABALHADOR DE ALAGOAS'
        df_vendas_filtered2 = df_vendas[df_vendas['estabelecimento.nomeFantasia'] == trabalhador]
        df_vendas_filtered2.loc[:, 'estabelecimento.razaoSocial'] = 'Farmácia do trabalhador de Alagoas'
        df_grouped2 = df_vendas_filtered2.groupby(['produto.gtin', 'estabelecimento.razaoSocial']).agg(
            precoMinimo=('produto.venda.valorVenda', 'min'),
            precoMaximo=('produto.venda.valorVenda', 'max'),
            precoMedio=('produto.venda.valorVenda', 'mean'),
            precoModa=('produto.venda.valorVenda', lambda x: x.mode().iloc[0] if not x.mode().empty else None)
        ).reset_index()

    # Arredondar os valores para duas casas decimais
    if 'df_grouped1' in locals() and df_grouped1 is not None:
        df_grouped1[['precoMinimo', 'precoMaximo', 'precoMedio', 'precoModa']] = df_grouped1[['precoMinimo', 'precoMaximo', 'precoMedio', 'precoModa']].round(2)

    if 'df_grouped2' in locals() and df_grouped2 is not None:
        df_grouped2[['precoMinimo', 'precoMaximo', 'precoMedio', 'precoModa']] = df_grouped2[['precoMinimo', 'precoMaximo', 'precoMedio', 'precoModa']].round(2)

    # Merge dos DataFrames
    if 'df_grouped1' in locals() and df_grouped1 is not None and 'df_grouped2' in locals() and df_grouped2 is not None:
        df_merged = pd.concat([df_grouped1, df_grouped2], ignore_index=True)
    elif 'df_grouped1' in locals() and df_grouped1 is not None:
        df_merged = df_grouped1
    elif 'df_grouped2' in locals() and df_grouped2 is not None:
        df_merged = df_grouped2
    else:
        st.warning("Nenhum dado foi filtrado.")

# Exibir DataFrame combinado
    if 'df_merged' in locals() and not df_merged.empty:
        st.write(df_merged)
        export_excel(df_merged, "Pesquisa_de_Precos.xlsx")
