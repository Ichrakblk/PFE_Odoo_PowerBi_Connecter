import requests
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
from markupsafe import Markup

_logger = logging.getLogger(__name__)

class PowerBIDataset(models.Model):
    _name = 'power_bi.dataset'
    _description = 'Dataset Power BI'
    _inherit = ['mail.thread']

    name = fields.Char(string="Dataset Name", required=True)
    workspace_id = fields.Many2one('power_bi.workspace', string="Workspace", tracking=True)
    table_ids = fields.Many2many(
        'power_bi.table',
        string="Tables",
        relation='power_bi_dataset_power_bi_table_rel',
        column1='dataset_id',
        column2='table_id'
    )
    field_ids = fields.Many2many('ir.model.fields', string="Fields", compute='_compute_fields', store=True)
    selected_field_ids = fields.Many2many(
        'ir.model.fields', string="Selected Fields",
        related='table_ids.selected_field_ids',
        readonly=True
    )
    related_field_ids = fields.Many2many(
        'ir.model.fields', string="Related Fields",
        related='table_ids.related_field_ids',
        readonly=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published')
    ], string="State", default='draft', tracking=True)
    decorated_state = fields.Html(string="Status", compute="_compute_decorated_state", store=False)

    def _compute_decorated_state(self):
        """
        deco
        """
        for record in self:
            color = "#27AE60" if record.state == "published" else "#E13535"
            label = "Published" if record.state == "published" else "Draft"
            record.decorated_state = Markup(
                f'<span style="color: white; background-color: {color}; padding: 2px 6px; border-radius: 4px;">{label}</span>')

    @api.depends('state')
    def _onchange_state(self):
        if self.state == 'published':
            self.name = self.name



    is_readonly = fields.Boolean(compute='_compute_is_readonly', store=False)

    def _compute_is_readonly(self):
        for record in self:
            record.is_readonly = record.state == 'published'
    @api.depends('table_ids')
    def _compute_fields(self):
        for record in self:
            field_ids = []
            for table in record.table_ids:
                fields = self.env['ir.model.fields'].search([('model_id', '=', table.id)])
                field_ids.extend(fields.ids)
            record.field_ids = [(6, 0, field_ids)]

    @api.model
    def create(self, vals):
        record = super(PowerBIDataset, self).create(vals)
        self.env['log.message'].create({
            'log_date': fields.Datetime.now(),
            'message': 'success',
            'log_message': f"Dataset Power BI '{record.name}' créé avec ID {record.id}."
        })
        return record

    def write(self, vals):
        result = super(PowerBIDataset, self).write(vals)
        for record in self:
            self.env['log.message'].create({
                'log_date': fields.Datetime.now(),
                'message': 'success',
                'log_message': f"Dataset Power BI '{record.name}' (ID {record.id}) mis à jour avec valeurs {vals}."
            })
        return result

    def action_show_tables(self):
        selected_table_ids = [model.id for model in self.table_ids]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'power_bi.table',
            'view_mode': 'tree',
            'view_id': self.env.ref('custom_powerbi_connector.view_power_bi_table_tree').id,
            'target': 'new',
            'context': {
                'default_dataset_id': self.id,
                'selected_table_ids': selected_table_ids,
            }
        }

    def action_save_selected_tables(self):
        selected_tables = self.table_ids.ids
        _logger.info("Selected tables: %s", selected_tables)

        if not selected_tables:
            raise UserError("Aucune table sélectionnée. Veuillez sélectionner des tables avant de sauvegarder.")

        dataset = self.env['power_bi.dataset'].search([('name', '=', self.name)], limit=1)
        if not dataset:
            raise UserError(f"Aucun dataset trouvé avec le nom : {self.name}")

        current_table_ids = set(dataset.table_ids.ids)
        selected_table_ids = set(selected_tables)
        new_table_ids = selected_table_ids - current_table_ids

        if new_table_ids:
            dataset.table_ids = [(4, table_id) for table_id in new_table_ids]


        self.env['log.message'].create({
            'log_date': fields.Datetime.now(),
            'message': 'success',
            'log_message': f"Tables mises à jour pour le dataset Power BI '{dataset.name}' (ID {dataset.id})."
        })

        _logger.info("Tables associées au dataset : %s", dataset.name)
        return True

    def action_publish_dataset(self):
        for record in self:
            record.message_post(body="Jeu de données publié avec succès!")
            self.env['log.message'].create({
                'log_date': fields.Datetime.now(),
                'message': 'success',
                'log_message': f"Dataset Power BI '{record.name}' (ID {record.id}) publié avec succès."
            })
        return True

    def action_publish_to_power_bi(self):
        _logger.info("Tentative de publication pour le dataset Power BI avec ID '%s'", self.id)

        connection = self.env['power_bi.connection'].search([], limit=1)
        if not connection:
            raise UserError("Aucune connexion Power BI trouvée.")

        token = connection.get_access_token()
        if not token:
            raise UserError("Impossible d'obtenir un token d'accès Power BI.")

        workspace_id = "5240a229-ed55-45a7-a593-b23a4bbea19a"
        url = f'https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        data = {
            "name": self.name,
            "defaultMode": "Push",
            "tables": []
        }

        for table in self.table_ids:
            column_names = set()
            columns = []

            for field in table.selected_field_ids:
                if field.name not in column_names:
                    column_names.add(field.name)
                    columns.append({
                        "name": field.name,
                        "dataType": "string"
                    })

            for field in table.related_field_ids:
                if field.name not in column_names:
                    column_names.add(field.name)
                    columns.append({
                        "name": field.name,
                        "dataType": "string"
                    })

            if columns:
                data["tables"].append({
                    "name": f"Table_{table.id}",
                    "columns": columns
                })

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 201:
            _logger.info("Publication réussie pour le dataset Power BI (ID: %d)", self.id)
            self.state = 'published'

            log_message = f"Dataset Power BI '{self.name}' (ID {self.id}) publié avec succès."
            self._create_log_message('success', log_message)

            # ➕ Message dans le chatter
            self.message_post(body=log_message)

        else:
            _logger.error("Erreur lors de la publication du dataset Power BI (ID: %d). Code: %d, Message: %s", self.id,
                          response.status_code, response.text)
            log_message = f"Erreur lors de la publication du dataset Power BI (ID {self.id}). Code: {response.status_code}, Message: {response.text}"
            self._create_log_message('error', log_message)
            raise UserError(f"Erreur lors de la publication : {response.status_code} - {response.text}")

    def _create_log_message(self, status, message):
        # Création du log
        self.env['log.message'].create({
            'log_date': fields.Datetime.now(),
            'message': status,
            'log_message': message
        })

