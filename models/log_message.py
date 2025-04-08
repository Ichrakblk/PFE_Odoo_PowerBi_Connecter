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

    def action_download_report(self):
        _logger = logging.getLogger(__name__)
        logs = self.search([('message', '=', 'success')])


        report_action = self.env.ref('custom_powerbi_connector.action_report_log_message')
        _logger.info("Report Action : %s", report_action)


        pdf_report = report_action.report_action(logs)
        _logger.info("Données du rapport : %s", pdf_report)
        if 'datas' in pdf_report:
            _logger.info("Le fichier PDF a été généré.")
        else:
            _logger.warning("Aucune donnée PDF générée.")

        return {
            'type': 'ir.actions.report',
            'report_name': 'custom_powerbi_connector.report_log_message',
            'report_type': 'html',
            'context': {
                'datas': pdf_report.get('datas'),
            },
            'report_file': 'log_report.html',
            'close_on_report_download': True,
        }

    @api.model
    def send_log_report_by_email(self, email_to):
        logs = self.search([('message', '=', 'success')])

        report_action = self.env.ref('custom_powerbi_connector.action_report_log_message')
        pdf_report = report_action.report_action(logs)

        admin_email = self.env.user.email

        mail_values = {
            'subject': f'Log Report - {fields.Datetime.now()}',
            'body_html': '<p>Veuillez trouver ci-joint le rapport des logs.</p>',
            'email_from': admin_email,
            'email_to': admin_email,
        }

        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

        return True

    @api.model
    def create_report_action(self):
        existing_action = self.env.ref('custom_powerbi_connector.action_report_log_message', raise_if_not_found=False)

        if not existing_action:
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
