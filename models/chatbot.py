from odoo import http
from odoo.http import request
import json
import re

class ChatbotController(http.Controller):

    @http.route('/chatbot', type='http', auth='user')
    def chatbot_page(self):
        return request.render('custom_powerbi_connector.chatbot_template')

    def detect_intent(self, message):
        message = message.lower()
        if "créer" in message and "contact" in message:
            return "create_contact"
        elif "trouver" in message and "client" in message:
            return "search_client"
        elif "facture" in message and "dernier" in message:
            return "last_invoice"
        elif "produit" in message and "stock" in message:
            return "product_stock"
        elif "bon de commande" in message or "commande fournisseur" in message:
            return "purchase_order"
        else:
            return "unknown"

    def generate_chatbot_response(self, message):
        intent = self.detect_intent(message)

        if intent == "create_contact":
            name = re.search(r"créer contact (.*)", message)
            name = name.group(1) if name else "Contact inconnu"
            partner = request.env['res.partner'].sudo().create({'name': name})
            return f"Contact '{partner.name}' créé avec succès."

        elif intent == "search_client":
            name = re.search(r"client (.*)", message)
            name = name.group(1) if name else ""
            clients = request.env['res.partner'].sudo().search([('name', 'ilike', name)], limit=5)
            if clients:
                return f"Clients trouvés : {', '.join(c.name for c in clients)}"
            else:
                return "Aucun client trouvé."

        elif intent == "last_invoice":
            invoice = request.env['account.move'].sudo().search([('move_type', '=', 'out_invoice')], order="date desc",
                                                                limit=1)
            if invoice:
                return f"Dernière facture : {invoice.name}, Montant : {invoice.amount_total} {invoice.currency_id.name}"
            else:
                return "Aucune facture trouvée."

        elif intent == "product_stock":
            products = request.env['product.product'].sudo().search([], limit=5)
            return "\n".join(f"{p.name}: en stock" for p in products)

        elif intent == "purchase_order":
            orders = request.env['purchase.order'].sudo().search([], limit=3)
            return "\n".join(f"{o.name} - Fournisseur : {o.partner_id.name}" for o in orders)

        return "Désolé, je ne comprends pas encore cette action."

    @http.route('/chatbot/message', type='json', auth='user', methods=['POST'])
    def handle_message(self, **kw):
        try:
            body = request.httprequest.get_data(as_text=True)
            data = json.loads(body) if body else {}
            message = data.get('text')
        except Exception:
            message = None

        if not message:
            return {'response': "Aucun message reçu."}

        response = self.generate_chatbot_response(message)
        return {'response': response}
