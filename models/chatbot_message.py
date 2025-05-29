from odoo import models, fields

class ChatbotMessage(models.Model):
    _name = 'chatbot.message'
    _description = 'Historique messages chatbot'

    user_id = fields.Many2one('res.users', string='Utilisateur', required=True)
    message = fields.Text(string='Message utilisateur', required=True)
    response = fields.Text(string='Réponse chatbot', required=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
