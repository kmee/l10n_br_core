# Copyright (C) 2009  Renato Lima - Akretion, Gabriel C. Stabel
# Copyright (C) 2012  Raphaël Valyi - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'l10n_br_fiscal.document.mixin']

    @api.model
    def _default_operation(self):
        return self.env.user.company_id.purchase_fiscal_operation_id

    @api.model
    def _operation_domain(self):
        domain = [
            ('state', '=', 'approved'),
            ('fiscal_type', 'in', ('purchase', 'other', 'purchase_refund'))]
        return domain

    operation_id = fields.Many2one(
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=_default_operation,
        domain=lambda self: self._operation_domain(),
    )

    cnpj_cpf = fields.Char(
        string='CNPJ/CPF',
        related='partner_id.cnpj_cpf',
    )

    legal_name = fields.Char(
        string='Legal Name',
        related='partner_id.legal_name',
    )

    ie = fields.Char(
        string='State Tax Number/RG',
        related='partner_id.inscr_est',
    )

    @api.onchange('operation_id')
    def _onchange_operation_id(self):
        self.fiscal_position_id = self.operation_id.fiscal_position_id
