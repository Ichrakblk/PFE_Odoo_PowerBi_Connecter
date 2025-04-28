from odoo import models, fields, api

class ChooseReportWizard(models.TransientModel):
    _name = 'choose.report.wizard'
    _description = 'Choisir un rapport Power BI'

    report_id = fields.Many2one('power_bi.report.choice', string="Rapport à afficher")

    def action_select_report(self):
        active_id = self.env.context.get('active_id')
        main_report = self.env['power_bi.report'].browse(active_id)
        if main_report and self.report_id:
            main_report.selected_report_choice = self.report_id
            main_report.action_test_report_embed()
