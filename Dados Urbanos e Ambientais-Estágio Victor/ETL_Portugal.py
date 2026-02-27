import requests, pandas as pd, os, json

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

os.makedirs(config['pastas']['dados'], exist_ok=True)
dataframes = {}

def processar_iotbi(dados, api):

    registos = []
    campos_cfg = api.get('campos', {})

    for item in dados:
        r = {}

        lat = item.get('location_coordinates_lat')
        lon = item.get('location_coordinates_lon')
        if lat is None or lon is None:
            continue
        r['latitude']  = lat
        r['longitude'] = lon

        for dest, cfg in campos_cfg.items():
            v = item.get(cfg.get('origem', dest))
            if v is not None and str(v).strip() not in ('', 'None', 'null'):
                r[dest] = v

        if not r.get('local'):
            r['local'] = item.get('name') or item.get('title') or item.get('streetAddress') or 'Sem nome'

        r['fonte'] = api['nome']
        registos.append(r)

    return pd.DataFrame(registos)

for api in config['apis']:
    if not api.get('ativo', True): continue
    print(f"A processar: {api['titulo']}")
    try:
        r = requests.get(api['url'], timeout=60)
        r.raise_for_status()
        df = processar_iotbi(r.json(), api)
        if not df.empty:
            dataframes[api['nome']] = df
            print(f"  {len(df)} registos | colunas: {', '.join(df.columns)}")
        else:
            print(f"  Nenhum registo valido")
    except Exception as e:
        print(f"  Erro: {e}")

for nome, df in dataframes.items():
    if not df.empty:
        caminho = os.path.join(config['pastas']['dados'], f"Dados_{nome.upper()}.csv")
        df.to_csv(caminho, index=False, encoding=config['csv']['encoding'], sep=config['csv']['separador'])
        print(f"  {caminho} ({len(df)} linhas)")

       

    