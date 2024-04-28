import base64
import json

import pandas as pd
import requests
import streamlit as st
from streamlit_option_menu import option_menu

from credentials import APP_TOKEN, BASE_URL_API, USER_EMAIL, USER_PASSWORD

# Configuração da página
st.set_page_config(page_title=f"Dados Em FOCO! - Pesquisa", page_icon="bar_chart", layout="wide")


def signin(login, password):
    # Substitua esta parte pelo código de autenticação da sua nova API ou método
    if login == USER_EMAIL and password == USER_PASSWORD:
        st.success("Login realizado com sucesso!")
        st.button("Acessar Painel")
        # Aqui você pode definir o token e detalhes do usuário como desejado
        token = "seu_token_de_autenticacao"
        user_details = {"nome": "Usuário Exemplo", "login": login}
        st.session_state.token = token
        st.session_state.logged_in = True  # Definindo como True após o login
        st.session_state.user_details = user_details  # Armazenar os detalhes do usuário
        return token
    else:
        st.error("Falha ao fazer login. Verifique suas credenciais.")


# Verifica se o usuário está logado
def is_user_logged_in():
    return "token" in st.session_state and st.session_state.logged_in


# Página de Login
def login_page():
    st.markdown(
        """
        <style>
            .header-text {
                color: #FFCE3F;
                background-color: #7300AB; /* Cor amarela */
                text-align: center;
                font-size: 24px;
                margin-bottom: 30px;
            }
            .input-container {
                margin-bottom: 20px;
            }
            .login-button {
                background-color: #008080;
                color: blue;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                transition: background-color 0.3s;
            }
            .login-button:hover {
                background-color: #001F3F;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<h2 class='header-text'>🔐 Acesso ao sistema</h2>", unsafe_allow_html=True)

    login = st.text_input("Login", key="login", max_chars=50)
    password = st.text_input("Senha", type="password", key="password", max_chars=20)

    if st.button("Entrar", key="login_button"):
        token = signin(login, password)

    st.markdown("</div>", unsafe_allow_html=True)


def update_sidebar():
    user_details = st.session_state.user_details
    if user_details:
        st.sidebar.empty()
        with st.sidebar:
            st.markdown(
                """
                <style>
                .sidebar .sidebar-content {
                    display: flex;
                    flex-direction: column;
                    align-items: right;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            # Lista de opções para o selectbox
            options = ["💰 Pesquisa de preços", "🚪 Sair"]
            # Criar o selectbox
            selected = st.selectbox("Selecione:", options)

        if selected == "💰 Pesquisa de preços":
            consulta_page()
        elif selected == "🚪 Sair":
            logout()
    else:
        st.sidebar.empty()

def logout():
    confirm_logout()


# Função para confirmar logout
def confirm_logout():
    if st.sidebar.button("Sim", key="confirm_button"):
        st.session_state.logged_in = False
        st.session_state.token = None
        st.sidebar.empty()  # Limpa a barra lateral
        st.success("Logout realizado com sucesso!")
    elif st.sidebar.button("Não", key="cancel_button"):
        st.sidebar.empty()  # Limpa a barra lateral
        st.info("Logout cancelado.")



@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is not None:
        # Ler o arquivo EXCEL
        df = pd.read_excel(uploaded_file, dtype={'gtin': str})
        with st.spinner("Carregando dados..."):    
            # Lista para armazenar todos os dados coletados
            all_data = []
            not_found = []

            # URL base da API
            base_url = BASE_URL_API

            # Token de acesso fornecido pela SEFAZ/AL
            app_token = APP_TOKEN

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
                        not_found.append(title)
                else:
                    not_found.append(title)

            # Exibir a contagem de códigos não encontrados
            if len(not_found) > 0:
                st.warning(f"{len(not_found)} produtos não foram encontrados.")

                # Listar os códigos não encontrados
                st.write("Códigos não encontrados:")
                for code in not_found:
                    st.write(code)

            # Criar DataFrame com todos os dados coletados
            df_vendas = pd.json_normalize(all_data)
            # Converter a coluna 'produto.venda.valorVenda' para numérica
            df_vendas['produto.venda.valorVenda'] = pd.to_numeric(df_vendas['produto.venda.valorVenda'], errors='coerce')

            return df_vendas

def consulta_page():
    st.title('💰')
    col1, col2 = st.columns(2)

    # Adicionar texto personalizado acima do botão de upload
    col1.markdown("""
    ### Carregue arquivo EXCEL com códigos de barras:
    **ATENÇÃO PARA OS PONTOS ABAIXO:**

    **-Lembre-se de nomear coluna com EANS de "git";**

    **-Arquivo Formato • EXCEL XLSX.**
    """)

    uploaded_file = col1.file_uploader("", type=["xlsx"])

    if uploaded_file is not None:
        df_vendas = load_data(uploaded_file)
        mapeamento_cnpjs = {
            'BARROS COMERCIO LTDA': 'SUPERMERCADO SAO DOMINGOS',
            'ATACADAO S.A.': 'ATACADÃO',
            'AMERICANAS S.A - EM RECUPERACAO JUDICIAL': 'AMERICANAS',
            'FARMACIA SANTA ANITA LTDA - ME': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'RAPHAEL ARAGAO DE ARAUJO - ME': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'GONCALVES E ARAUJO FARMACIA LTDA': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'SAUDE FARMA LTDA - EPP': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'MEG FARMACIA LTDA - ME': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'E LUCENA DE ARAUJO FARMACIA LTDA': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'ERICO LUCENA DE ARAUJO FARMACIA - ME': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'DROGA LUZ LTDA -  ME': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'FARMACIA DO TRABALHADOR MINIPRECO LTDA - ME': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'FARMACIA SAO SEVERINO LTDA - ME': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'E L DE ARAUJO FARMACIA - ME': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'FARMACIA QUEIROZ LTDA - ME': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'FARMACIA LUCENA LTDA - EPP': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'NOSSA SENHORA DE FATIMA FARMACIA LTDA - ME': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'R J INACIO COMERCIO LTDA - ME': 'FARMACIA DO TRABALHADOR DE ALAGOAS',
            'BEZERRA & CLINERIO COMERCIO HORTIFRUTIGRANJEIROS LTDA': 'QUITANDARIA',
            'BIG DISTRIBUIDOR IMPORTACAO E EXPORTACAO LTDA': 'BIG ATACADO',
            'BOMPRECO SUPERMERCADOS DO NORDESTE LTDA': 'SUPERMERCADOS BOMPRECO',
            'C&A MODAS S.A.': 'C&A',
            'CASA LEA LTDA': 'CASA LEA',
            'CENCOSUD BRASIL COMERCIAL S.A.': 'G. BARBOSA',
            'CLINERIO COMERCIO DE HORTIFRUTIGRANJEIROS': 'QUITANDARIA',
            'COMERCIAL DE EMBALAGENS DESCARTAVEIS E FESTAS LTDA - EPP': 'FELÍCIA',
            'COMERCIAL DE MEDICAMENTOS SAMPAIO LTDA': 'DROGARIAS SAMPAIO',
            'COMERCIAL DRUGSTORE LTDA': 'FARMACIA PERMANENTE',
            'COMPRARBEM LTDA': 'COMPRARBEM SUPERMERCADO',
            'COSMETICA VAREJO LTDA': 'COSMETICA VAREJO',
            'D A L COMERCIO LTDA': 'FARMACIA DROGALIMA',
            'DROGATIM DROGARIAS LTDA': 'FARMACIA PERMANENTE',
            'EMPREENDIMENTOS PAGUE MENOS S/A': 'FARMACIA PAGUE MENOS',
            'ESPECIARYA INDUSTRIA E COMERCIO LTDA': 'PALATO SUPERMERCADO',
            'IAP COSMETICOS LTDA.': 'IAP! COSMETICOS',
            'JARBAS COSTA BRAZ - ME': 'FARMACIA DO JARBAS',
            'LEITE & PARANHOS LTDA': 'PRECO BOM',
            'LAMENHA COMÉRCIO DE ALIMENTOS LTDA': 'SUPERMERCADO O CESTÃO BENEDITO BENTES',
            'LOJAS RIACHUELO SA': 'LOJAS RIACHUELO',
            'LOJAS RENNER S.A.': 'LOJAS RENNER',
            'OLIVEIRA E NOBRE SUPERMERCADO LTDA': 'SUPERMERCADO NOBRE',
            'P V SUPERMERCADO LTDA': 'PV SUPERMERCADO',
            'PRECO CERTO COM. DE ALIMENTOS LTDA': 'SUPERMERCADO PRECO CERTO',
            'PROFISSIONAL CABELOS E COSMETICOS': 'PROFISSIONAL CABELOS E COSMETICOS',
            'RAIA DROGASIL S/A': 'DROGASIL',
            'S. VIEIRA DA SILVA LTDA': 'CASA VIEIRA',
            'SENDAS DISTRIBUIDORA S/A': 'ASSAÍ',
            'SUPER GIRO DISTRIBUIDOR DE ALIMENTOS LTDA': 'SUPER GIRO',
            'SUPER-AZUL COMERCIO VAREJISTA E ATACADISTA DE ALIMENTOS - LTDA': 'SUPERMERCADO AZULÃO',
            'SUPERMERCADO LESTE OESTE LTDA': 'PONTO CERTO',
            'SUPERMERCADOS CESTA DE ALIMENTOS LTDA': 'CESTA DE ALIMENTOS',
            'T.M. SUPERMERCADO LTDA': 'SUPERMERCADO BOM DIA',
            'UNI COMPRA SUPERMERCADOS LTDA': 'UNI COMPRA',
            'WMB SUPERMERCADOS DO BRASIL LTDA.': 'SAMS CLUB'
        }
        if df_vendas is not None:
            df_vendas['estabelecimento.razaoSocial'] = df_vendas['estabelecimento.razaoSocial'].map(mapeamento_cnpjs)
            df_grouped1 = None
            df_grouped2 = None

        # Compartilhar a lógica para evitar duplicação
            def export_excel(df, file_name):
                with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Sheet1')
                with open(file_name, 'rb') as f:
                    data = f.read()
                    b64 = base64.b64encode(data).decode()
                    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{file_name}">Faça Download da {file_name}</a>'
                    st.markdown(href, unsafe_allow_html=True)

        # Função para filtrar e agregar os dados
            def filtrar_e_agregar(dados, filtro):
                df_filtrado = dados[dados['estabelecimento.razaoSocial'].isin(filtro) | dados['estabelecimento.nomeFantasia'].isin(filtro)]
                
                # Substituir valores None em 'estabelecimento.razaoSocial' pelo nome fantasia 'FARMACIA DO TRABALHADOR DE ALAGOAS'
                # df_filtrado.loc[df_filtrado['estabelecimento.razaoSocial'].isna(), 'estabelecimento.razaoSocial'] = 'FARMACIA DO TRABALHADOR DE ALAGOAS'

                # Agregar os dados
                df_agregado = df_filtrado.groupby(['produto.gtin', 'estabelecimento.razaoSocial']).agg(
                    preço_Mínimo=('produto.venda.valorVenda', 'min'),
                    preço_Máximo=('produto.venda.valorVenda', 'max'),
                    preço_Médio=('produto.venda.valorVenda', 'mean'),
                    preço_Moda=('produto.venda.valorVenda', lambda x: x.mode().iloc[0] if not x.mode().empty else None)
                ).reset_index()

                return df_agregado


            # Listas de empresas para cada categoria
            cosmeticos = ['CASA LEA', 'COSMETICA VAREJO', 'IAP! COSMETICOS', 'PROFISSIONAL CABELOS E COSMETICOS', 'PROFISSIONAL CABELOS E COSMETICOS']
            varejo_alimentar = ['UNI COMPRA', 'SAMS CLUB', 'SUPERMERCADO BOM DIA', 'CESTA DE ALIMENTOS', 'PONTO CERTO', 'SUPERMERCADO AZULÃO', 'SUPER GIRO', 'SUPERMERCADO PRECO CERTO', 'PV SUPERMERCADO', 'SUPERMERCADO NOBRE', 'SUPERMERCADO O CESTÃO BENEDITO BENTES', 'PRECO BOM', 'PALATO SUPERMERCADO', 'COMPRARBEM SUPERMERCADO', 'G. BARBOSA', 'SUPERMERCADOS BOMPRECO', 'SUPERMERCADO SAO DOMINGOS']
            atacado_alimentar = ['ASSAÍ', 'ATACADÃO', 'BIG ATACADO']
            moda = ['C&A', 'LOJAS RIACHUELO', 'LOJAS RENNER']
            multi_departamentos = ['AMERICANAS', 'FELÍCIA', 'CASA VIEIRA']
            farmacias = ['FARMACIA DO TRABALHADOR DE ALAGOAS', 'DROGARIAS SAMPAIO', 'FARMACIA PERMANENTE', 'FARMACIA DROGALIMA', 'FARMACIA PAGUE MENOS', 'DROGASIL']
            outros = ['QUITANDARIA']

            # Defina a ordem das categorias conforme o CNPJ
            ordem_categorias = [
                cosmeticos,
                varejo_alimentar,
                multi_departamentos,
                farmacias,
                moda,
                atacado_alimentar,
                outros
            ]
            # Filtrar por Razão Social no sidebar
            with st.sidebar:
                selected_categorias = st.multiselect("Filtrar concorrentes por segmento:", ["Todos", "Cosméticos", "Varejo Alimentar", "Multi Departamentos", "Farmácias", "Moda", "Atacado Alimentar", "Outros"])

            resultados_por_categoria = []

            # Iterar sobre as categorias selecionadas e adicionar resultados filtrados
            for categoria in selected_categorias:
                if categoria == "Todos":
                    filtro = cosmeticos + varejo_alimentar + multi_departamentos + farmacias + moda + atacado_alimentar + outros
                elif categoria == "Cosméticos":
                    filtro = cosmeticos
                elif categoria == "Varejo Alimentar":
                    filtro = varejo_alimentar
                elif categoria == "Multi Departamentos":
                    filtro = multi_departamentos
                elif categoria == "Farmácias":
                    filtro = farmacias
                elif categoria == "Moda":
                    filtro = moda
                elif categoria == "Atacado Alimentar":
                    filtro = atacado_alimentar
                elif categoria == "Outros":
                    filtro = outros

                df_agregado = filtrar_e_agregar(df_vendas, filtro)
                resultados_por_categoria.append(df_agregado)

            # Combinar os resultados de todas as categorias
            if resultados_por_categoria:
                df_completo = pd.concat(resultados_por_categoria, ignore_index=True)

                # Exibir o DataFrame completo
                st.write(df_completo)

                # Exportar para Excel
                export_excel(df_completo, "Pesquisa_de_Precos.xlsx")
                # Identificar linhas com valores None na coluna 'estabelecimento.razaoSocial'
                rows_with_none = df_completo[df_completo['estabelecimento.razaoSocial'].isna()]

                # Exibir as linhas com valores None
                print(rows_with_none)
            else:
                st.warning("Por favor, selecione o(s) segmento(s) dos concorrrente(s) para continuar.")

# Página de login
def main():
    if not is_user_logged_in():
            st.sidebar.image("resources/img/logo192.png")
            st.sidebar.image("resources/img/logo-topo.png")
        #     selected = option_menu(
        #         menu_title="Menu",
        #         options=["Acesso"],
        #         icons=["key"],
        #         menu_icon="cast",
        #         default_index=0
        #     )
        # if selected == "Acesso":
            login_page()
    else:
        update_sidebar()

if __name__ == "__main__":
    main()