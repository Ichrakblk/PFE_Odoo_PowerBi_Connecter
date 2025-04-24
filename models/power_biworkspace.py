from odoo import models, fields, api
import requests
from odoo.exceptions import UserError
import logging

class PowerBIWorkspace(models.Model):
    _name = 'power_bi.workspace'
    _description = 'Power BI Workspace'

    name = fields.Char(string="Workspace Name")
    workspace_id = fields.Char(string="Workspace ID")
    connection_id = fields.Many2one('power_bi.connection', string="Power BI Connection", ondelete='cascade', default=lambda self: self._get_default_connection())

    def _get_default_connection(self):
        connection = self.env['power_bi.connection'].search([], limit=1)
        return connection.id if connection else False

    workspace_name = fields.Selection(
        selection='_get_workspace_selection',
        string="🏷️ Workspace Name"
    )
    @api.model
    @api.model
    def _get_workspace_selection(self):
        workspaces = self.search([])
        seen = set()
        unique_names = []
        for ws in workspaces:
            if ws.name and ws.name not in seen:
                unique_names.append((ws.name, ws.name))
                seen.add(ws.name)
        return unique_names

    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ], default='draft', string="State")
    report_ids = fields.One2many('power_bi.report', 'workspace_id', string="Reports")

    @api.onchange('connection_id')
    def _onchange_connection_id(self):
        if self.connection_id:
            if self.connection_id.workspace_name:
                self.workspace_name = self.connection_id.workspace_name
            else:
                self.workspace_name = "Nom du workspace non disponible"
        else:
            self.workspace_name = False

    @api.model
    def import_workspaces(self):
        _logger = logging.getLogger(__name__)

        connection = self.env['power_bi.connection'].search([], limit=1)
        if not connection:
            raise UserError("Aucune connexion Power BI configurée !")

        try:
            token = connection.get_access_token()
            if not token:
                raise UserError("Impossible d'obtenir un access token.")

            url = 'https://api.powerbi.com/v1.0/myorg/groups'
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                workspaces = response.json().get('value', [])

                if not workspaces:
                    raise UserError("Aucun workspace trouvé.")

                self.env['power_bi.workspace'].search([('connection_id', '=', connection.id)]).unlink()

                for workspace in workspaces:
                    self.create({
                        'name': workspace['name'],
                        'workspace_id': workspace['id'],
                        'connection_id': connection.id,
                    })

                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Sélectionner un Workspace',
                    'res_model': 'power_bi.workspace',
                    'view_mode': 'tree,form',
                    'target': 'new',
                    'context': {}
                }

            else:
                raise UserError(f"Erreur API Power BI: {response.text}")

        except Exception as e:
            _logger.error(f"Échec de l'importation des workspaces : {str(e)}")
            raise UserError(f"Échec de l'importation des workspaces : {str(e)}")

    def create_workspace_popup(self):

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sélectionner un Workspace',
            'res_model': 'power_bi.workspace',
            'view_mode': 'form',
            'view_id': self.env.ref('custom_powerbi_connector.view_power_bi_workspace_form').id,
            'target': 'new',
        }

    def existe_workspace_popup(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Exister Workspace',
            'res_model': 'power_bi.workspace',
            'view_mode': 'form',
            'view_id': self.env.ref('custom_powerbi_connector.view_power_bi_workspace_existe_form').id,
            'target': 'new',
        }

    def action_save_and_redirect(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'power_bi.workspace',
            'view_mode': 'tree',
            'target': 'current',
        }

    def log_message(self, message_type, message):

        self.env['log.message'].create({
            'message': message_type,
            'log_message': message,
        })

    @api.model
    def create_workspace_in_powerbi(self, connection_id, workspace_name):
        _logger = logging.getLogger(__name__)
        if not workspace_name:
            raise UserError("Le nom du workspace est requis !")

        connection = self.env['power_bi.connection'].browse(connection_id)
        if not connection.exists():
            raise UserError("Veuillez sélectionner une connexion Power BI valide.")

        try:
            token = connection.get_access_token()
            if not token:
                raise UserError("Impossible d'obtenir un access token.")

            url = 'https://api.powerbi.com/v1.0/myorg/groups'
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            data = {'name': workspace_name}
            response = requests.post(url, headers=headers, json=data)

            if response.status_code in [200, 201]:
                workspace_data = response.json()
                workspace_id = workspace_data.get('id')
                if not workspace_id:
                    raise UserError("Réponse API invalide : aucun ID de workspace retourné.")

                # Si on est dans un record existant (self contient un record en cours), on le met à jour
                if self and len(self) == 1 and not self.workspace_id:
                    self.write({
                        'workspace_id': workspace_id,
                    })
                    self.log_message('success', f"Workspace '{workspace_name}' mis à jour avec l'ID Power BI.")
                    return self
                else:
                    # Sinon on en crée un nouveau
                    workspace = self.create({
                        'name': workspace_name,
                        'workspace_id': workspace_id,
                        'connection_id': connection.id,
                    })
                    self.log_message('success', f"Workspace '{workspace_name}' créé avec succès.")
                    return workspace

                self.log_message('success', f"Workspace '{workspace_name}' créé avec succès.")
                return workspace
            else:
                error_message = f"Erreur API Power BI: {response.text}"
                self.log_message('error', error_message)
                raise UserError(error_message)
        except Exception as e:
            error_message = f"Échec de la création du workspace : {str(e)}"
            _logger.error(error_message)
            self.log_message('error', error_message)
            raise UserError(error_message)




    def action_create_workspace(self):
        self.ensure_one()
        return self.create_workspace_in_powerbi(self.connection_id.id, self.name)

    def action_save_and_redirect(self):
        self.ensure_one()
        self.create_workspace_in_powerbi(self.connection_id.id, self.name)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'power_bi.workspace',
            'view_mode': 'tree',
            'target': 'current',
        }


