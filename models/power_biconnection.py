from odoo import models, fields, api
import requests
from odoo.exceptions import UserError
import logging

class PowerBIConnection(models.Model):
    _name = 'power_bi.connection'
    _description = 'Power BI Connection'
    _rec_name = 'name'

    name = fields.Char(required=True)
    tenant_id = fields.Char(required=True)
    client_id = fields.Char(required=True)
    client_secret = fields.Char(required=True)

    state = fields.Selection([
        ('not_connected', 'Not Connected'),
        ('connected', 'Connected')
    ], string="State", default='not_connected', tracking=True)

    workspace_count = fields.Integer(string="Workspaces", store=True)
    workspace_ids = fields.One2many('power_bi.workspace', 'connection_id', string="Workspaces")
    workspace_name = fields.Char(string="Workspace Name")

    def _compute_workspace_count(self):
        for record in self:
            record.workspace_count = 0  # Valeur par défaut

    def get_access_token(self):
        url = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://analysis.windows.net/powerbi/api/.default'
        }

        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            raise UserError(f"Failed to get access token: {response.text}")

    def test_power_bi_api(self, token):
        url = 'https://api.powerbi.com/v1.0/myorg/groups'
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            workspaces = response.json().get('value', [])
            if workspaces:
                # Vérification du workspace_name
                first_workspace_name = workspaces[0].get('name')
                if first_workspace_name:
                    return len(workspaces), first_workspace_name
                else:
                    return 0, "Nom du premier workspace non disponible"
            else:
                return 0, "Aucun workspace trouvé"
        elif response.status_code == 403:
            raise UserError("Permission refusée ! Vérifie les permissions API dans Azure.")
        else:
            raise UserError(f"Erreur API Power BI: {response.text}")

    def action_test_connection(self):
        _logger = logging.getLogger(__name__)
        try:
            token = self.get_access_token()
            if token:
                workspace_count, first_workspace_name = self.test_power_bi_api(token)
                self.write({
                    'state': 'connected',
                    'workspace_count': workspace_count,
                    'workspace_name': first_workspace_name or "Aucun workspace trouvé"
                })
                self.env.cr.commit()
                _logger.info(
                    f"Connexion réussie ! {workspace_count} workspaces trouvés. Premier workspace: {first_workspace_name}")
                raise UserError(
                    f"Connexion réussie ! {workspace_count} workspaces trouvés. Premier workspace: {first_workspace_name}")
            else:
                self.write({'state': 'not_connected', 'workspace_name': "Erreur de connexion"})
                self.env.cr.commit()
                _logger.warning("Impossible d'obtenir un access token.")
                raise UserError("Impossible d'obtenir un access token.")
        except Exception as e:
            self.write({'state': 'connected', 'workspace_count': 0, 'workspace_name': "Erreur"})
            self.write({
                'state': 'connected',
                'workspace_count': workspace_count,
                'workspace_name': first_workspace_name or "Aucun workspace trouvé"
            })

            self.env.cr.commit()
            _logger.error(f"Échec de la connexion : {str(e)}")
            raise UserError(f"Échec de la connexion : {str(e)}")


    def existe_workspace_popup(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Exister Workspace',
            'res_model': 'power_bi.workspace',
            'view_mode': 'form',
            'view_id': self.env.ref('custom_powerbi_connector.view_power_bi_workspace_existe_form').id,
            'target': 'new',
        }