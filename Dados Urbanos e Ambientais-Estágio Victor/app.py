from flask import Flask, render_template, request
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import json
from datetime import datetime
import os

app = Flask(__name__)

def carregar_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

config = carregar_config()

def carregar_dados():
    pasta = config['pastas']['dados']
    sep   = config['csv']['separador']
    dados = {}
    for api in config['apis']:
        if not api.get('ativo', True):
            continue
        caminho = os.path.join(pasta, f"Dados_{api['nome'].upper()}.csv")
        try:
            df = pd.read_csv(caminho, sep=sep)
            dados[api['nome']] = {'df': df, 'config': api, 'campos': api.get('campos', {})}
        except FileNotFoundError:
            print(f"Ficheiro nao encontrado: {caminho}")
        except Exception as e:
            print(f"Erro {api['nome']}: {e}")
    return dados

def determinar_cor(linha, config_api):
    # Procurar regras_cor dentro dos campos
    for campo_dest, campo_cfg in config_api.get('campos', {}).items():
        if 'regras_cor' in campo_cfg:
            if campo_dest in linha and pd.notna(linha[campo_dest]):
                try:
                    valor = float(linha[campo_dest])
                    for regra in campo_cfg['regras_cor']:
                        if valor <= regra['max']:
                            return regra['cor']
                except:
                    pass

    # Fallback para regras_cor na raiz (compatibilidade)
    if 'regras_cor' in config_api:
        regras = config_api['regras_cor']
        campo  = regras['campo']
        if campo in linha and pd.notna(linha[campo]):
            try:
                valor = float(linha[campo])
                for regra in regras['regras']:
                    if valor <= regra['max']:
                        return regra['cor']
            except:
                pass

    return config_api.get('cor_marcador', 'blue')

def construir_popup(linha, config_api, campos_config):
    local = linha.get('local', 'Desconhecido')

    html = f"""
    <div style='font-family:Segoe UI; min-width:220px;'>
        <div style='background:#2c3e50; color:white; padding:8px; border-radius:5px 5px 0 0;'>
            <b>{local}</b>
        </div>
        <div style='padding:10px; background:white; border-radius:0 0 5px 5px; border:1px solid #ddd;'>
            <small style='color:#666;'>{config_api.get('titulo', '')}</small><br>
    """

    for campo_dest, campo_cfg in campos_config.items():
        if campo_dest == 'local':
            continue
        if campo_dest in linha and pd.notna(linha[campo_dest]):
            valor   = linha[campo_dest]
            unidade = campo_cfg.get('unidade', '')
            if isinstance(valor, (int, float)):
                valor = f"{valor:.1f}" if abs(valor) < 1000 else f"{valor:.0f}"
            html += f"<div style='margin:3px 0;'><b>{campo_dest.capitalize()}:</b> {valor}{unidade}</div>"

    html += f"""
            <div style='margin-top:8px; color:#7f8c8d; font-size:10px;'>
                {linha.get('latitude', 0):.4f}, {linha.get('longitude', 0):.4f}
            </div>
        </div>
    </div>
    """
    return html

@app.route('/', methods=['GET', 'POST'])
def mapa():
    todos_dados = carregar_dados()
    apis_ativas = [a for a in config['apis'] if a.get('ativo', True)]

    if request.method == 'POST':
        apis_visiveis = {a['nome']: f"mostrar_{a['nome']}" in request.form for a in apis_ativas}
    else:
        apis_visiveis = {a['nome']: True for a in apis_ativas}

    mapa_cfg = config.get('mapa', {})
    mapa_obj = folium.Map(
        location=[mapa_cfg.get('centro_lat', 39.5), mapa_cfg.get('centro_lon', -8.0)],
        zoom_start=mapa_cfg.get('zoom_inicial', 6)
    )

    clusters   = {}
    contadores = {a['nome']: 0 for a in apis_ativas}
    totais     = {a['nome']: len(todos_dados.get(a['nome'], {}).get('df', [])) for a in apis_ativas}

    for api in apis_ativas:
        if api['nome'] in todos_dados:
            clusters[api['nome']] = MarkerCluster(name=api['titulo']).add_to(mapa_obj)

    for nome_api, info in todos_dados.items():
        if not apis_visiveis.get(nome_api, False):
            continue
        for _, linha in info['df'].iterrows():
            if pd.notna(linha.get('latitude')) and pd.notna(linha.get('longitude')):
                try:
                    folium.Marker(
                        [float(linha['latitude']), float(linha['longitude'])],
                        popup=construir_popup(linha, info['config'], info['campos']),
                        icon=folium.Icon(color=determinar_cor(linha, info['config'])),
                        tooltip=linha.get('local', 'Clique para detalhes')
                    ).add_to(clusters[nome_api])
                    contadores[nome_api] += 1
                except:
                    pass

    return render_template('index_app.html',
        titulo        = config.get('interface', {}).get('titulo', 'Mapa'),
        apis          = apis_ativas,
        apis_visiveis = apis_visiveis,
        contadores    = contadores,
        totais        = totais,
        total_pontos  = sum(contadores.values()),
        mapa_html     = mapa_obj._repr_html_(),
        hora          = datetime.now().strftime('%H:%M')
    )

@app.route('/sobre')
def sobre():
    return render_template('sobre.html',
        titulo = config.get('interface', {}).get('titulo', 'Mapa')
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)