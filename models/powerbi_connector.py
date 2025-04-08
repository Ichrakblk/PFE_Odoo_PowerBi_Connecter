import base64
import json
import requests
from odoo import models, fields, api
from datetime import datetime


class PowerBIConnector(models.Model):
    _name = 'powerbi.connector'
    _description = 'Configuration Power BI'

    name = fields.Char(string='Nom de la configuration', required=True)
    model_ids = fields.Many2many('ir.model', string='Modèles à synchroniser')
    sync_frequency = fields.Selection([  # Ajout des options de synchronisation
        ('manual', 'Manuel'),
        ('daily', 'Quotidien'),
        ('weekly', 'Hebdomadaire'),
    ], string="Fréquence de Synchronisation", default='manual')

    def sync_data(self):
        for record in self:
            for model in record.model_ids:
                self.env['powerbi.connector'].export_model_data(model.model)

    @api.model
    def export_model_data(self, model_name):

        model_obj = self.env[model_name]
        records = model_obj.search([])

        data_list = []
        for rec in records:

            record_data = rec.read()[0]

            for field, value in record_data.items():
                if isinstance(value, bytes):
                    record_data[field] = base64.b64encode(value).decode('utf-8')  # Conversion en base64

                # Convertir les champs de type 'datetime' en chaîne au format ISO
                if isinstance(value, datetime):
                    record_data[field] = value.isoformat()

            data_list.append(record_data)

        # Appeler la méthode pour envoyer les données
        self._send_to_powerbi(model_name, data_list)

    def _send_to_powerbi(self, model_name, data):

        url = "http://localhost:5000/api/powerbi/sync"
        payload = {
            'model': model_name,
            'data': data
        }
        headers = {'Content-Type': 'application/json'}


        response = requests.post(url, data=json.dumps(payload), headers=headers)

        if response.status_code != 200:
            raise Exception(
                f"Échec de la synchronisation du modèle {model_name}, code de statut: {response.status_code}")

    @api.model
    def _cron_sync_powerbi(self):

        connectors = self.search([])
        for connector in connectors:
            connector.sync_data()
