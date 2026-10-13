from django.db import models 
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.models import User
import os


class Estabelecimento(models.Model):
    cnpj = models.CharField(
        max_length=18,
        verbose_name="CNPJ/CPF"
    )
    nome_fantasia = models.CharField(
        max_length=255,
        verbose_name="Nome Fantasia"
    )
    razao_social = models.CharField(
        max_length=255,
        verbose_name="Razão Social"
    )
    n_parecer = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Número do Parecer"
    )
    logradouro = models.CharField(
        max_length=255,
        verbose_name="Endereço"
    )
    numero = models.CharField(
        max_length=20,
        verbose_name="Número"
    )
    bairro = models.CharField(
        max_length=100,
        verbose_name="Bairro"
    )
    cidade = models.CharField(
        max_length=100,
        verbose_name="Cidade"
    )
    uf = models.CharField(
        max_length=2,
        verbose_name="UF"
    )
    cep = models.CharField(
        max_length=9,
        verbose_name="CEP"
    )
    phone = models.CharField(
        max_length=20,
        verbose_name="Telefone"
    )
    email = models.EmailField(
        blank=True
    )
    insc_municipal = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Inscrição Municipal"
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True
    )
    status = models.BooleanField(
        default=False, 
        help_text="Ativo quando desmarcado."
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):
        return f"{self.nome_fantasia}"


class Tipo(models.Model):
    class Risco(models.TextChoices):
        I = "I", " Risco I"
        II = "II", "Risco II"
        III = "III", "Risco III"
        IV = "IV", "Risco IV"


    estabelecimento = models.ForeignKey(
        Estabelecimento, 
        on_delete=models.CASCADE, 
        related_name="tipos",
    )
    alterado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="classificacoes_alteradas",
        verbose_name="Fiscal responsável pela alteração",
    )
    risco = models.CharField(
        max_length=4, 
        choices=Risco.choices,
        default=Risco.I,
        verbose_name="Risco"
    )
    cnae_principal = models.CharField(
        max_length=10
    )
    cnae_secundaria = models.CharField(
        max_length=255, 
        blank=True
    )
    classe = models.CharField(
        max_length=100
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.estabelecimento}\nRisco: {self.risco}"


