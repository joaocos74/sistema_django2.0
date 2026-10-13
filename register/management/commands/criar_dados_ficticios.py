from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from register.models import Estabelecimento, Responsavel, RTResponsavel, Tipo, Vigilancia


class Command(BaseCommand):
    help = "Cria exemplos identificados como fictícios, sem duplicar os registros existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Os dados fictícios são exclusivos do ambiente de desenvolvimento (DEBUG=True).")

        fiscais = []
        for numero, nome in enumerate(("Ana", "Bruno"), 1):
            usuario, criado = get_user_model().objects.get_or_create(
                username=f"demo_fiscal_{numero}",
                defaults={"first_name": nome, "last_name": "Fictício", "is_active": False},
            )
            if criado:
                usuario.set_unusable_password()
                usuario.save(update_fields=["password"])
            elif usuario.is_active or usuario.has_usable_password():
                raise CommandError(f"O usuário demo_fiscal_{numero} já existe e não é uma conta de demonstração desativada.")
            fiscais.append(usuario)

        exemplos = (
            ("Mercado Exemplo", "I", "4712-1/00", "Comércio de alimentos", "a_fazer"),
            ("Padaria Exemplo", "II", "1091-1/02", "Panificação", "concluido"),
            ("Restaurante Exemplo", "II", "5611-2/01", "Restaurante", "pendente"),
            ("Farmácia Exemplo", "III", "4771-7/01", "Farmácia", "concluido"),
            ("Clínica Exemplo", "III", "8630-5/03", "Clínica", "a_fazer"),
        )
        # Data fixa para que novas execuções não criem outro conjunto de inspeções.
        referencia = date(2026, 10, 11)
        criados = 0
        for numero, (nome, risco, cnae, classe, status) in enumerate(exemplos, 1):
            endereco = {
                "logradouro": "Rua Fictícia", "numero": str(numero * 100),
                "bairro": "Bairro de Demonstração", "cidade": "Taiobeiras", "uf": "MG",
                "phone": "(00) 00000-0000",
            }
            estabelecimento, criado = Estabelecimento.objects.get_or_create(
                n_parecer=f"DEMO-{numero:03d}",
                nome_fantasia=f"[FICTÍCIO] {nome}",
                defaults={
                    **endereco, "cnpj": f"00.000.000/000{numero}-00",
                    "razao_social": f"{nome} Fictício Ltda.", "cep": "00000-000",
                    "email": f"exemplo{numero}@example.invalid",
                    # O modelo atual define False como ativo.
                    "status": False,
                },
            )
            criados += criado
            Tipo.objects.get_or_create(
                estabelecimento=estabelecimento, risco=risco, cnae_principal=cnae, classe=classe,
            )
            Responsavel.objects.get_or_create(
                estabelecimento=estabelecimento, nome=f"Responsável Fictício {numero}",
                defaults={**endereco, "cpf": f"000.000.00{numero}-00"},
            )
            if numero >= 4:
                RTResponsavel.objects.get_or_create(
                    estabelecimento=estabelecimento, nome=f"Técnico Fictício {numero}",
                    defaults={
                        **endereco, "profissao": "Farmacêutico" if numero == 4 else "Médico",
                        "rg_conselho": f"DEMO-{numero}",
                    },
                )
            concluido = status == Vigilancia.Status.CONCLUIDO
            Vigilancia.objects.get_or_create(
                estabelecimento=estabelecimento, obs="DEMO: inspeção fictícia para testes do admin.",
                defaults={
                    "fiscal": fiscais[numero % 2], "inspecao_status": status,
                    "ano_previsto": referencia.year, "mes_previsto": referencia.month,
                    "data_realizacao": referencia - timedelta(days=numero) if concluido else None,
                    "data_alvara": referencia - timedelta(days=1) if concluido else None,
                    "plano_aplicado": "aplicado" if status == "pendente" else "nao_requerido",
                    "plano_status": "pendente" if status == "pendente" else None,
                },
            )
        self.stdout.write(self.style.SUCCESS(
            f"Dados fictícios disponíveis: 5 estabelecimentos ({criados} novos), "
            "5 classificações, 5 responsáveis, 2 responsáveis técnicos e 5 inspeções. "
            "Os 2 usuários fictícios estão inativos e sem senha utilizável."
        ))
