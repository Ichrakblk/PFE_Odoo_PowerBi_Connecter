from odoo import models, fields, api
class facturial (models.Model):
    _name = 'power_bi.facturail'
    _description = 'calculer facturial'

    nombre = fields.Integer('Nombre')
    resultat = fields.Integer('resultat', readonly=True)



    @api.depends('nombre')
    def calculer (self) :
         for res in self :
            n = res.nombre
            res.resultat = 1
            for i in range (2, n+1):
                res.resultat *=i