import json
import re
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from usuarios.models import PALETA_CORES
from .forms import ItemAgendaForm
from .models import ItemAgenda


def serializar(item, user):
    perfil = getattr(item.autor, 'perfil', None)
    return {
        'id': item.pk, 'dia': item.dia.isoformat(), 'turno': item.turno,
        'texto': item.texto, 'feito': item.feito,
        'cor': perfil.cor if perfil else PALETA_CORES[(item.autor_id - 1) % len(PALETA_CORES)],
        'autor_nome': item.autor.get_full_name() or item.autor.username,
        'pode_editar': user.is_superuser or item.autor_id == user.pk,
        'url': reverse('home:api_agenda_detalhe', args=[item.pk]),
    }


def dados_json(request):
    if len(request.body) > 40000:
        raise ValueError('Conteúdo muito grande.')
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('JSON inválido.')
    if not isinstance(data, dict):
        raise ValueError('Envie um objeto JSON.')
    for field in ('dia', 'turno', 'texto'):
        if field in data and not isinstance(data[field], str):
            raise ValueError('Campos de data, turno e texto devem ser textos.')
    if 'feito' in data and type(data['feito']) is not bool:
        raise ValueError('O campo feito deve ser verdadeiro ou falso.')
    vinculados = data.get('vinculados', [])
    if not isinstance(vinculados, list) or len(vinculados) > 1000 or any(not isinstance(v, str) or len(v) > 150 for v in vinculados):
        raise ValueError('Lista de menções inválida.')
    return data


def salvar_mencoes(item, data):
    if 'texto' not in data and 'vinculados' not in data:
        return
    usuarios = get_user_model().objects.filter(is_active=True)
    if not re.search(r'@todos\b', item.texto, re.IGNORECASE):
        nomes = re.findall(r'@([\w.+-]+)', item.texto)
        usuarios = usuarios.filter(username__in=set(data.get('vinculados', []) + nomes))
    item.mencionados.set(usuarios.exclude(pk=item.autor_id))


@login_required
@require_GET
def agenda_view(request):
    return render(request, 'home/agenda.html')


@login_required
@require_GET
def api_usuarios(request):
    usuarios = get_user_model().objects.filter(is_active=True).order_by('username')
    return JsonResponse([
        {'id': u.pk, 'matricula': u.username, 'nome': u.get_full_name() or u.username}
        for u in usuarios
    ], safe=False)


@login_required
@require_GET
def api_agenda_semana(request, minha=False):
    hoje = timezone.localdate()
    inicio = hoje - timedelta(days=hoje.weekday())
    dias = [inicio + timedelta(days=i) for i in range(6)]
    itens = ItemAgenda.objects.filter(dia__range=(inicio, dias[-1]))
    if minha:
        itens = itens.filter(Q(autor=request.user) | Q(mencionados=request.user)).distinct()
    itens = itens.select_related('autor__perfil')
    return JsonResponse({
        'inicio': inicio.isoformat(),
        'dias': [{'dia': dia.isoformat(), 'limpar_url': reverse('home:api_agenda_apagar_dia', args=[dia.isoformat()])} for dia in dias],
        'itens': [serializar(item, request.user) for item in itens],
    })


@login_required
@require_POST
def api_agenda_criar(request):
    try:
        data = dados_json(request)
    except ValueError as error:
        return JsonResponse({'erro': str(error)}, status=400)
    form = ItemAgendaForm(data)
    if not form.is_valid():
        return JsonResponse({'erro': 'Revise a data, o turno e o texto (até 3.000 caracteres).', 'campos': form.errors}, status=400)
    with transaction.atomic():
        item = form.save(commit=False)
        item.autor = request.user
        item.save()
        salvar_mencoes(item, data)
    return JsonResponse(serializar(item, request.user), status=201)


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def api_agenda_detalhe(request, pk):
    with transaction.atomic():
        item = get_object_or_404(ItemAgenda.objects.select_for_update(), pk=pk)
        if not request.user.is_superuser and item.autor_id != request.user.pk:
            return JsonResponse({'erro': 'Somente o autor ou administrador pode alterar este lembrete.'}, status=403)
        if request.method == 'DELETE':
            item.delete()
            return JsonResponse({'sucesso': True})
        try:
            data = dados_json(request)
        except ValueError as error:
            return JsonResponse({'erro': str(error)}, status=400)
        valores = {name: data.get(name, getattr(item, name)) for name in ItemAgendaForm.Meta.fields}
        form = ItemAgendaForm(valores, instance=item)
        if not form.is_valid():
            return JsonResponse({'erro': 'Revise a data, o turno e o texto (até 3.000 caracteres).', 'campos': form.errors}, status=400)
        item = form.save()
        salvar_mencoes(item, data)
        return JsonResponse(serializar(item, request.user))


@login_required
@require_http_methods(['DELETE'])
def api_agenda_apagar_dia(request, dia_iso):
    try:
        dia = date.fromisoformat(dia_iso)
    except ValueError:
        return JsonResponse({'erro': 'Data inválida.'}, status=400)
    itens = ItemAgenda.objects.filter(dia=dia)
    if not request.user.is_superuser:
        itens = itens.filter(autor=request.user)
    itens.delete()
    return JsonResponse({'sucesso': True})
