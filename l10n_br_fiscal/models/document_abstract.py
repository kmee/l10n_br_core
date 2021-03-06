# Copyright (C) 2019  Renato Lima - Akretion <renato.lima@akretion.com.br>
# Copyright (C) 2019  Luis Felipe Mileo - KMEE <mileo@kmee.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..constants.fiscal import (
    TAX_FRAMEWORK,
    DOCUMENT_ISSUER,
    DOCUMENT_ISSUER_COMPANY)


class DocumentAbstract(models.AbstractModel):
    _name = "l10n_br_fiscal.document.abstract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Fiscal Document Abstract"

    """ Implementação base dos documentos fiscais

    Devemos sempre ter em mente que o modelo que vai usar este módulo abstrato
     tem diversos metodos importantes e a intenção que os módulos da OCA que
     extendem este modelo, funcionem se possível sem a necessidade de
     codificação extra.

    É preciso também estar atento que o documento fiscal tem dois estados:

    - Estado do documento eletrônico / não eletônico: state_edoc
    - Estado FISCAL: state_fiscal

    O estado fiscal é um campo que é alterado apenas algumas vezes pelo código
    e é de responsabilidade do responsável fiscal pela empresa de manter a
    integridade do mesmo, pois ele não tem um fluxo realmente definido e
    interfere no lançamento do registro no arquivo do SPED FISCAL.
    """

    @api.depends("line_ids")
    def _compute_amount(self):
        for record in self:
            record.amount_untaxed = sum(
                line.amount_untaxed for line in record.line_ids)
            record.amount_icms_base = sum(
                line.icms_base for line in record.line_ids)
            record.amount_icms_value = sum(
                line.icms_value for line in record.line_ids)
            record.amount_ipi_base = sum(
                line.ipi_base for line in record.line_ids)
            record.amount_ipi_value = sum(
                line.ipi_value for line in record.line_ids)
            record.amount_pis_base = sum(
                line.pis_base for line in record.line_ids)
            record.amount_pis_value = sum(
                line.pis_value for line in record.line_ids)
            record.amount_pis_ret_base = sum(
                line.pis_wh_base for line in record.line_ids)
            record.amount_pis_ret_value = sum(
                line.pis_wh_value for line in record.line_ids)
            record.amount_cofins_base = sum(
                line.cofins_base for line in record.line_ids)
            record.amount_cofins_value = sum(
                line.cofins_value for line in record.line_ids)
            record.amount_cofins_ret_base = sum(
                line.cofins_wh_base for line in record.line_ids)
            record.amount_cofins_ret_value = sum(
                line.cofins_wh_value for line in record.line_ids)
            record.amount_csll_base = sum(
                line.csll_base for line in record.line_ids)
            record.amount_csll_value = sum(
                line.csll_value for line in record.line_ids)
            record.amount_csll_ret_base = sum(
                line.csll_wh_base for line in record.line_ids)
            record.amount_csll_ret_value = sum(
                line.csll_wh_value for line in record.line_ids)
            record.amount_issqn_base = sum(
                line.issqn_base for line in record.line_ids)
            record.amount_issqn_value = sum(
                line.issqn_value for line in record.line_ids)
            record.amount_issqn_ret_base = sum(
                line.issqn_wh_base for line in record.line_ids)
            record.amount_issqn_ret_value = sum(
                line.issqn_wh_value for line in record.line_ids)
            record.amount_irpj_base = sum(
                line.irpj_base for line in record.line_ids)
            record.amount_irpj_value = sum(
                line.irpj_value for line in record.line_ids)
            record.amount_irpj_ret_base = sum(
                line.irpj_wh_base for line in record.line_ids)
            record.amount_irpj_ret_value = sum(
                line.irpj_wh_value for line in record.line_ids)
            record.amount_inss_base = sum(
                line.inss_base for line in record.line_ids)
            record.amount_inss_value = sum(
                line.inss_value for line in record.line_ids)
            record.amount_inss_wh_base = sum(
                line.inss_wh_base for line in record.line_ids)
            record.amount_inss_wh_value = sum(
                line.inss_wh_value for line in record.line_ids)
            record.amount_tax = sum(
                line.amount_tax for line in record.line_ids)
            record.amount_discount = sum(
                line.discount_value for line in record.line_ids)
            record.amount_insurance_value = sum(
                line.insurance_value for line in record.line_ids)
            record.amount_other_costs_value = sum(
                line.other_costs_value for line in record.line_ids)
            record.amount_freight_value = sum(
                line.freight_value for line in record.line_ids)
            record.amount_total = sum(
                line.amount_total for line in record.line_ids)

    is_edoc_printed = fields.Boolean(string="Impresso", readonly=True)

    # used mostly to enable _inherits of account.invoice on fiscal_document
    # when existing invoices have no fiscal document.
    active = fields.Boolean(
        string="Active",
        default=True)

    number = fields.Char(
        string="Number",
        copy=False,
        index=True)

    key = fields.Char(
        string="key",
        copy=False,
        index=True)

    issuer = fields.Selection(
        selection=DOCUMENT_ISSUER,
        default=DOCUMENT_ISSUER_COMPANY,
        required=True,
        string="Issuer")

    date = fields.Datetime(
        string="Date",
        copy=False)

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        index=True,
        default=lambda self: self.env.user)

    document_type_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.type",
        )

    operation_name = fields.Char(
        string="Operation Name")

    document_electronic = fields.Boolean(
        related="document_type_id.electronic",
        string="Electronic?",
        store=True)

    date_in_out = fields.Datetime(
        string="Date Move",
        copy=False)

    document_serie_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.serie",
        domain="[('active', '=', True),"
               "('document_type_id', '=', document_type_id)]")

    document_serie = fields.Char(
        string="Serie Number")

    fiscal_document_related_ids = fields.One2many(
        comodel_name='l10n_br_fiscal.document.related',
        inverse_name='fiscal_document_id',
        string='Fiscal Document Related')

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner")

    partner_legal_name = fields.Char(
        string="Legal Name")

    partner_name = fields.Char(
        string="Name")

    partner_cnpj_cpf = fields.Char(
        string="CNPJ")

    partner_inscr_est = fields.Char(
        string="State Tax Number")

    partner_inscr_mun = fields.Char(
        string="Municipal Tax Number")

    partner_suframa = fields.Char(
        string="Suframa")

    partner_cnae_main_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.cnae",
        string="Main CNAE")

    partner_tax_framework = fields.Selection(
        selection=TAX_FRAMEWORK,
        string="Tax Framework")

    partner_shipping_id = fields.Many2one(
        comodel_name="res.partner",
        string="Shipping Address")

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env["res.company"]._company_default_get(
            "l10n_br_fiscal.document"))

    processador_edoc = fields.Selection(
        related="company_id.processador_edoc",
        store=True)

    company_legal_name = fields.Char(
        string="Company Legal Name",)

    company_name = fields.Char(
        string="Company Name",
        size=128)

    company_cnpj_cpf = fields.Char(
        string="Company CNPJ",
    )

    company_inscr_est = fields.Char(
        string="Company State Tax Number",
    )

    company_inscr_mun = fields.Char(
        string="Company Municipal Tax Number",
    )

    company_suframa = fields.Char(
        string="Company Suframa",
    )

    company_cnae_main_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.cnae",
        string="Company Main CNAE")

    company_tax_framework = fields.Selection(
        selection=TAX_FRAMEWORK,
        string="Company Tax Framework")

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.user.company_id.currency_id,
        store=True,
        readonly=True)

    amount_untaxed = fields.Monetary(
        string="Amount Untaxed",
        compute="_compute_amount")

    amount_icms_base = fields.Monetary(
        string="ICMS Base",
        compute="_compute_amount")

    amount_icms_value = fields.Monetary(
        string="ICMS Value",
        compute="_compute_amount")

    amount_ipi_base = fields.Monetary(
        string="IPI Base",
        compute="_compute_amount")

    amount_ipi_value = fields.Monetary(
        string="IPI Value",
        compute="_compute_amount")

    amount_pis_base = fields.Monetary(
        string="PIS Base",
        compute="_compute_amount")

    amount_pis_value = fields.Monetary(
        string="PIS Value",
        compute="_compute_amount")

    amount_pis_ret_base = fields.Monetary(
        string="PIS Ret Base",
        compute="_compute_amount")

    amount_pis_ret_value = fields.Monetary(
        string="PIS Ret Value",
        compute="_compute_amount")

    amount_cofins_base = fields.Monetary(
        string="COFINS Base",
        compute="_compute_amount")

    amount_cofins_value = fields.Monetary(
        string="COFINS Value",
        compute="_compute_amount")

    amount_cofins_ret_base = fields.Monetary(
        string="COFINS Ret Base",
        compute="_compute_amount")

    amount_cofins_ret_value = fields.Monetary(
        string="COFINS Ret Value",
        compute="_compute_amount")

    amount_issqn_base = fields.Monetary(
        string="ISSQN Base",
        compute="_compute_amount")

    amount_issqn_value = fields.Monetary(
        string="ISSQN Value",
        compute="_compute_amount")

    amount_issqn_ret_base = fields.Monetary(
        string="ISSQN Ret Base",
        compute="_compute_amount")

    amount_issqn_ret_value = fields.Monetary(
        string="ISSQN Ret Value",
        compute="_compute_amount")

    amount_csll_base = fields.Monetary(
        string="CSLL Base",
        compute="_compute_amount")

    amount_csll_value = fields.Monetary(
        string="CSLL Value",
        compute="_compute_amount")

    amount_csll_ret_base = fields.Monetary(
        string="CSLL Ret Base",
        compute="_compute_amount")

    amount_csll_ret_value = fields.Monetary(
        string="CSLL Ret Value",
        compute="_compute_amount")

    amount_irpj_base = fields.Monetary(
        string="IRPJ Base",
        compute="_compute_amount")

    amount_irpj_value = fields.Monetary(
        string="IRPJ Value",
        compute="_compute_amount")

    amount_irpj_ret_base = fields.Monetary(
        string="IRPJ Ret Base",
        compute="_compute_amount")

    amount_irpj_ret_value = fields.Monetary(
        string="IRPJ Ret Value",
        compute="_compute_amount")

    amount_inss_base = fields.Monetary(
        string="INSS Base",
        compute="_compute_amount")

    amount_inss_value = fields.Monetary(
        string="INSS Value",
        compute="_compute_amount")

    amount_inss_wh_base = fields.Monetary(
        string="INSS Ret Base",
        compute="_compute_amount")

    amount_inss_wh_value = fields.Monetary(
        string="INSS Ret Value",
        compute="_compute_amount")

    amount_tax = fields.Monetary(
        string="Amount Tax",
        compute="_compute_amount")

    amount_total = fields.Monetary(
        string="Amount Total",
        compute="_compute_amount")

    amount_discount = fields.Monetary(
        string="Amount Discount",
        compute="_compute_amount")

    amount_insurance_value = fields.Monetary(
        string="Insurance Value",
        default=0.00,
        compute="_compute_amount")

    amount_other_costs_value = fields.Monetary(
        string="Other Costs",
        default=0.00,
        compute="_compute_amount")

    amount_freight_value = fields.Monetary(
        string="Freight Value",
        default=0.00,
        compute="_compute_amount")

    amount_change_value = fields.Monetary(
        string="Change Value",
        default=0.00,
        compute="_compute_payment_change_value")

    amount_payment_value = fields.Monetary(
        string="Payment Value",
        default=0.00,
        compute="_compute_payment_change_value")

    amount_missing_payment_value = fields.Monetary(
        string="Missing Payment Value",
        default=0.00,
        compute="_compute_payment_change_value")

    line_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.document.line.abstract",
        inverse_name="document_id",
        string="Document Lines")

    #
    # Duplicatas e pagamentos
    #
    payment_term_id = fields.Many2one(
        comodel_name='l10n_br_fiscal.payment.term',
        string='Condição de pagamento',
        ondelete='restrict',
    )
    financial_ids = fields.One2many(
        comodel_name='l10n_br_fiscal.payment.line',
        inverse_name='document_id',
        string='Duplicatas',
        copy=True,
    )
    fiscal_payment_ids = fields.One2many(
        comodel_name='l10n_br_fiscal.payment',
        inverse_name='document_id',
        string='Pagamentos',
        copy=True,
    )

    @api.multi
    def name_get(self):
        return [(r.id, '{0} - Série: {1} - Número: {2}'.format(
            r.document_type_id.name,
            r.document_serie,
            r.number)) for r in self]

    @api.model
    def _create_serie_number(self, document_serie_id, document_date):
        document_serie = self.env['l10n_br_fiscal.document.serie'].browse(
            document_serie_id)
        number = document_serie.internal_sequence_id.with_context(
            ir_sequence_date=document_date)._next()
        invalids = \
            self.env['l10n_br_fiscal.document.invalidate.number'].search([
                ('state', '=', 'done'),
                ('document_serie_id', '=', document_serie_id)])
        invalid_numbers = []
        for invalid in invalids:
            invalid_numbers += range(
                invalid.number_start, invalid.number_end + 1)
        if int(number) in invalid_numbers:
            return self._create_serie_number(document_serie_id, document_date)
        return number

    @api.model
    def create(self, values):
        if not values.get('date'):
            values['date'] = self._date_server_format()

        if values.get('document_serie_id') and not values.get('number'):
            values['number'] = self._create_serie_number(
                values.get('document_serie_id'), values['date'])

        # if values.get('financial_ids') and values.get('fiscal_payment_ids'):
        #     values['fiscal_payment_ids'][0][2]['line_ids'] = \
        #         values.pop('financial_ids')

        return super(DocumentAbstract, self).create(values)

    @api.onchange("document_serie_id")
    def _onchange_document_serie_id(self):
        if self.document_serie_id and self.issuer == DOCUMENT_ISSUER_COMPANY:
            self.document_serie = self.document_serie_id.code

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self.company_id:
            self.company_legal_name = self.company_id.legal_name
            self.company_name = self.company_id.name
            self.company_cnpj_cpf = self.company_id.cnpj_cpf
            self.company_inscr_est = self.company_id.inscr_est
            self.company_inscr_mun = self.company_id.inscr_mun
            self.company_suframa = self.company_id.suframa
            self.company_cnae_main_id = self.company_id.cnae_main_id
            self.company_tax_framework = self.company_id.tax_framework

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_legal_name = self.partner_id.legal_name
            self.partner_name = self.partner_id.name
            self.partner_cnpj_cpf = self.partner_id.cnpj_cpf
            self.partner_inscr_est = self.partner_id.inscr_est
            self.partner_inscr_mun = self.partner_id.inscr_mun
            self.partner_suframa = self.partner_id.suframa
            self.partner_cnae_main_id = self.partner_id.cnae_main_id
            self.partner_tax_framework = self.partner_id.tax_framework

    @api.onchange("operation_id")
    def _onchange_operation_id(self):
        if self.operation_id:
            self.operation_name = self.operation_id.name

    def generate_financial(self):
        for record in self:
            if self.env.context.get('action_document_confirm'):
                if (record.amount_missing_payment_value > 0 and
                        not record.payment_term_id):
                    raise UserError(
                        _("O Valor dos lançamentos financeiros é "
                          "menor que o valor da nota."),
                    )
                continue

            if record.payment_term_id and self.company_id and self.currency_id:
                record.financial_ids.unlink()
                record.fiscal_payment_ids.unlink()
                vals = {
                    'payment_term_id': self.payment_term_id.id,
                    'amount': self.amount_missing_payment_value,
                    'currency_id': self.currency_id.id,
                    'company_id': self.company_id.id,
                }
                vals.update(self.fiscal_payment_ids._compute_payment_vals(
                    payment_term_id=self.payment_term_id,
                    currency_id=self.currency_id,
                    company_id=self.company_id,
                    amount=self.amount_missing_payment_value, date=self.date)
                )
                self.fiscal_payment_ids = self.fiscal_payment_ids.new(vals)
                for line in self.fiscal_payment_ids.mapped('line_ids'):
                    line.document_id = self

            elif record.fiscal_payment_ids:
                record.financial_ids.unlink()
                record.fiscal_payment_ids.unlink()

    @api.onchange("fiscal_payment_ids", "payment_term_id")
    def _onchange_fiscal_payment_ids(self):
        financial_ids = []

        for payment in self.fiscal_payment_ids:
            for line in payment.line_ids:
                financial_ids.append(line.id)
        self.financial_ids = [(6, 0, financial_ids)]

    # @api.onchange("payment_term_id", "company_id", "currency_id",
    #               "amount_missing_payment_value", "date")
    # def _onchange_payment_term_id(self):
    #     if (self.payment_term_id and self.company_id and
    #             self.currency_id):
    #
    #         self.financial_ids.unlink()
    #
    #         vals = {
    #             'payment_term_id': self.payment_term_id.id,
    #             'amount': self.amount_missing_payment_value,
    #             'currency_id': self.currency_id.id,
    #             'company_id': self.company_id.id,
    #          }
    #         vals.update(self.fiscal_payment_ids._compute_payment_vals(
    #             payment_term_id=self.payment_term_id, currency_id=self.currency_id,
    #             company_id=self.company_id,
    #             amount=self.amount_missing_payment_value, date=self.date)
    #         )
    #         self.fiscal_payment_ids = self.fiscal_payment_ids.new(vals)
    #         for line in self.fiscal_payment_ids.mapped('line_ids'):
    #             line.document_id = self

    @api.depends("amount_total", "fiscal_payment_ids")
    def _compute_payment_change_value(self):
        payment_value = 0
        for payment in self.fiscal_payment_ids:
            for line in payment.line_ids:
                payment_value += line.amount

        self.amount_payment_value = payment_value

        change_value = payment_value - self.amount_total
        self.amount_change_value = change_value if change_value >= 0 else 0

        missing_payment = self.amount_total - payment_value
        self.amount_missing_payment_value = missing_payment \
            if missing_payment >= 0 else 0
