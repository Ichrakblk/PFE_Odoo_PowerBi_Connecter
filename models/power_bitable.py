from odoo import models, fields, api

class PowerBiTable(models.Model):
    _name = 'power_bi.table'
    _description = 'Power BI Table'

    dataset_ids = fields.Many2many(
        'power_bi.dataset',
        string="Datasets",
        relation='power_bi_dataset_power_bi_table_rel',
        column1='table_id',
        column2='dataset_id'
    )

    table_ids = fields.Many2many(
        'ir.model', string="Tables",
        relation='power_bi_table_ir_model_rel',
        column1='table_id', column2='model_id',
    )

    merge_table = fields.Boolean(string="Merge Table?")
    state = fields.Selection([
        ('to_publish', 'To Publish'),
        ('published', 'Published')
    ], string="Status", default='to_publish', readonly=True, tracking=True)

    selected_field_ids = fields.Many2many(
        'ir.model.fields', string="Selected Fields",
        domain="[('model_id', 'in', table_ids)]"
    )
    related_field_ids = fields.Many2many(
        'ir.model.fields',  # ou un autre modèle
        'power_bi_table_related_field_rel',  # nom de la table relationnelle
        'power_bi_table_id',  # colonne correspondant à ce modèle
        'related_field_id',  # colonne correspondant à l'autre modèle
        string='Related Fields'
    )


    @api.depends('merge_table', 'table_ids')
    def _compute_related_fields(self):
        for rec in self:
            if rec.merge_table and rec.table_ids:
                related_fields = self.env['ir.model.fields'].search([
                    ('model_id', 'in', rec.table_ids.ids),
                    ('ttype', 'in', ['many2one', 'one2many', 'many2many'])
                ])
                rec.related_field_ids = related_fields
            else:
                rec.related_field_ids = [(5, 0, 0)]


    @api.onchange('table_ids')
    def _onchange_table_ids(self):

        if self.table_ids:

            self.selected_field_ids = [(5, 0, 0)]
            field_ids = self.env['ir.model.fields'].search([('model_id', 'in', self.table_ids.ids)]).ids
            return {'domain': {'selected_field_ids': [('id', 'in', field_ids)]}}

        return {'domain': {'selected_field_ids': []}}

    @api.onchange('dataset_ids')
    def _onchange_dataset_ids(self):
        for rec in self:
            if rec.dataset_ids:
                rec.state = 'published'
            else:
                rec.state = 'to_publish'

    def action_go_to_dataset(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'power_bi.dataset',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_table_ids': [(6, 0, [self.id])],
                'default_related_field_ids': [(6, 0, self.related_field_ids.ids)],
            }
        }

