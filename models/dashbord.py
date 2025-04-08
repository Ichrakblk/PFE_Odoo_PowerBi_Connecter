from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class PowerBiDashboard(models.Model):
    _name = 'power_bi.dashboard'
    _description = 'Power BI Dashboard'
    _auto = False

    workspace_total = fields.Integer(string="Total Workspaces", compute="_compute_counts", store=False)


    dataset_total = fields.Integer(string="Total Datasets", compute="_compute_counts", store=False)
    dataset_published = fields.Integer(string="Published Datasets", compute="_compute_counts", store=False)
    dataset_unpublished = fields.Integer(string="Unpublished Datasets", compute="_compute_counts", store=False)

    table_total = fields.Integer(string="Total Tables", compute="_compute_counts", store=False)
    table_published = fields.Integer(string="Published Tables", compute="_compute_counts", store=False)
    table_unpublished = fields.Integer(string="Unpublished Tables", compute="_compute_counts", store=False)

    @api.depends()
    def _compute_counts(self):
        for record in self:
            # Workspaces
            for record in self:

                workspace_data = self.env['power_bi.workspace'].search([])
                _logger.info("read_group result: %s", workspace_data)
                record.workspace_total = len(workspace_data)


            # Datasets
            dataset_data = self.env['power_bi.dataset'].read_group([], ['state'], ['state'])
            _logger.info("Grouped read_group result: %s", dataset_data)
            record.dataset_total = sum(item.get('state_count', 0) for item in dataset_data)
            record.dataset_published = sum(
                item.get('state_count', 0) for item in dataset_data if item.get('state') == 'published')
            record.dataset_unpublished = record.dataset_total - record.dataset_published

            # Tables
            table_data = self.env['power_bi.table'].read_group([], ['state'], ['state'])
            _logger.info("Grouped read_group result: %s", table_data)
            record.table_total = sum(item.get('state_count', 0) for item in table_data)
            record.table_published = sum(item['state_count'] for item in table_data if item['state'] == 'published')
            record.table_unpublished = record.table_total - record.table_published
