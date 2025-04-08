from odoo import http
from odoo.http import request
import json

class PowerBIAPIController(http.Controller):

    @http.route('/api/powerbi/get_data', type='json', auth='public', methods=['POST'])
    def get_data(self, **kwargs):

        models = kwargs.get('models', [])
        result = {}

        for model_name in models:
            try:
                model_obj = request.env[model_name]
                records = model_obj.search([])
                result[model_name] = [rec.read()[0] for rec in records]
            except Exception as e:
                result[model_name] = {'error': str(e)}

        return result

    @http.route('/api/powerbi/update_record', type='json', auth='public', methods=['POST'])
    def update_record(self, **kwargs):

        model = kwargs.get('model')
        record_id = kwargs.get('record_id')
        values = kwargs.get('values', {})

        if not model or not record_id or not values:
            return {'error': 'Paramètres manquants'}

        try:
            record = request.env[model].browse(record_id)
            record.write(values)
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}
