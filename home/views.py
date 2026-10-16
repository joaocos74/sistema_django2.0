from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.paginator import Paginator
from django.utils import timezone

from denuncias.models import Denuncia
from register.models import Vigilancia


@login_required
def home_view(request):
    hoje = timezone.localdate()
    inspecoes = Vigilancia.objects.filter(
        fiscal=request.user, inspecao_status=Vigilancia.Status.A_FAZER,
        ano_previsto=hoje.year, mes_previsto=hoje.month,
        estabelecimento__status=False,
    ).select_related('estabelecimento').order_by('estabelecimento__numero_pasta', 'pk')
    denuncias = Denuncia.objects.filter(
        fiscal_responsavel=request.user, status__in=['pendente', 'em_andamento'],
    ).order_by('data_criacao', 'pk')
    return render(request, 'home/index.html', {
        'mes_pendencias': hoje,
        'inspecoes_pendentes': Paginator(inspecoes, 5).get_page(request.GET.get('insp_page')),
        'denuncias_pendentes': Paginator(denuncias, 5).get_page(request.GET.get('den_page')),
    })
