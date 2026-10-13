from django.utils import timezone

def endereco(pessoa):
    if not pessoa:
        return ''
    return ', '.join(str(getattr(pessoa, campo) or '') for campo in ('logradouro', 'numero', 'bairro')
                     if getattr(pessoa, campo))


def contexto_documento(est, user, notificacao=False, pode_salvar=False):
    responsavel = est.responsavel.order_by('-pk').first()
    tecnico = est.responsavel_tecnico.order_by('-pk').first()
    tipo = est.tipos.order_by('-pk').first()
    hoje = timezone.localdate()
    campos = {f'campo_{numero:02d}': '' for numero in range(1, 33)}
    campos.update({
        'pode_salvar_padrao': pode_salvar,
        'estabelecimento': est,
        'campo_01': 'Montes Claros-MG',
        'campo_02': 'Taiobeiras-MG',
        'campo_03': est.pk,
        'campo_04': est.nome_fantasia, 'campo_05': est.razao_social,
        'campo_06': est.cnpj, 'campo_07': est.insc_municipal,
        'campo_08': ' / '.join(filter(None, [tipo.classe, tipo.cnae_principal])) if tipo else '',
        'campo_09': endereco(est), 'campo_10': est.phone, 'campo_11': est.cep,
        'campo_12': est.cidade, 'campo_13': est.uf,
        'campo_21': endereco(responsavel), 'campo_28': endereco(tecnico),
        'autoridade_nome': user.get_full_name() or user.username,
        'campo_38_dia': hoje.strftime('%d'), 'campo_38_mes': hoje.strftime('%m'),
        'campo_38_ano': hoje.year,
    })
    for numero, atributo in {14: 'nome', 15: 'nacionalidade', 16: 'naturalidade',
                            17: 'estado_civil', 18: 'rg', 19: 'profissao', 20: 'cpf',
                            22: 'phone', 24: 'cidade', 25: 'uf'}.items():
        campos[f'campo_{numero:02d}'] = getattr(responsavel, atributo, '') or ''
    for numero, atributo in {26: 'nome', 27: 'rg_conselho', 29: 'phone', 31: 'cidade', 32: 'uf'}.items():
        campos[f'campo_{numero:02d}'] = getattr(tecnico, atributo, '') or ''
    if notificacao:
        campos.update(campo_02='Montes Claros-MG', campo_03='Taiobeiras-MG',
                      campo_email=est.email, campo_34_nome_1=campos['autoridade_nome'],
                      campo_36_cargo_1='Autoridade Sanitária')
    return campos
