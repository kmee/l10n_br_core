# -*- coding: utf-8 -*-
#
# Copyright 2017 KMEE INFORMATICA LTDA
#   Luis Felipe Miléo <mileo@kmee.com.br>
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl)
#

from __future__ import division, print_function, unicode_literals

import os
import logging

from odoo import api, fields, models
from odoo.addons.l10n_br_base.constante_tributaria import *
from odoo.exceptions import UserError, Warning


_logger = logging.getLogger(__name__)

try:
    from pybrasil.inscricao import limpa_formatacao
    from pybrasil.data import (parse_datetime, UTC, data_hora_horario_brasilia,
                               agora)
    from pybrasil.valor import formata_valor
    from pybrasil.valor.decimal import Decimal as D
    from pybrasil.template import TemplateBrasil

    from satcomum.ersat import ChaveCFeSAT
    from satcfe.entidades import *
    from satcfe.excecoes import ExcecaoRespostaSAT, ErroRespostaSATInvalida

except (ImportError, IOError) as err:
    _logger.debug(err)


class SpedDocumento(models.Model):
    _inherit = 'sped.documento'

    @api.multi
    def _buscar_configuracoes_pdv(self):
        self.configuracoes_pdv = self.env.user.configuracoes_sat_cfe

    configuracoes_pdv = fields.Many2one(
        string=u"Configurações para a venda",
        comodel_name="pdv.config",
        compute=_buscar_configuracoes_pdv
    )

    pagamento_autorizado_cfe = fields.Boolean(
        string=u"Pagamento Autorizado",
        readonly=True,
        default=False
    )

    def executa_depois_autorizar(self):
        #
        # Este método deve ser alterado por módulos integrados, para realizar
        # tarefas de integração necessárias depois de autorizar uma NF-e,
        # por exemplo, criar lançamentos financeiros, movimentações de
        # estoque etc.
        #
        self.ensure_one()

        if self.modelo != MODELO_FISCAL_CFE:
            super(SpedDocumento, self)._compute_permite_cancelamento()
            return

        if self.emissao != TIPO_EMISSAO_PROPRIA:
            super(SpedDocumento, self)._compute_permite_cancelamento()
            return

        #
        # Envia o email da nota para o cliente
        #
        mail_template = None
        if self.operacao_id.mail_template_id:
            mail_template = self.operacao_id.mail_template_id
        else:
            if self.modelo == MODELO_FISCAL_NFE and \
                    self.empresa_id.mail_template_nfe_autorizada_id:
                mail_template = \
                    self.empresa_id.mail_template_nfe_autorizada_id
            elif self.modelo == MODELO_FISCAL_NFCE and \
                    self.empresa_id.mail_template_nfce_autorizada_id:
                mail_template = \
                    self.empresa_id.mail_template_nfce_autorizada_id

        if mail_template is None:
            return

        self.envia_email(mail_template)

    @api.depends('modelo', 'emissao', 'importado_xml', 'situacao_nfe')
    def _compute_permite_alteracao(self):
        super(SpedDocumento, self)._compute_permite_alteracao()

        for documento in self:
            if not self.modelo == MODELO_FISCAL_CFE:
                super(SpedDocumento, documento)._compute_permite_alteracao()
                continue

            if documento.emissao != TIPO_EMISSAO_PROPRIA:
                super(SpedDocumento, documento)._compute_permite_alteracao()
                continue

            #
            # É emissão própria de NF-e ou NFC-e, permite alteração
            # somente quando estiver em digitação ou rejeitada
            #
            documento.permite_alteracao = documento.permite_alteracao or \
                documento.situacao_nfe in (SITUACAO_NFE_EM_DIGITACAO,
                                        SITUACAO_NFE_REJEITADA)

    def processador_cfe(self):
        """
        Busca classe do processador do cadastro da empresa, onde podemos ter três tipos de processamento dependendo
        de onde o equipamento esta instalado:

        - Instalado no mesmo servidor que o Odoo;
        - Instalado na mesma rede local do servidor do Odoo;
        - Instalado em um local remoto onde o browser vai ser responsável por se comunicar com o equipamento

        :return:
        """
        self.ensure_one()

        if self.configuracoes_pdv.tipo_sat == 'local':
            from mfecfe.clientelocal import ClienteSATLocal
            from mfecfe import BibliotecaSAT
            cliente = ClienteSATLocal(
                BibliotecaSAT('/opt/Integrador'),  # FIXME: Caminho do integrador nas configurações
                codigo_ativacao=self.configuracoes_pdv.codigo_ativacao
            )
        elif self.configuracoes_pdv.tipo_sat == 'rede_interna':
            from mfecfe.clientesathub import ClienteSATHub
            cliente = ClienteSATHub(
                self.configuracoes_pdv.ip,
                5000,  # FIXME: Colocar a porta nas configurações
                numero_caixa=int(self.configuracoes_pdv.numero_caixa)
            )
        elif self.configuracoes_pdv.tipo_sat == 'remoto':
            cliente = None
            # NotImplementedError

        return cliente

    def grava_cfe(self, cfe):
        self.ensure_one()
        nome_arquivo = 'envio-cfe.xml'
        conteudo = cfe.documento().encode('utf-8')
        self.arquivo_xml_id = False
        self.arquivo_xml_id = self._grava_anexo(nome_arquivo, conteudo).id

    def grava_cfe_autorizacao(self, cfe):
        self.ensure_one()
        nome_arquivo = self.chave + '-proc-nfe.xml'
        self.arquivo_xml_autorizacao_id = False
        self.arquivo_xml_autorizacao_id = \
            self._grava_anexo(nome_arquivo, cfe).id

    def grava_cfe_cancelamento(self, chave, canc):
        self.ensure_one()
        nome_arquivo = self.chave + '-01-can.xml'
        conteudo = canc.xml.encode('utf-8')
        self.arquivo_xml_cancelamento_id = False
        self.arquivo_xml_cancelamento_id = \
            self._grava_anexo(nome_arquivo, conteudo).id

    def grava_cfe_autorizacao_cancelamento(self, chave, canc):
        self.ensure_one()
        nome_arquivo = chave + '-01-proc-can.xml'
        self.arquivo_xml_autorizacao_cancelamento_id = False
        self.arquivo_xml_autorizacao_cancelamento_id = \
            self._grava_anexo(nome_arquivo, canc).id

    def monta_cfe(self, processador=None):
        self.ensure_one()

        kwargs = {}

        if not self.modelo == MODELO_FISCAL_CFE:
            return

        #
        # Identificação da CF-E
        #
        cnpj_software_house, assinatura, numero_caixa = \
            self._monta_cfe_identificacao()

        #
        # Emitente
        #
        emitente = self._monta_cfe_emitente()

        #
        # Destinatário
        #
        if self.participante_id:
            kwargs['destinatario'] = self._monta_cfe_destinatario()

        #
        # Itens
        #

        detalhamentos = []

        for item in self.item_ids:
            detalhamentos.append(item.monta_cfe())

        #
        # Pagamentos
        #
        pagamentos = []

        self._monta_cfe_pagamentos(pagamentos)

        cfe_venda = CFeVenda(
            CNPJ=limpa_formatacao(cnpj_software_house),
            signAC=assinatura,
            numeroCaixa=2,
            emitente=emitente,
            detalhamentos=detalhamentos,
            pagamentos=pagamentos,
            vCFeLei12741=D(self.vr_ibpt).quantize('0.01'),
            **kwargs
        )
        cfe_venda.validar()
        return cfe_venda

    def _monta_cfe_identificacao(self):
        # FIXME: Buscar dados do cadastro da empresa / cadastro do caixa
        cnpj_software_house = self.configuracoes_pdv.cnpj_software_house
        assinatura = self.configuracoes_pdv.assinatura
        numero_caixa = self.configuracoes_pdv.numero_caixa
        return cnpj_software_house, assinatura, numero_caixa

    def _monta_cfe_emitente(self):
        emitente = Emitente(
                CNPJ=limpa_formatacao(self.configuracoes_pdv.cnpjsh),
                IE=limpa_formatacao(self.configuracoes_pdv.ie),
                indRatISSQN='N'
        )
        emitente.validar()
        return emitente

    def _monta_cfe_destinatario(self,):

        participante = self.participante_id

        #
        # Trata a possibilidade de ausência do destinatário na NFC-e
        #
        if self.modelo == MODELO_FISCAL_CFE and not participante.cnpj_cpf:
            return

        #
        # Participantes estrangeiros tem a ID de estrangeiro sempre começando
        # com EX
        #
        if participante.cnpj_cpf.startswith('EX'):
            # TODO:
            pass
            # dest.idEstrangeiro.valor = \
            #     limpa_formatacao(participante.cnpj_cpf or '')

        elif len(participante.cnpj_cpf or '') == 14:
            return Destinatario(CPF=limpa_formatacao(participante.cnpj_cpf))

        elif len(participante.cnpj_cpf or '') == 18:
            return Destinatario(CNPJ=limpa_formatacao(participante.cnpj_cpf))

    def _monta_cfe_pagamentos(self, pag):
        if self.modelo != MODELO_FISCAL_CFE:
            return

        for pagamento in self.pagamento_ids:
            pag.append(pagamento.monta_cfe())

    def resposta_cfe(self, resposta):
        """

        :param resposta:

        u'123456|06001|Código de ativação inválido||'
        u'123456|06002|SAT ainda não ativado||'
        u'123456|06003|SAT não vinculado ao AC||'
        u'123456|06004|Vinculação do AC não confere||'
        u'123456|06005|Tamanho do CF-e-SAT superior a 1.500KB||'
        u'123456|06006|SAT bloqueado pelo contribuinte||'
        u'123456|06007|SAT bloqueado pela SEFAZ||'
        u'123456|06008|SAT bloqueado por falta de comunicação||'
        u'123456|06009|SAT bloqueado, código de ativação incorreto||'
        u'123456|06010|Erro de validação do conteúdo||'
        u'123456|06098|SAT em processamento. Tente novamente.||'
        u'123456|06099|Erro desconhecido na emissão||'

        resposta.numeroSessao
        resposta.EEEEE
        resposta.CCCC
        resposta.arquivoCFeSAT
        resposta.timeStamp
        resposta.chaveConsulta
        resposta.valorTotalCFe
        resposta.assinaturaQRCODE
        resposta.xml()
        :return:
        """
        from mfecfe.resposta.enviardadosvenda import RespostaEnviarDadosVenda
        resposta_sefaz = RespostaEnviarDadosVenda.analisar(resposta.get('retorno'))

        if resposta_sefaz.EEEEE in '06000':
            self.executa_antes_autorizar()
            self.situacao_nfe = SITUACAO_NFE_AUTORIZADA
            self.executa_depois_autorizar()
            # self.data_hora_autorizacao = fields.Datetime.now()
        elif resposta_sefaz.EEEEE in ('06001', '06002', '06003', '06004', '06005',
                                '06006', '06007', '06008', '06009', '06010',
                                '06098', '06099'):
            self.executa_antes_denegar()
            self.situacao_fiscal = SITUACAO_FISCAL_DENEGADO
            self.situacao_nfe = SITUACAO_NFE_DENEGADA
            self.executa_depois_denegar()
        self.grava_cfe(resposta_sefaz.xml())

    @api.model
    def processar_venda_cfe(self, venda_id):
        venda = self.browse(venda_id)
        return venda.monta_cfe()

    @api.model
    def processar_resposta_cfe(self, venda_id, resposta):
        venda = self.browse(venda_id)
        return venda.resposta_cfe(resposta)

    def _monta_cancelamento(self):
        cnpj_software_house, assinatura, numero_caixa = \
            self._monta_cfe_identificacao()

        destinatario = self._monta_cfe_destinatario()

        return CFeCancelamento(
            chCanc= u'CFe' + self.chave,
            CNPJ=limpa_formatacao(cnpj_software_house),
            signAC=assinatura,
            numeroCaixa=int(numero_caixa),
        )

    def grava_xml_cancelamento(self, chave, canc):
        self.ensure_one()
        nome_arquivo = chave + '-01-can.xml'
        conteudo = canc.documento().encode('utf-8')
        self.arquivo_xml_cancelamento_id = False
        self.arquivo_xml_cancelamento_id = \
            self._grava_anexo(nome_arquivo, conteudo).id

    def grava_xml_autorizacao_cancelamento(self, chave, canc):
        self.ensure_one()
        nome_arquivo = chave + '-01-proc-can.xml'
        conteudo = canc.encode('utf-8')
        self.arquivo_xml_autorizacao_cancelamento_id = False
        self.arquivo_xml_autorizacao_cancelamento_id = \
            self._grava_anexo(nome_arquivo, conteudo).id

    def cancela_nfe(self):
        self.ensure_one()
        result = super(SpedDocumento, self).envia_nfe()
        if not self.modelo == MODELO_FISCAL_CFE:
            return result

        processador = self.processador_cfe()

        try:
            cancelamento = self._monta_cancelamento()

            processo = processador.cancelar_ultima_venda(
                cancelamento.chCanc,
                cancelamento
            )

            #
            # O cancelamento foi aceito e vinculado à CF-E
            #
            if processo.EEEEE in ('07000'):
                #
                # Grava o protocolo de cancelamento
                #
                self.grava_xml_cancelamento(self.chave, cancelamento)
                self.grava_xml_autorizacao_cancelamento(self.chave, processo.xml())

                # data_cancelamento = retevento.infEvento.dhRegEvento.valor
                # data_cancelamento = UTC.normalize(data_cancelamento)
                #
                # self.data_hora_cancelamento = data_cancelamento
                # self.protocolo_cancelamento = \
                #     procevento.retEvento.infEvento.nProt.valor

                #
                # Cancelamento extemporâneo
                #
                self.executa_antes_cancelar()

                if processo.EEEEE != '07000':
                    # FIXME: Verificar se da para cancelar fora do prazo
                    self.situacao_fiscal = SITUACAO_FISCAL_CANCELADO_EXTEMPORANEO
                    self.situacao_nfe = SITUACAO_NFE_CANCELADA
                elif processo.EEEEE == '07000':
                    self.situacao_fiscal = SITUACAO_FISCAL_CANCELADO
                    self.situacao_nfe = SITUACAO_NFE_CANCELADA

                self.executa_depois_cancelar()

        except (ErroRespostaSATInvalida, ExcecaoRespostaSAT) as resposta:
            mensagem = 'Erro no cancelamento'
            mensagem += '\nCódigo: ' + resposta.EEEEE
            mensagem += '\nMotivo: ' + resposta.mensagem
            raise UserError(mensagem)
        except Exception as resposta:

            if not hasattr(resposta, 'resposta'):
                mensagem = 'Erro no cancelamento'
                mensagem += '\nMotivo: ' + resposta.message
                raise UserError(mensagem)

            mensagem = 'Erro no cancelamento'
            mensagem += '\nCódigo: ' + resposta.resposta.EEEEE
            mensagem += '\nMotivo: ' + resposta.resposta.mensagem
            raise UserError(mensagem)

    def envia_nfe(self):
        self.ensure_one()
        result = super(SpedDocumento, self).envia_nfe()
        if not self.modelo == MODELO_FISCAL_CFE:
            return result

        if not self.pagamento_autorizado_cfe:
            self.envia_pagamento()
            if not self.pagamento_autorizado_cfe:
                raise Warning('Pagamento(s) não autorizado(s)!')

        cliente = self.processador_cfe()

        cfe = self.monta_cfe()
        self.grava_cfe(cfe)

        #
        # Processa resposta
        #
        try:
            resposta = cliente.enviar_dados_venda(cfe)
            if resposta.EEEEE in '06000':
                self.executa_antes_autorizar()
                self.executa_depois_autorizar()
                self.data_hora_autorizacao = fields.Datetime.now()

                chave = ChaveCFeSAT(resposta.chaveConsulta)
                self.numero = chave.numero_cupom_fiscal
                self.serie = chave.numero_serie
                self.chave = resposta.chaveConsulta[3:]
                self.grava_cfe_autorizacao(resposta.xml())

                self.situacao_fiscal = SITUACAO_FISCAL_REGULAR
                self.situacao_nfe = SITUACAO_NFE_AUTORIZADA


                # # self.grava_pdf(nfe, procNFe.danfe_pdf)

                # data_autorizacao = protNFe.infProt.dhRecbto.valor
                # data_autorizacao = UTC.normalize(data_autorizacao)

                # self.data_hora_autorizacao = data_autorizacao
                # self.protocolo_autorizacao = protNFe.infProt.nProt.valor
                #

            elif resposta.EEEEE in ('06001', '06002', '06003', '06004', '06005',
                                    '06006', '06007', '06008', '06009', '06010',
                                    '06098', '06099'):
                self.executa_antes_denegar()
                self.situacao_fiscal = SITUACAO_FISCAL_DENEGADO
                self.situacao_nfe = SITUACAO_NFE_DENEGADA
                self.executa_depois_denegar()
        except (ErroRespostaSATInvalida, ExcecaoRespostaSAT) as resposta:
            mensagem = 'Código de retorno: ' + \
                       resposta.EEEEE
            mensagem += '\nMensagem: ' + \
                        resposta.mensagem
            self.mensagem_nfe = mensagem
            self.situacao_nfe = SITUACAO_NFE_REJEITADA
        except Exception as resposta:
            mensagem = 'Código de retorno: ' + \
                       resposta.resposta.EEEEE
            mensagem += '\nMensagem: ' + \
                        resposta.resposta.mensagem
            self.mensagem_nfe = mensagem
            self.situacao_nfe = SITUACAO_NFE_REJEITADA

    @api.multi
    def _verificar_formas_pagamento(self):
        pagamentos_cartoes = []
        for pagamento in self.pagamento_ids:
            if pagamento.condicao_pagamento_id.forma_pagamento in ["03", "04"]:
                pagamentos_cartoes.append(pagamento)

        return pagamentos_cartoes

    def envia_pagamento(self):
        self.ensure_one()
        pagamentos_cartoes = self._verificar_formas_pagamento()
        if not pagamentos_cartoes:
            self.pagamento_autorizado_cfe = True
        else:
            pagamentos_autorizados = True
            config = self.configuracoes_pdv
            from mfecfe import BibliotecaSAT
            from mfecfe import ClienteVfpeLocal
            cliente = ClienteVfpeLocal(
                BibliotecaSAT('/opt/Integrador'),
                chave_acesso_validador=config.chave_acesso_validador
            )

            for duplicata in pagamentos_cartoes:
                if not duplicata.id_fila_status:
                    resposta = cliente.enviar_pagamento(
                        config.chave_requisicao, config.estabelecimento,
                        config.serial_pos, config.cnpjsh, self.bc_icms_proprio,
                        duplicata.valor, config.id_fila_validador,config.multiplos_pag,
                        config.anti_fraude, 'BRL', config.numero_caixa
                    )
                    duplicata.id_fila_status = resposta
                # FIXME status sempre vai ser negativo na homologacao
                # resposta_status_pagamento = cliente.verificar_status_validador(
                #     config.cnpjsh, duplicata.id_fila_status
                # )
                #
                # resposta_status_pagamento = cliente.verificar_status_validador(
                #     config.cnpjsh, '214452'
                # )
                # if resposta_status_pagamento.ValorPagamento == '0' and resposta_status_pagamento.IdFila == '0':
                #     pagamentos_autorizados = False
                #     break

            self.pagamento_autorizado_cfe = pagamentos_autorizados
