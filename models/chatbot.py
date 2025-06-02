from odoo import http
from odoo.http import request
import json
import re
import spacy
import logging
from spellchecker import SpellChecker
import os
import requests
from odoo import fields

_logger = logging.getLogger(__name__)


class ChatbotController(http.Controller):
    # Initialisation de spaCy et du correcteur orthographique
    nlp = spacy.load("fr_core_news_md")
    spell = SpellChecker(language='fr')

    def phonetic_correction(self, text):
        try:
            response = requests.post(
                'https://api.languagetool.org/v2/check',
                data={
                    'text': text,
                    'language': 'fr',
                },
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                matches = result.get("matches", [])
                corrected_text = text
                offset_correction = 0

                for match in matches:
                    if match.get("replacements"):
                        replacement = match["replacements"][0]["value"]
                        start = match["offset"] + offset_correction
                        end = start + match["length"]
                        corrected_text = corrected_text[:start] + replacement + corrected_text[end:]
                        offset_correction += len(replacement) - match["length"]
                return corrected_text
            else:
                _logger.warning(f"Erreur LanguageTool: {response.status_code} {response.text}")
                return text
        except Exception as e:
            _logger.error(f"Erreur lors de l'appel à LanguageTool : {e}")
            return text

    def correct_message(self, message):
        """Corrige les fautes d'orthographe simples dans le message utilisateur."""
        corrected_words = []
        for word in message.split():
            if word in ['de', 'la', 'le', 'du']:
                corrected_words.append(word)
            else:
                try:
                    candidates = self.spell.candidates(word)
                    if candidates:
                        best = self.spell.correction(word)
                        corrected_words.append(best if best else word)
                    else:
                        corrected_words.append(word)
                except Exception as e:
                    _logger.error(f"Erreur lors de la correction du mot '{word}' : {e}")
                    corrected_words.append(word)
        return ' '.join(corrected_words)

    @http.route('/chatbot', type='http', auth='user')
    def chatbot_page(self):
        return request.render('custom_powerbi_connector.chatbot_template')

    def detect_intent(self, message):
        doc = self.nlp(message.lower())
        lemmas = [token.lemma_ for token in doc]
        if any(greeting in lemmas for greeting in ["bonjour", "salut", "bonsoir", "coucou"]):
            return "greeting"
        elif any(thank in lemmas for thank in ["merci", "remercier", "thanks", "thank"]):
            return "thanks"
        elif {"annuler", "annule", "cancel", "annulation", "annulé", "annulée"}.intersection(
                lemmas) and "devis" in lemmas:
            return "cancel_quotation"
        elif {"produit", "disponible", "article", "catalogue", "voir"}.intersection(lemmas):
            return "list_products"
        elif {"envoyer", "mail", "email", "courriel", "envoyer", "envoyé"}.intersection(lemmas) and "devis" in lemmas:
            return "send_quotation_email"
        elif {"valider", "confirmer"}.intersection(lemmas) and "devis" in lemmas:
            return "confirm_quotation"
        elif {"créer", "nouveau", "facture"}.intersection(lemmas):
            return "create_invoice"
        elif {"créer", "ajouter", "insérer"}.intersection(lemmas) and {"contact", "client"}.intersection(lemmas):
            return "create_contact"
        elif {"trouver", "chercher", "afficher"}.intersection(lemmas) and "client" in lemmas:
            return "search_client"
        elif "facture" in lemmas and "dernier" in lemmas:
            return "last_invoice"
        elif {"produit", "article"}.intersection(lemmas) and "stock" in lemmas:
            return "product_stock"
        elif {"commande", "bon"}.intersection(lemmas) and "fournisseur" in lemmas:
            return "purchase_order"
        elif {"employé", "personnel", "salarié"}.intersection(lemmas):
            return "list_employees"
        elif {"vente", "devis", "commercial"}.intersection(lemmas):
            return "list_sale_orders"
        elif {"pipeline", "opportunité", "afficher", "voir", "suivi"}.intersection(lemmas):
            return "list_opportunities"
        elif {"statistique", "total", "vente", "chiffre"}.intersection(lemmas):
            return "sales_statistics"

        elif {"aide", "capacité", "que", "peux", "faire"}.intersection(lemmas):
            return "help"
        else:
            return "unknown"

    def extract_name(self, message):
        match = re.search(r"(?:contact|client)\s+(.*)", message, re.IGNORECASE)
        return match.group(1).strip() if match else "Inconnu"

    def extract_quotation_ref(self, message):
        """
        Extrait la référence du devis depuis le message.
        Ex : "Envoyer le devis SO12345 par email" → retourne "SO12345"
        """
        match = re.search(r'\bSO\d+\b', message, re.IGNORECASE)
        return match.group(0) if match else None

    def generate_chatbot_response(self, message):
        original_message = message.lower()

        # Étape 1 : correction simple avec SpellChecker
        message_corrected = self.correct_message(original_message)

        # Étape 2 : correction grammaticale avec LanguageTool API
        final_corrected = self.phonetic_correction(message_corrected)

        _logger.info(f"[Chatbot] Message corrigé : {final_corrected}")

        correction_notice = ""
        if final_corrected != original_message:
            correction_notice = f"📝 Vous vouliez dire : « {final_corrected} » ?\n"

        intent = self.detect_intent(final_corrected)
        _logger.info(f"[Chatbot] Intent détecté : {intent}")

        intent_dispatcher = {
            "create_contact": self.create_contact,
            "search_client": self.search_client,
            "last_invoice": self.last_invoice,
            "product_stock": self.product_stock,
            "purchase_order": self.purchase_order,
            "list_employees": self.list_employees,
            "list_sale_orders": self.list_sale_orders,
            "confirm_quotation": self.confirm_quotation,
            "list_opportunities": self.list_opportunities,
            "cancel_quotation": self.cancel_quotation,
            "create_quotation": self.create_quotation,
            "create_invoice": self.create_invoice,
            "sales_statistics": self.sales_statistics,
            "send_quotation_email": self.send_quotation_email,
            "list_products": self.list_products,
            "greeting": self.greeting,
            "thanks": self.thanks,

            "help": self.show_help
        }

        handler = intent_dispatcher.get(intent, self.unknown_intent)
        response = handler(final_corrected)

        return correction_notice + response

    # === HANDLERS ===

    def create_contact(self, message):
        name = self.extract_name(message)
        partner = request.env['res.partner'].sudo().create({'name': name})
        return f"✅ Contact '{partner.name}' créé avec succès."

    def search_client(self, message):
        name = self.extract_name(message)
        clients = request.env['res.partner'].sudo().search([('name', 'ilike', name)], limit=5)
        if clients:
            return f"👤 Clients trouvés : {', '.join(c.name for c in clients)}"
        else:
            return "❌ Aucun client trouvé."

    def last_invoice(self, message):
        invoice = request.env['account.move'].sudo().search([('move_type', '=', 'out_invoice')], order="date desc", limit=1)
        if invoice:
            return f"🧾 Dernière facture : {invoice.name}, Montant : {invoice.amount_total} {invoice.currency_id.name}"
        return "❌ Aucune facture trouvée."

    def product_stock(self, message):
        templates = request.env['product.template'].sudo().search([], limit=5)
        return "\n".join(f"📦 {p.name} : {p.list_price} en stock" for p in templates)

    def purchase_order(self, message):
        orders = request.env['purchase.order'].sudo().search([], limit=3)
        return "\n".join(f"🛒 {o.name} - Fournisseur : {o.partner_id.name}" for o in orders)

    def list_employees(self, message):
        employees = request.env['hr.employee'].sudo().search([], limit=5)
        return "\n".join(f"👩‍💼 {e.name}" for e in employees) if employees else "❌ Aucun employé trouvé."

    def list_sale_orders(self, message):
        orders = request.env['sale.order'].sudo().search([], limit=5)
        return "\n".join(f"🧾 {o.name} - Client : {o.partner_id.name} - Total : {o.amount_total}" for o in orders)

    import re

    def confirm_quotation(self, message):
        try:
            match = re.search(r'\bSO\d+\b', message, re.IGNORECASE)
            if not match:
                return "❌ Référence du devis non trouvée dans le message."

            reference = match.group(0)

            order = request.env['sale.order'].sudo().search([
                ('name', 'ilike', reference),
                ('state', 'in', ['draft', 'sent'])  # seulement confirmables
            ], limit=1)

            if order:
                order.action_confirm()
                return f"✅ Devis {order.name} confirmé avec succès."
            else:
                return f"❌ Le devis {reference} n'est pas dans un état confirmable (brouillon ou envoyé)."

        except Exception as e:
            return f"❌ Erreur lors de la confirmation du devis : {str(e)}"

    def cancel_quotation(self, message):
        try:

            match = re.search(r'\bSO\d+\b', message, re.IGNORECASE)
            if not match:
                return "❌ Référence du devis non trouvée dans le message."

            reference = match.group(0)


            order = request.env['sale.order'].sudo().search([
                ('name', 'ilike', reference),
                ('state', 'in', ['draft', 'sent'])
            ], limit=1)

            if order:
                order.action_cancel()
                return f"🛑 Devis {order.name} annulé avec succès."
            else:
                return f"❌ Aucun devis annulable trouvé avec la référence {reference}."

        except Exception as e:
            return f"❌ Erreur lors de l'annulation du devis : {str(e)}"

    def list_opportunities(self, message):
        leads = request.env['crm.lead'].sudo().search([('type', '=', 'opportunity')], limit=5)
        if leads:
            return "\n".join(f"🎯 {l.name} - {l.stage_id.name} - {l.prorated_revenue} €" for l in leads)
        return "❌ Aucune opportunité trouvée."

    def create_quotation(self, message):
        partner = request.env['res.partner'].sudo().search([], limit=1)
        quotation = request.env['sale.order'].sudo().create({
            'partner_id': partner.id,
        })
        return f"📄 Nouveau devis créé : {quotation.name}"

    def sales_statistics(self, message):
        orders = request.env['sale.order'].sudo().search([('state', '=', 'sale')])
        total = sum(o.amount_total for o in orders)
        return f"📊 Le chiffre d'affaires total est de {total:.2f} € sur {len(orders)} commandes validées."

    def send_quotation_email(self, message):
        try:
            reference = self.extract_quotation_ref(message)
            if not reference:
                return "❌ Référence du devis non trouvée dans le message."

            order = request.env['sale.order'].sudo().search([('name', 'ilike', reference)], limit=1)
            if not order:
                return f"❌ Aucun devis trouvé avec la référence {reference}."


            template = request.env['mail.template'].sudo().browse(36)
            if not template:
                return "❌ Le modèle d'email avec l'ID 36 est introuvable."


            template.send_mail(order.id, force_send=True)
            return f"📧 Le devis {order.name} a été envoyé par email avec succès."

        except Exception as e:
            _logger.error(f"Erreur lors de l'envoi du devis par email : {e}")
            return f"❌ Erreur lors de l'envoi du devis : {str(e)}"

    def create_invoice(self, message):
        # Extraire le nom du client dans le message (ex: "Créer une facture pour client Dupont")
        name = self.extract_name(message)

        # Rechercher le partenaire/client
        partner = request.env['res.partner'].sudo().search([('name', 'ilike', name)], limit=1)
        if not partner:
            return f"❌ Aucun client trouvé avec le nom '{name}'."

        try:
            # Créer la facture (account.move de type facture client)
            invoice_vals = {
                'move_type': 'out_invoice',  # facture client
                'partner_id': partner.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [(0, 0, {
                    'name': "Article exemple",  # Tu peux extraire des détails produits depuis message ou paramètres
                    'quantity': 1,
                    'price_unit': 100.0,
                })],
            }
            invoice = request.env['account.move'].sudo().create(invoice_vals)

            # Optionnel : valider la facture automatiquement (enlever si tu veux juste créer un brouillon)
            invoice.action_post()

            return f"🧾 Facture {invoice.name} créée et validée pour le client {partner.name}."
        except Exception as e:
            return f"❌ Erreur lors de la création de la facture : {str(e)}"

    def list_products(self, message):
        products = request.env['product.product'].sudo().search([('qty_available', '>', 0)], limit=10)
        if products:
            return "\n".join(f"📦 {p.name} - En stock : {p.qty_available}" for p in products)
        return "❌ Aucun produit disponible en stock."

    def show_help(self, message):
        return ("📚 Voici ce que je peux faire :\n"
                "- Créer un contact\n"
                "- Rechercher un client\n"
                "- Afficher la dernière facture\n"
                "- Lister les produits en stock\n"
                "- Voir les bons de commande\n"
                "- Lister les employés\n"
                "- Afficher les devis/ventes")

    def unknown_intent(self, message):
        return ("❓ Je n'ai pas compris votre demande.\n"
                "Exemples : 'Créer un contact Jean Dupont', 'Afficher la dernière facture', ou 'Lister les employés'.")

    def greeting(self, message):
        return "👋 Bonjour ! Comment puis-je vous aider aujourd'hui ?"

    def thanks(self, message):
        return "🙏 Avec plaisir ! N'hésitez pas si vous avez d'autres questions."

    @http.route('/chatbot/message', type='json', auth='user', methods=['POST'])
    def handle_message(self, **kw):
        try:
            body = request.httprequest.get_data(as_text=True)
            data = json.loads(body) if body else {}
            message = data.get('text')
        except Exception:
            message = None

        if not message:
            return {'response': "⚠️ Aucun message reçu."}

        response = self.generate_chatbot_response(message)


        request.env['chatbot.message'].sudo().create({
            'user_id': request.env.user.id,
            'message': message,
            'response': response,
        })

        return {'response': response}
