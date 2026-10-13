import uuid

from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.paginator import Paginator
from django.db import OperationalError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_GET

from register.models import Estabelecimento
from .contexto import contexto_documento
from .forms import PadraoForm, NotificacaoForm
from .models import AutoTermoPadrao, NotificacaoPadrao, NotificacaoEmitida
from .services import proximo_numero, gerar_notificacao


def pagina(request, template, contexto):
    response = render(request, template, contexto)
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
@require_http_methods(['GET', 'POST'])
def documento(request, pk, tipo='auto_termo'):
    notificacao = tipo == 'notificacao'
    modelo = NotificacaoPadrao if notificacao else AutoTermoPadrao
    formulario = NotificacaoForm if notificacao else PadraoForm
    est = get_object_or_404(Estabelecimento, pk=pk)
    ultima = est.fiscalizacoes.order_by('-pk').first()
    pode_salvar = request.user.is_superuser or (ultima is not None and ultima.fiscal_id == request.user.pk)
    if request.method == 'POST':
        if not pode_salvar:
            return JsonResponse({'erro': 'Somente o fiscal responsável ou administrador pode salvar ou gerar.'}, status=403)
        form = formulario(request.POST)
        if not form.is_valid():
            return JsonResponse({'erro': 'Confira o tamanho e o formato dos campos.', 'campos': form.errors}, status=400)
        campos = {key: value for key, value in form.cleaned_data.items() if key in request.POST}
        if notificacao:
            try:
                token = signing.loads(request.POST.get('emissao_token', ''), salt='notificacao', max_age=86400)
                if token['est'] != est.pk or token['user'] != request.user.pk:
                    raise ValueError
                chave = uuid.UUID(token['chave'])
            except (signing.BadSignature, KeyError, ValueError, TypeError):
                return JsonResponse({'erro': 'Sessão de emissão inválida ou expirada. Reabra a Notificação.'}, status=400)
            try:
                base = contexto_documento(est, request.user, True)
                snapshot = {k: str(v or '') for k, v in base.items() if k in formulario().fields}
                anterior = NotificacaoPadrao.objects.filter(estabelecimento=est).first()
                if anterior:
                    snapshot.update({k: v for k, v in anterior.campos.items() if k in formulario().fields})
                snapshot.update(campos)
                registro = gerar_notificacao(est, request.user, snapshot, chave)
            except OperationalError:
                return JsonResponse({'erro': 'O banco está ocupado. Tente gerar novamente.'}, status=503)
            return JsonResponse({'mensagem': f'Notificação {registro.numero_formatado} gerada.',
                                 'url': reverse('termos:emitida', args=[registro.pk])})
        modelo.objects.update_or_create(estabelecimento=est, defaults={'campos': campos, 'atualizado_por': request.user})
        return JsonResponse({'mensagem': 'Padrão salvo para este estabelecimento.'})
    campos = contexto_documento(est, request.user, notificacao, pode_salvar)
    padrao = modelo.objects.filter(estabelecimento=est).first()
    campos['padrao_salvo'] = {k: v for k, v in padrao.campos.items() if k in formulario().fields} if padrao else {}
    if notificacao:
        campos['numero_notificacao'] = proximo_numero()
        campos['emissao_token'] = signing.dumps({'est': est.pk, 'user': request.user.pk, 'chave': str(uuid.uuid4())}, salt='notificacao')
    return pagina(request, f'termos/{tipo}.html', campos)


@login_required
@require_GET
def emitida(request, pk):
    registro = get_object_or_404(NotificacaoEmitida.objects.select_related('estabelecimento'), pk=pk)
    return pagina(request, 'termos/notificacao.html', {'estabelecimento': registro.estabelecimento,
        'padrao_salvo': registro.campos, 'numero_notificacao': registro.numero_formatado,
        'emitida': registro, 'pode_salvar_padrao': False})


@login_required
@require_GET
def historico(request, pk):
    est = get_object_or_404(Estabelecimento, pk=pk)
    registros = est.notificacoes_emitidas.select_related('gerado_por')
    return pagina(request, 'termos/historico.html', {'estabelecimento': est,
        'pagina': Paginator(registros, 25).get_page(request.GET.get('page'))})
