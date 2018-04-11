# -*- coding: utf-8 -*-
# Copyright 2018 KMEE INFORMATICA LTDA
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl)
#

from __future__ import division, print_function, unicode_literals

from odoo import api, fields, models

from odoo.addons.l10n_br_base.constante_tributaria import \
    TIPO_PRODUTO_SERVICO_SERVICOS


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ncm_id = fields.Many2one(
        comodel_name='sped.ncm',
        string='NCM',
    )
    cest_ids = fields.Many2many(
        comodel_name='sped.cest',
        related='ncm_id.cest_ids',
        string='Códigos CEST',
    )
    exige_cest = fields.Boolean(
        string='Exige código CEST?',
        compute='_compute_exige_cest',
    )
    cest_id = fields.Many2one(
        comodel_name='sped.cest',
        string='CEST'
    )
    protocolo_id = fields.Many2one(
        comodel_name='sped.protocolo.icms',
        string='Protocolo/Convênio',
    )
    al_ipi_id = fields.Many2one(
        comodel_name='sped.aliquota.ipi',
        string='Alíquota de IPI',
    )
    al_pis_cofins_id = fields.Many2one(
        comodel_name='sped.aliquota.pis.cofins',
        string='Alíquota de PIS e COFINS',
    )
    codigo_natureza_receita_pis_cofins = fields.Char(
        string='Natureza da receita',
        size=3,
        index=True,
    )
    servico_id = fields.Many2one(
        comodel_name='sped.servico',
        string='Código do serviço',
    )
    nbs_id = fields.Many2one(
        comodel_name='sped.nbs',
        string='NBS',
    )
    unidade_tributacao_ncm_id = fields.Many2one(
        comodel_name='product.uom',
        related='ncm_id.unidade_id',
        string='Unidade para tributação do NCM',
        readonly=True,
    )
    fator_conversao_unidade_tributacao_ncm = fields.Float(
        string='Fator de conversão entre as unidades',
        default=1,
    )
    exige_fator_conversao_unidade_tributacao_ncm = fields.Boolean(
        string='Exige fator de conversão entre as unidades?',
        compute='_compute_exige_fator_conversao_ncm',
    )

    @api.depends('ncm_id', 'uom_id')
    def _compute_exige_fator_conversao_ncm(self):
        for product_template_id in self:
            if (product_template_id.uom_id and
                    product_template_id.unidade_tributacao_ncm_id):
                product_template_id.\
                    exige_fator_conversao_unidade_tributacao_ncm = (
                        product_template_id.uom_id.id !=
                        product_template_id.unidade_tributacao_ncm_id.id
                )
            else:
                product_template_id.\
                    exige_fator_conversao_unidade_tributacao_ncm = False
                product_template_id.\
                    fator_conversao_unidade_tributacao_ncm = 1

    def _ajusta_cest(self):
        for product_template_id in self:
            if not product_template_id.ncm_id:
                product_template_id.exige_cest = False
                product_template_id.cest_id = False
                continue

            if len(product_template_id.ncm_id.cest_ids) == 0:
                product_template_id.exige_cest = False
                product_template_id.cest_id = False
                continue

            product_template_id.exige_cest = True

            if len(product_template_id.ncm_id.cest_ids) == 1:
                product_template_id.cest_id = product_template_id.ncm_id.cest_ids[0].id

    @api.depends('ncm_id')
    def _compute_exige_cest(self):
        self._ajusta_cest()

    @api.onchange('ncm_id')
    def onchange_ncm(self):
        self._ajusta_cest()

    @api.depends('tipo')
    def _onchange_tipo(self):
        for produto in self:
            if produto.tipo == TIPO_PRODUTO_SERVICO_SERVICOS:
                produto.ncm_id = \
                    self.env.ref('sped_imposto.NCM_00000000')
