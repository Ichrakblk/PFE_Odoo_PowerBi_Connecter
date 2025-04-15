from odoo import models, fields, api
import logging
import requests

_logger = logging.getLogger(__name__)

class PowerBIReport(models.Model):
    _name = 'power_bi.report'
    _description = 'Rapport Power BI'

    name = fields.Char(string="Name")
    workspace_id = fields.Many2one('power_bi.workspace', string="Workspace")
    report_id = fields.Selection(
        selection='_get_report_selection',
        string="Rapport Power BI"
    )

    report_url = fields.Char(string="URL  Rapport", compute="_compute_report_url", store=False)
    report_embed = fields.Html(string="Aperçu Rapport", compute="_compute_report_embed", sanitize=False)

    @api.model
    def _get_access_token(self):
        # Token fourni pour l'accès à l'API Power BI
       return "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6IkNOdjBPSTNSd3FsSEZFVm5hb01Bc2hDSDJYRSIsImtpZCI6IkNOdjBPSTNSd3FsSEZFVm5hb01Bc2hDSDJYRSJ9.eyJhdWQiOiJodHRwczovL2FuYWx5c2lzLndpbmRvd3MubmV0L3Bvd2VyYmkvYXBpIiwiaXNzIjoiaHR0cHM6Ly9zdHMud2luZG93cy5uZXQvYTA3OWE0NjMtMzBlMC00NTMwLWEyMzEtNTc2Y2FhMDUwOGJjLyIsImlhdCI6MTc0NDcyMjUzMiwibmJmIjoxNzQ0NzIyNTMyLCJleHAiOjE3NDQ3MjY0MzIsImFpbyI6ImsyUmdZTmg5YmZNYTlRMmFONXg4NTN0cG5DdUlCQUE9IiwiYXBwaWQiOiI4NDIyMGZmOC1mZTgwLTQwZGItYTdhZS0xMTFhZjFkZTA4NWYiLCJhcHBpZGFjciI6IjEiLCJpZHAiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9hMDc5YTQ2My0zMGUwLTQ1MzAtYTIzMS01NzZjYWEwNTA4YmMvIiwiaWR0eXAiOiJhcHAiLCJvaWQiOiJhNWQ1ZjIxYS01YTNjLTRjNzMtOGEzMi01NWIyNzAxZWRjYTciLCJyaCI6IjEuQVlJQVk2UjVvT0F3TUVXaU1WZHNxZ1VJdkFrQUFBQUFBQUFBd0FBQUFBQUFBQUNWQUFDQ0FBLiIsInJvbGVzIjpbIlRlbmFudC5SZWFkV3JpdGUuQWxsIiwiVGVuYW50LlJlYWQuQWxsIl0sInN1YiI6ImE1ZDVmMjFhLTVhM2MtNGM3My04YTMyLTU1YjI3MDFlZGNhNyIsInRpZCI6ImEwNzlhNDYzLTMwZTAtNDUzMC1hMjMxLTU3NmNhYTA1MDhiYyIsInV0aSI6InhRLWpTeHdFMkUyUDhXd24ySGxCQUEiLCJ2ZXIiOiIxLjAiLCJ4bXNfaWRyZWwiOiI3IDgifQ.A4lK-WXq3qpThcGjx8sYp2qDlMl-fvHmlq5fdwzqcYHn7y7XRU7-8HZ6egiogie7GJPGFOkRoBvACsF1-CWk0_yYqsCtdC7QjLfXPD6q3bqn7gc_xrMyZMjTY-hq1ZJHTuAEZLcdILtQf5RSx9A9daCcvbWIcWn4BQziY6GRYIBJCdtho65isYRms0fUFQe1bmybotmfGhISnwEfUpsB_AQm1KoCmdMrE3xoTH06DmWnc_uWH6KNpHTkJoMOwV31pp5CrbylZqtpwLvdAkq2gjykls-qA872L8i2QbfmjCYpkJ6LpqZJjPeeGG2lvRuf7SPnKEC5L6X89wSJB8XjKQ"


    def update_report_selection(self, options):
        """Met à jour dynamiquement la sélection des rapports."""
        _logger.debug("Mise à jour de la sélection des rapports avec %d options.", len(options))
        # Utilisation du champ 'report_id' pour définir les options de sélection
        self.write({'report_id': False})  # Réinitialiser report_id si nécessaire
        # Met à jour le domaine des rapports
        self.fields_get()['report_id']['selection'] = options
        # Redéfinir les domaines si nécessaire pour garantir une mise à jour correcte
        self.env.context = dict(self.env.context, report_id_domain=[("id", "in", [r[0] for r in options])])

    @api.depends('report_id', 'workspace_id')
    def _compute_report_url(self):
        for rec in self:
            if rec.report_id and rec.workspace_id:
                # L'URL correcte selon le format attendu
                rec.report_url = f"https://app.powerbi.com/groups/{rec.workspace_id.workspace_id}/reports/{rec.report_id}/{rec.report_id}?experience=power-bi"
                _logger.debug("URL du rapport générée : %s", rec.report_url)
            else:
                rec.report_url = ''
                _logger.debug("Aucune URL générée, report_id ou workspace_id manquant.")

    @api.depends('report_id')
    def _compute_report_embed(self):
        ctid = "a079a463-30e0-4530-a231-576caa0508bc"

        for rec in self:
            if rec.report_id:
                report_id = rec.report_id
                embed_url = f"https://app.powerbi.com/reportEmbed?reportId={report_id}&autoAuth=true&ctid={ctid}"
                rec.report_embed = f'''
                    <iframe title="Power BI Report" 
                            width="100%" 
                            height="600" 
                            src="{embed_url}" 
                            frameborder="0" 
                            allowFullScreen="true">
                    </iframe>
                '''


            else:
                rec.report_embed = ""

    def _get_report_selection(self):
        access_token = self._get_access_token()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        url = "https://api.powerbi.com/v1.0/myorg/groups/5240a229-ed55-45a7-a593-b23a4bbea19a/reports"

        _logger.info("🔄 Chargement de la sélection des rapports Power BI...")

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                rapports = response.json().get('value', [])
                selection = [(rapport['id'], rapport['name']) for rapport in rapports]
                _logger.info("✅ Rapports disponibles pour la sélection : %s", selection)
                return selection
            else:
                _logger.error("❌ Erreur lors de la récupération des rapports : %s", response.text)
                return []
        except Exception as e:
            _logger.exception("⚠️ Exception lors de la récupération des rapports Power BI : %s", str(e))
            return []

    def test_recuperation_rapports_console(self):
        access_token = self._get_access_token()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        url = f"https://api.powerbi.com/v1.0/myorg/groups/5240a229-ed55-45a7-a593-b23a4bbea19a/reports"

        _logger.info("🔄 Appel à l'API Power BI pour récupérer les rapports...")
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            rapports = response.json().get('value', [])
            _logger.info("✅ Rapports récupérés avec succès. Nombre de rapports : %d", len(rapports))

            # Préparation de la liste pour la selection
            selection = [(rapport['id'], rapport['name']) for rapport in rapports]

            # Mise à jour du champ report_id avec la sélection des rapports récupérés
            self._update_report_selection(selection)

            for rapport in rapports:
                _logger.info("📊 Rapport trouvé - Nom: %s | ID: %s", rapport.get('name'), rapport.get('id'))
        else:
            _logger.error("❌ Échec de récupération des rapports. Code: %s | Message: %s", response.status_code,
                          response.text)

    def _update_report_selection(self, selection):
        """
        Met à jour dynamiquement les options disponibles dans le champ 'report_id'.
        """
        # Ajout de la sélection des rapports dans le champ `report_id`
        self._set_report_selection(selection)

        # Méthode pour mettre à jour la sélection des rapports
    def _set_report_selection(self, selection):
            """
            Met à jour dynamiquement les options disponibles dans le champ 'report_id'.
            """
            # On met à jour le champ report_id avec la sélection dynamique
            self.env.cr.execute('''
                UPDATE ir_model_fields
                SET selection = %s
                WHERE model = %s AND name = %s
            ''', (str(selection), 'power_bi.report', 'report_id'))