class Responsavel(models.Model):
    estabelecimento = models.ForeignKey(
        Estabelecimento, 
        on_delete=models.CASCADE, 
        related_name="responsavel",
        verbose_name="Responsável"
    )
    nome = models.CharField(
        max_length=255
    )
    nacionalidade = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    naturalidade = models.CharField(
        max_length=100, 
        blank=True,
        null=True
    )
    estado_civil = models.CharField(
        max_length=50, 
        blank=True,
        null=True
    )
    rg = models.CharField(
        max_length=20, 
        blank=True,
        null=True
    )
    profissao = models.CharField(
        max_length=100, 
        blank=True,
        null=True
    )
    cpf = models.CharField(
        max_length=14,
    )
    logradouro = models.CharField(
        max_length=255,
        verbose_name="Endereço"
    )
    numero = models.CharField(
        max_length=20
    )
    bairro = models.CharField(
        max_length=100
    )
    cidade = models.CharField(
        max_length=100
    )
    uf = models.CharField(
        max_length=2
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Telefone"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Estabelecimento: #{self.estabelecimento_id} Responsável: {self.nome}"


class RTResponsavel(models.Model):
    estabelecimento = models.ForeignKey(
        Estabelecimento, 
        on_delete=models.CASCADE, 
        related_name="responsavel_tecnico",
        verbose_name="Responsável Técnico"
    )
    nome = models.CharField(
        max_length=255, 
        blank=True
    )
    nacionalidade = models.CharField(
        max_length=100, 
        blank=True
    )
    naturalidade = models.CharField(
        max_length=100, 
        blank=True
    )
    estado_civil = models.CharField(
        max_length=50, 
        blank=True
    )
    rg = models.CharField(
        max_length=20, 
        blank=True
    )
    profissao = models.CharField(
        max_length=100, 
        blank=True
    )
    rg_conselho = models.CharField(
        max_length=50, 
        blank=True
    )
    cpf = models.CharField(
        max_length=14, 
        blank=True
    )
    logradouro = models.CharField(
        max_length=255, 
        blank=True
    )
    numero = models.CharField(
        max_length=20, 
        blank=True
    )
    bairro = models.CharField(
        max_length=100, 
        blank=True
    )
    cidade = models.CharField(
        max_length=100, 
        blank=True
    )
    uf = models.CharField(
        max_length=2, 
        blank=True
    )
    phone = models.CharField(
        max_length=20, 
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "register_rt_responsavel"
        verbose_name = "responsável técnico"
        verbose_name_plural = "responsáveis técnicos"

    def __str__(self):
        return f"RT: {self.nome}\nEstabelecimento: {self.estabelecimento_id}"


class Vigilancia(models.Model):


    class Status(models.TextChoices):
        A_FAZER = "a_fazer", "A fazer"
        CONCLUIDO = "concluido", "Concluído"
        PENDENTE = "pendente", "Pendente"


    class Relatado(models.TextChoices):
        APLICADO = "aplicado", "Aplicado"
        NAO_REQUERIDO = "nao_requerido", "Não Requerido"


    estabelecimento = models.ForeignKey(
        Estabelecimento, 
        on_delete=models.CASCADE, 
        related_name="fiscalizacoes",
    )
    fiscal = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="fiscalizacoes",
    )
    inspecao_status = models.CharField(
        max_length=10, 
        choices=Status.choices, 
        default=Status.A_FAZER,
        verbose_name="Inspeção - Status"
    )
    plano_aplicado = models.CharField(
        max_length=15, 
        choices=Relatado.choices, 
        default=Relatado.NAO_REQUERIDO,
        verbose_name="Plano de Trabalho"
    )
    plano_status = models.CharField(
        max_length=10, 
        choices=Status.choices, 
        blank=True,
        null=True,
        verbose_name="Plano de Trabalho - Status"
    )
    termo_ciencia = models.CharField(
        max_length=15, 
        choices=Relatado.choices, 
        default=Relatado.NAO_REQUERIDO,
        verbose_name="Termo de Ciência"
    )
    termo_status = models.CharField(
        max_length=10, 
        choices=Status.choices, 
        blank=True,
        null=True,
        verbose_name="Termo de Ciência - Status"
    )
    interdicao = models.CharField(
        max_length=15, 
        choices=Relatado.choices, 
        default=Relatado.NAO_REQUERIDO,
        verbose_name="Interdição"
    )
    interdicao_status = models.CharField(
        max_length=10, 
        choices=Status.choices, 
        blank=True,
        null=True,
        verbose_name="Interdição - Status"
    )
    processo = models.CharField(
        max_length=15, 
        choices=Relatado.choices, 
        default=Relatado.NAO_REQUERIDO,
        verbose_name="Processo"
    )
    processo_status = models.CharField(
        max_length=10, 
        choices=Status.choices, 
        blank=True,
        null=True,
        verbose_name="Processo - Status"
    )
    ano_previsto = models.IntegerField(
        blank=True, 
        null=True
    )
    mes_previsto = models.IntegerField(
        blank=True, 
        null=True, 
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    data_realizacao = models.DateField(
        blank=True, 
        null=True
    )
    data_alvara = models.DateField(
        blank=True, 
        null=True,
        verbose_name="Data do Alvará"
    )
    obs = models.TextField(
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Vigilância Inspeção"
        verbose_name_plural = "Vigilância Inspeções"



    def __str__(self):
        return f"{self.estabelecimento}\n{self.get_inspecao_status_display()}"

def caminho_documento(instance, filename):
    id_pasta = (
        instance.id if instance.id else f"est_{instance.estabelecimento.id}"
    )
    return os.path.join("documentos", str(id_pasta), filename)

class Documento(models.Model):
    
    class TipoDocumento(models.TextChoices):
        ALVARA = "alvara", "Alvará"
        TERMO_CIENCIA = "t_ciencia", "Termo de Ciência"
        RELATORIO = "relatorio", "Relatório"
        PROCESSO = "processo", "Processo"   
        OUTRO = "outro", "Outros"


    estabelecimento = models.ForeignKey(
        Estabelecimento, 
        on_delete=models.CASCADE, 
        related_name="documentos",
    )
    tipo_documento = models.CharField(
        max_length=20,
        choices=TipoDocumento.choices,
        default=TipoDocumento.OUTRO,
        verbose_name="Tipo de Documento"
    )
    nome = models.CharField(
        max_length=255
    )
    arquivo = models.FileField(
        upload_to=caminho_documento
    )
    data_envio = models.DateField(
        auto_now_add=True
    )
    enviado_por = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name="documentos_enviados",
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    def __str__(self):
        return self.nome
