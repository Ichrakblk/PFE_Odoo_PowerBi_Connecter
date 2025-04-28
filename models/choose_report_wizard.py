from odoo import models, fields, api

class ChooseReportWizard(models.TransientModel):
    _name = 'choose.report.wizard'
    _description = 'Choisir un rapport à afficher'

    report_main_id = fields.Many2one('power_bi.report', string="Rapport principal", required=True)
    selected_report_id = fields.Many2one('power_bi.report.choice', string="Rapport à choisir"
                                         )

    def action_confirm_selection(self):
        self.report_main_id.selected_report_choice = self.selected_report_id
        return {'type': 'ir.actions.act_window_close'}
