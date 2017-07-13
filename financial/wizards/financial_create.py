# -*- coding: utf-8 -*-
# Copyright 2017 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FinancialInstallment(models.Model):

    _name = 'financial.installment'
    _inherit = ['abstract.financial']
    _rec_name = 'document_number' # FIXME: criar display name correto
    @api.depends('amount_document', 'amount_discount')
    def _compute_totals(self):
        for record in self:
            record.amount_total = \
                record.amount_document - record.amount_discount

    @api.depends('line_ids.generated_move')
    def _compute_moves_created(self):
        for record in self:
            record.moves_created = record.line_ids and all(
                [x.generated_move for x in record.line_ids])

    line_ids = fields.One2many(
        comodel_name='financial.installment.line',
        inverse_name='financial_move_id',
        # readonly=True,
    )
    payment_term_id = fields.Many2one(
        string='Payment Term',
        comodel_name='account.payment.term',
        required=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string=u'Analytic account',
    )
    document_number = fields.Char(
        required=True,
    )
    date_document = fields.Date(
        string=u'Financial date',
        default=fields.Date.context_today,
    )
    amount_document = fields.Float(
        required=False,
    )
    amount_total = fields.Monetary(
        string=u'Total',
        readonly=True,
        compute='_compute_totals',
    )
    amount_discount = fields.Monetary(
        string=u'Discount',
    )
    moves_created = fields.Boolean(
        compute='_compute_moves_created',
        copy=False
    )
    generated_move_line_ids = fields.One2many(
        comodel_name='financial.move',
        inverse_name='installment_line_id',
        string=u'Generated Lines'
    )

    @api.onchange('payment_term_id', 'document_number',
                  'date_document', 'amount_document')
    def onchange_fields(self):
        res = {}
        if not (self.payment_term_id and self.document_number and
                self.date_document and self.amount_document > 0.00):
            return res

        computations = self.payment_term_id.compute(
            self.amount_document, self.date_document)[0]
        payment_ids = []
        for idx, item in enumerate(computations):
            payment = dict(
                document_item=self.document_number + '/' + str(idx + 1),
                date_maturity=item[0],
                amount_document=item[1],
            )
            payment_ids.append((0, False, payment))
        self.line_ids = payment_ids

    def _prepare_move_item(self, item):
        return {
            'document_number': item.document_item,
            'date_maturity': item.date_maturity,
            'amount_document': item.amount_document,
        }

    def _prepare_financial_move(self):
        return {
            'date_document': self.date_document,
            'type': self.type,
            'document_type_id': self.document_type_id.id,
            'partner_id': self.partner_id.id,
            'bank_id': self.bank_id.id,
            'company_id': self.company_id and self.company_id.id,
            'currency_id': self.currency_id.id,
            # 'payment_term_id':
            #     self.payment_term_id and self.payment_term_id.id or False,
            'account_id':
                self.account_id and
                self.account_id.id or False,
            # 'analytic_account_id':
            #     self.analytic_account_id and
            #     self.analytic_account_id.id or False,
            # 'payment_mode_id':
            #     self.payment_mode_id and
            #     self.payment_mode_id.id or False,
            'note': self.note,
            'lines': [
                self._prepare_move_item(item) for item in self.line_ids
            ],
        }

    @api.multi
    def compute(self):
        financial_move = self.env['financial.move']
        if not self.moves_created:
            p = self._prepare_financial_move()
            financial_move = financial_move._create_from_dict(p)
            self.generated_move_line_ids = financial_move
            for line in self.line_ids:
                line.generated_move_id = financial_move.search([
                    ('document_number', '=', line.document_item),
                    ('amount_document', '=', line.amount_document),
                    ('date_maturity', '=', line.date_maturity),
                 ], limit=1)
                if line.generated_move_id:
                    line.generated_move = True
            financial_move.action_confirm()
        type = financial_move and financial_move[0].type
        return financial_move.action_view_financial(type)


class FinancialInstallmentLine(models.Model):

    _name = 'financial.installment.line'

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string=u'Currency',
    )
    document_item = fields.Char()
    date_document = fields.Date(
        string=u"Document date",
    )
    date_maturity = fields.Date(
        string=u"Due date",
    )
    amount_document = fields.Float(
        string=u"Document amount",
    )
    financial_move_id = fields.Many2one(
        comodel_name='financial.installment',

    )
    generated_move_id = fields.Many2one(
        comodel_name='financial.move'
    )
    generated_move = fields.Boolean()
