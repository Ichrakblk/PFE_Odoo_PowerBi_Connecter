from odoo import models, fields, api

class PowerBIReportChoice(models.Model):
    _name = 'power_bi.report.choice'
    _description = 'Choix de rapport Power BI'

    name = fields.Char(string="Nom du rapport", compute="_compute_name", store=True)
    report_id = fields.Char(string="Report ID")
    workspace_id = fields.Many2one('power_bi.workspace', string="Workspace")

    report_main_id = fields.Many2one('power_bi.report', string="Rapport parent", required=True, ondelete="cascade")
    report_name = fields.Char(string="Nom du Rapport")
    report_embed = fields.Html(string="Aperçu", sanitize=False)



    @api.model
    def create(self, vals):
        if vals.get('report_name'):
            vals['report_name'] = vals['report_name']
        return super().create(vals)

