from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Subquery
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.cache import never_cache

from denuncias.models import Denuncia
from register.models import Estabelecimento, Vigilancia
from register.inspecoes import com_inspecao_atual
from .forms import LembreteForm
from .models import Lembrete
from .reflexoes import sortear_reflexao


@login_required
def home_view(request):
    return _render_home(request)


@login_required
@require_GET
@never_cache
def reflexao_aleatoria(request):
    return JsonResponse(sortear_reflexao(request.GET.get('anterior', '')))


def _render_home(request, lembrete_form=None, status=200):
    hoje = timezone.localdate()
    estabelecimentos = com_inspecao_atual(Estabelecimento.objects.all(), hoje.year).filter(
        status=False, inspecao_fiscal_id=request.user.pk,
        inspecao_status_atual=Vigilancia.Status.A_FAZER,
        inspecao_ano_previsto=hoje.year, inspecao_mes_previsto=hoje.month,
    )
    inspecoes = Vigilancia.objects.filter(
        pk__in=Subquery(estabelecimentos.values('inspecao_atual_id')),
    ).select_related('estabelecimento').order_by('estabelecimento__numero_pasta', 'pk')
    denuncias = Denuncia.objects.filter(
        fiscal_responsavel=request.user, status__in=['pendente', 'em_andamento'],
    ).order_by('data_criacao', 'pk')
    return render(request, 'home/index.html', {
        'mes_pendencias': hoje,
        'inspecoes_pendentes': Paginator(inspecoes, 5).get_page(request.GET.get('insp_page')),
        'denuncias_pendentes': Paginator(denuncias, 5).get_page(request.GET.get('den_page')),
        'lembretes': Lembrete.objects.filter(autor=request.user, concluido_em__isnull=True),
        'lembrete_form': lembrete_form if lembrete_form is not None else LembreteForm(),
    }, status=status)


def _ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


@login_required
@require_POST
def lembrete_criar(request):
    form = LembreteForm(request.POST)
    if not form.is_valid():
        if _ajax(request):
            return JsonResponse({'erro': ' '.join(form.errors.get('texto', ['Confira o lembrete.']))}, status=400)
        return _render_home(request, form, status=400)
    lembrete = form.save(commit=False)
    lembrete.autor = request.user
    lembrete.save()
    if _ajax(request):
        return JsonResponse({
            'id': lembrete.pk, 'texto': lembrete.texto,
            'concluir_url': reverse('home:lembrete_concluir', args=[lembrete.pk]),
        }, status=201)
    return redirect(reverse('home:index') + '#lembretes')


@login_required
@require_POST
def lembrete_concluir(request, pk):
    lembrete = get_object_or_404(Lembrete, pk=pk, autor=request.user)
    Lembrete.objects.filter(pk=lembrete.pk, concluido_em__isnull=True).update(concluido_em=timezone.now())
    if _ajax(request):
        return JsonResponse({'concluido': True})
    return redirect(reverse('home:index') + '#lembretes')
