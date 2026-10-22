"""Reflexões extraídas do PDF fornecido pelo usuário, separadas por título."""
import json
from functools import lru_cache
from pathlib import Path
from secrets import choice


@lru_cache(maxsize=1)
def catalogo():
    caminho = Path(__file__).resolve().parent / 'data' / 'reflexoes_epicteto.json'
    return json.loads(caminho.read_text(encoding='utf-8'))


def sortear_reflexao(anterior=''):
    dados = catalogo()
    reflexoes = dados['reflexoes']
    candidatas = [item for item in reflexoes if str(item['id']) != anterior]
    item = choice(candidatas or reflexoes)
    inicio, fim = item['pagina_livro_inicio'], item['pagina_livro_fim']
    return {
        'id': item['id'], 'titulo': item['titulo'], 'paragrafos': item['paragrafos'],
        'paginas': f'p. {inicio}' if inicio == fim else f'pp. {inicio}–{fim}',
        'fonte': (
            f"{dados['autor']} — {dados['livro']}. Interpretação de {dados['interpretacao']}. "
            f"Tradução de {dados['traducao']}. {dados['edicao']}."
        ),
    }
