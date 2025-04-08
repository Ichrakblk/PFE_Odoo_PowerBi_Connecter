from odoo import models, fields, api

class PowerBIWorkspaceTemp(models.Model):
    _name = 'power_bi.workspace.temp'
    _description = 'Power BI Workspace Temp'

    name = fields.Char(string="Workspace Name")
    workspace_id = fields.Char(string="Workspace ID")

    def action_confirm_selection(self):

        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'power_bi.workspace',
            'view_mode': 'form',
            'res_id': self.env.context.get('active_id'),
            'target': 'current',
            'context': {
                'default_name': self.name,
                'default_workspace_id': self.workspace_id,
            }
        }
