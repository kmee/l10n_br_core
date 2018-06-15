# -*- coding: utf-8 -*-
#
# Copyright 2017 KMEE
#   Wagner Pereira <wagner.pereira@kmee.com.br>
# Copyright 2018 ABGF - Wagner Pereira <wagner.pereira@abgf.gov.br>
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl)
#

from openerp import api, fields, models, _


class MotivoDesligamento(models.Model):
    _name = 'sped.motivo_desligamento'
    _description = 'Motivos de Desligamento'
    _order = 'name'
    _sql_constraints = [
        ('codigo',
         'unique(codigo)',
         'Este código já existe !'
         )
    ]

    codigo = fields.Char(
        size=2,
        string='Codigo',
        required=True,
    )
    nome = fields.Char(
        string='Nome',
        required=True,
    )
    name = fields.Char(
        compute='_compute_name',
        store=True,
    )
    descricao = fields.Text(
        string='Descrição',
    )

    @api.onchange('codigo')
    def _valida_codigo(self):
        for motivo in self:
            if motivo.codigo:
                if motivo.codigo.isdigit():
                    motivo.codigo = motivo.codigo.zfill(2)
                else:
                    res = {'warning': {
                        'title': _('Código Incorreto!'),
                        'message': _('Campo Código somente aceita números!'
                                     '- Corrija antes de salvar')
                    }}
                    motivo.codigo = False
                    return res

    @api.depends('codigo', 'nome')
    def _compute_name(self):
        for motivo in self:
            motivo.name = motivo.codigo + '-' + motivo.nome
