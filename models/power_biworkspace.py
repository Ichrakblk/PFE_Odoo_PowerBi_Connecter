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

    def get_access_token(self):
        tenant_id = 'a079a463-30e0-4530-a231-576caa0508bc'
        client_id = '84220ff8-fe80-40db-a7ae-111af1de085f'
        client_secret = '8Ei8Q~Id5c~sABXw3m90Z.a2lbL3rmgkAWPrlbUb'

        url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'https://analysis.windows.net/powerbi/api/.default'
        }

        response = requests.post(url, headers=headers, data=data)
        response_data = response.json()
        access_token = response_data.get('access_token')


        return access_token

    @api.model
    def create_workspace_in_powerbi(self, connection_id, workspace_name):
        _logger = logging.getLogger(__name__)

        if not workspace_name:
            raise UserError("Le nom du workspace est requis !")

        connection = self.env['power_bi.connection'].browse(connection_id)
        if not connection.exists():
            raise UserError("Connexion Power BI invalide.")

        try:
            token = connection.get_access_token()
            if not token:
                raise UserError("Impossible d'obtenir un access token.")

            # Étape A : Créer le workspace
            url = 'https://api.powerbi.com/v1.0/myorg/groups'
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            data = {'name': workspace_name}
            response = requests.post(url, headers=headers, json=data)

            _logger.info(f"Request URL: {url}")
            _logger.info(f"Request headers: {headers}")
            _logger.info(f"Request data: {data}")
            _logger.info(f"Response status: {response.status_code}")
            _logger.info(f"Response body: {response.text}")

            if response.status_code in [200, 201]:
                workspace_data = response.json()
                workspace_id = workspace_data.get('id')

                if not workspace_id:
                    raise UserError("Aucun ID de workspace retourné.")

                # Étape B : Ajouter l'utilisateur i.bouleklaka@intiqaal.com comme Admin
                user_add_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/users"
                user_payload = {
                    "identifier": "i.bouleklaka@intiqaal.com",
                    "principalType": "User",
                    "groupUserAccessRight": "Admin"
                }

                user_response = requests.post(user_add_url, headers=headers, json=user_payload)
                _logger.info(f"Ajout utilisateur: status={user_response.status_code}, body={user_response.text}")

                if user_response.status_code not in [200, 201]:
                    raise UserError(f"Erreur lors de l'ajout de l'utilisateur: {user_response.text}")

                # Enregistrement Odoo
                workspace = self.create({
                    'name': workspace_data.get('name'),
                    'workspace_id': workspace_id,
                    'connection_id': connection.id,
                })

                self.log_message('success',
                                 f"✅ Workspace '{workspace.name}' créé avec succès (ID: {workspace.workspace_id}) et utilisateur ajouté.")
                return workspace
            else:
                error_message = f"Erreur Power BI API ({response.status_code}) : {response.text}"
                _logger.error(error_message)
                raise UserError(error_message)

        except Exception as e:
            _logger.exception("❌ Erreur inattendue lors de la création du workspace.")
            raise UserError(f"Erreur inattendue : {str(e)}")

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


