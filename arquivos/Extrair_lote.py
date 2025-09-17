import os
import xarray as xr
import pandas as pd

# Caminho da pasta com os arquivos .nc
pasta = r"D:\Documentos\ufrpe\IPECTI\Projeto Raffael\incendio_florestal\arquivos\arquivos_extracao"

# Coordenadas desejadas

#Cotriguaçu MT
#lat = -9.85
#lon = -58.40

#Palmeiras BA
lat = -12.45
lon = -41.47

# Lista para armazenar os resultados
resultados = []

# Percorrer todos os arquivos na pasta
for arquivo in os.listdir(pasta):
    if arquivo.endswith(".nc") and "FireRisk" in arquivo:
        caminho_arquivo = os.path.join(pasta, arquivo)
        
        # Extrair a data do nome do arquivo
        try:
            data_str = arquivo[-11:-3]  # "20250613"
            data_formatada = f"{data_str[:4]}-{data_str[4:6]}-{data_str[6:]}"
        except Exception as e:
            print(f"Erro ao extrair data do arquivo {arquivo}: {e}")
            continue
        
        try:
            # Abrir o arquivo
            ds = xr.open_dataset(caminho_arquivo)

            # Variável de risco de fogo
            var = ds["rf"]

            # Selecionar o valor
            valor = var.sel(lat=lat, lon=lon, time=data_formatada, method="nearest")
            risco = round(valor.values.item(), 2)  # Arredonda para duas casas decimais

            # Armazena o resultado
            resultados.append({"data": data_formatada, "risco_fogo": risco})
            print(f"Extraído: {arquivo} | Risco: {risco}")

        except Exception as e:
            print(f"Erro processando {arquivo}: {e}")

# Criar DataFrame e exportar para Excel com "." como separador decimal
df = pd.DataFrame(resultados)
arquivo_saida = os.path.join(pasta, "Risco.xlsx")
with pd.ExcelWriter(arquivo_saida) as writer:
    df.to_excel(writer, sheet_name="Cidade", index=False, float_format="%.2f")

print("Arquivo Excel gerado com sucesso:", arquivo_saida)
