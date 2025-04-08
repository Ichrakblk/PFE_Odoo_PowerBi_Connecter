from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

class PowerBiTableField(models.Model):
    _name = 'power_bi.table.field'
    _description = 'Power BI Table Field'

    table_id = fields.Many2one('power_bi.table', string="Power BI Table")
    selected = fields.Boolean(string="Select for Publish", default=False)
    name = fields.Char(string="Field Name")
    label = fields.Char(string="Field Label")
    field_type = fields.Selection([
        ('char', 'Char'),
        ('text', 'Text'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('datetime', 'Datetime'),
        ('date', 'Date'),
        ('time', 'Time'),
        ('binary', 'Binary'),
        ('selection', 'Selection'),
        ('many2one', 'Many2One'),
        ('one2many', 'One2Many'),
        ('many2many', 'Many2Many'),
        ('reference', 'Reference'),
        ('html', 'HTML'),
        ('monetary', 'Monetary'),
        ('serialized', 'Serialized'),
    ], string="Field Type")
    model_id = fields.Many2one('ir.model', string="Model")

