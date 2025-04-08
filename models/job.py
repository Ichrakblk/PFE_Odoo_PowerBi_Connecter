# models/job.py

from odoo import models, fields, api
import os

class Job(models.Model):
    _name = 'job.model'
    _description = 'Job Model'

    name = fields.Char(string='Job Name', required=True)
    description = fields.Text(string='Job Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], default='draft', string='State')

    file_attachment = fields.Binary(string='File Attachment')
    file_filename = fields.Char(string='File Name')

    @api.model
    def upload_all_jobs(self):


        models_to_upload = ['power_bi.dashboard', 'power_bi.dataset']

        for model_name in models_to_upload:
            model = self.env[model_name]

            for record in model.search([]):

                print(f"Uploading record: {record.name}")

        return True

