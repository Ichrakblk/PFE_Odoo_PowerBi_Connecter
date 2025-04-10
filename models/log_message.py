from odoo import models, fields, api
from odoo.exceptions import UserError
import logging


class LogMessage(models.Model):
    _name = 'log.message'
    _description = 'Log Message'
    _order = 'log_date desc'

    log_date = fields.Datetime(string="Log Date", required=True, default=fields.Datetime.now)
    message = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('warning', 'Warning'),
    ], string="Message Type", required=True, default='success')
    log_message = fields.Text(string="Log Message", required=True)

    # Champ pour stocker le fichier PDF
    pdf_file = fields.Binary(string="PDF File", attachment=True)

    # Champ pour afficher l'URL du PDF dans le formulaire
    pdf_url = fields.Char(string="PDF URL")

    @api.model
    def create(self, vals):
        # Créer l'enregistrement et calculer l'URL du PDF
        record = super(LogMessage, self).create(vals)
        record._compute_pdf_url()
        return record

    def write(self, vals):

        result = super(LogMessage, self).write(vals)
        self._compute_pdf_url()
        return result

    def _compute_pdf_url(self):
        """Calculer l'URL du PDF pour chaque enregistrement"""
        for record in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            report_name = 'custom_powerbi_connector.report_log_message'
            pdf_url = f"{base_url}/report/pdf/{report_name}/{record.id}"
            record.pdf_url = pdf_url

    def action_download_report(self):
        """Action pour télécharger le rapport en PDF"""
        if not self:
            raise UserError("Aucun enregistrement sélectionné.")


        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_name = 'custom_powerbi_connector.report_log_message'
        ids = ','.join(str(rec.id) for rec in self)
        pdf_url = f'/report/pdf/{report_name}/{ids}'


        return {
            'type': 'ir.actions.act_url',
            'url': pdf_url,
            'target': 'self',
        }

    @api.model
    def send_log_report_by_email(self, email_to):
        """Envoyer le rapport des logs par email"""
        logs = self.search([('message', '=', 'success')])

        # Obtenir l'action du rapport
        report_action = self.env.ref('custom_powerbi_connector.action_report_log_message')
        pdf_report = report_action.report_action(logs)

        # Créer et envoyer l'email
        admin_email = self.env.user.email
        mail_values = {
            'subject': f'Log Report - {fields.Datetime.now()}',
            'body_html': '<p>Veuillez trouver ci-joint le rapport des logs.</p>',
            'email_from': admin_email,
            'email_to': email_to,
        }

        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

        return True

    @api.model
    def create_report_action(self):
        """Créer une action de rapport si elle n'existe pas déjà"""
        existing_action = self.env.ref('custom_powerbi_connector.action_report_log_message', raise_if_not_found=False)

        if not existing_action:
            # Créer l'action de rapport
            report_action = self.env['ir.actions.report'].create({
                'name': 'Log Report',
                'model': 'log.message',
                'report_type': 'qweb-pdf',
                'report_name': 'custom_powerbi_connector.report_log_message',
                'file': 'custom_powerbi_connector.report_log_message',
                'attachment_use': True,
            })
            print("Action de rapport créée :", report_action)
        else:
            print("L'action de rapport existe déjà.")
