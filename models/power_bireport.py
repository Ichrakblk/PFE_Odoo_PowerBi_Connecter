from odoo import models, fields, api
import requests
import logging
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class PowerBIReport(models.Model):
    _name = 'power_bi.report'
    _description = 'Rapport Power BI'

    name = fields.Char(string="Name")
    workspace_id = fields.Many2one('power_bi.workspace', string="Workspace", required=True)
    dataset_id = fields.Many2one('power_bi.dataset', string="Dataset Power BI")

    report_id = fields.Char(string="ID Rapport Power BI")  # ID réel
    report_url = fields.Char(string="URL Rapport", compute="_compute_report_url")
    report_embed = fields.Html(string=".", compute="_compute_report_embed", sanitize=False)

    # Nouveau : ligne vers un modèle contenant les rapports disponibles
    available_report_ids = fields.One2many(
        'power_bi.report.choice', 'report_main_id', string="Available Reports ", store=True)
    selected_report_choice = fields.Many2one(
        'power_bi.report.choice', string="Rapport Sélectionné"
    )
    dataset_id_display = fields.Char(string="ID Dataset (Power BI)", readonly=True)
    embed_url = fields.Char("URL d'intégration", readonly=True)
    has_multiple_reports = fields.Boolean(string="Plusieurs rapports ?", compute="_compute_multiple_reports",
                                          store=True)

    @api.depends('available_report_ids')
    def _compute_multiple_reports(self):
        for rec in self:
            rec.has_multiple_reports = len(rec.available_report_ids) > 1

    @api.onchange('workspace_id', 'dataset_id')
    def _onchange_workspace_id(self):
        """Quand on change de workspace ou de dataset, on recharge uniquement les rapports associés au dataset sélectionné"""
        self.available_report_ids = [(5, 0, 0)]  # Vider la liste des rapports
        self.selected_report_choice = False

        if not self.workspace_id or not self.dataset_id:
            return

        selected_dataset_name = self.dataset_id.name
        _logger.info("🔎 Dataset sélectionné : %s", selected_dataset_name)

        dataset_info = self.get_all_dataset_ids(self.workspace_id.workspace_id)

        selected_dataset_id = None
        for ds_id, ds_name in dataset_info:
            if ds_name == selected_dataset_name:
                selected_dataset_id = ds_id
                break

        if selected_dataset_id:
            _logger.info("📊 Dataset trouvé avec l'ID : %s", selected_dataset_id)

            rapports = self.get_reports_by_dataset(self.workspace_id.workspace_id)

            reports_for_selected_dataset = rapports.get(selected_dataset_id, [])

            if reports_for_selected_dataset:
                _logger.info("📋 Rapports associés au dataset %s :", selected_dataset_id)

                report_lines = []






            else:
                _logger.warning("⚠️ Aucun rapport trouvé pour le dataset sélectionné.")
        else:
            _logger.warning("⚠️ Le dataset sélectionné n'a pas été trouvé dans Power BI.")

    def action_create_report_lines(self):
        """
        Méthode pour générer et enregistrer les lignes de rapports
        disponibles en fonction du workspace_id et dataset_id.
        """
        if not self.workspace_id or not self.dataset_id:
            return

        selected_dataset_name = self.dataset_id.name
        _logger.info("🔎 Dataset sélectionné : %s", selected_dataset_name)

        dataset_info = self.get_all_dataset_ids(self.workspace_id.workspace_id)

        selected_dataset_id = None
        for ds_id, ds_name in dataset_info:
            if ds_name == selected_dataset_name:
                selected_dataset_id = ds_id
                break

        if selected_dataset_id:
            _logger.info("📊 Dataset trouvé avec l'ID : %s", selected_dataset_id)

            rapports = self.get_reports_by_dataset(self.workspace_id.workspace_id)

            reports_for_selected_dataset = rapports.get(selected_dataset_id, [])

            if reports_for_selected_dataset:
                _logger.info("📋 Rapports associés au dataset %s :", selected_dataset_id)

                report_lines = []

                for report_id, report_name in reports_for_selected_dataset:
                    _logger.info("    🔸 Report: %s (ID: %s)", report_name, report_id)

                    ctid = "a079a463-30e0-4530-a231-576caa0508bc"
                    embed_url = f"https://app.powerbi.com/reportEmbed?reportId={report_id}&autoAuth=true&ctid={ctid}"
                    _logger.info("🔗 URL Power BI générée : %s", embed_url)
                    self.embed_url = embed_url
                    report_embed = f'''
                                           <iframe title="Power BI Report" 
                                                   width="100%" 
                                                   height="600" 
                                                   src="{embed_url}" 
                                                   frameborder="0" 
                                                   allowFullScreen="true">
                                           </iframe>
                                       '''

                    report_lines.append((0, 0, {
                        'report_id': report_id,
                        'name': report_name,
                        'report_embed': report_embed
                    }))

                self.write({'available_report_ids': report_lines})
                _logger.info("✅ Lignes de rapports créées et enregistrées.")

    @api.depends('selected_report_choice', 'workspace_id')
    def _compute_report_url(self):
        for rec in self:
            if rec.selected_report_choice and rec.workspace_id:
                rec.report_url = f"https://app.powerbi.com/groups/{rec.workspace_id.workspace_id}/reports/{rec.selected_report_choice.report_id}?experience=power-bi"
            else:
                rec.report_url = ''

    def action_test_report_embed(self):

        self._compute_report_embed()
        _logger.info("✅ Méthode _compute_report_embed exécutée via le bouton")

    def _get_access_token(self):
        tenant_id = 'a079a463-30e0-4530-a231-576caa0508bc'
        client_id = '84220ff8-fe80-40db-a7ae-111af1de085f'
        client_secret = '8Ei8Q~Id5c~sABXw3m90Z.a2lbL3rmgkAWPrlbUb'

        url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'https://analysis.windows.net/powerbi/api/.default'
        }

        response = requests.post(url, headers=headers, data=data)
        response_data = response.json()
        access_token = response_data.get('access_token')

        if not access_token:
            _logger.error("❌ Échec de l'obtention du token : %s", response_data)
        return access_token

    @api.onchange('selected_report_choice')
    def _onchange_selected_report_choice(self):
        if self.selected_report_choice:
            access_token = self._get_access_token()
            workspace_id = self.workspace_id.workspace_id
            report_id = self.selected_report_choice.report_id

            url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                report = response.json()
                dataset_id = report.get('datasetId')
                self.dataset_id_display = dataset_id
                _logger.info("✅ Dataset ID récupéré depuis Power BI : %s", dataset_id)


                self.name = self.selected_report_choice.report_name
                _logger.info("✅ Nom du rapport mis à jour : %s", self.name)

                self.report_url = f"https://app.powerbi.com/groups/{workspace_id}/reports/{report_id}?experience=power-bi"
            else:
                _logger.error("❌ Impossible de récupérer le datasetId depuis Power BI : %s", response.text)
                self.report_url = ''
        else:
            self.dataset_id_display = ''
            self.report_url = ''

    def get_all_dataset_ids(self, workspace_id):
        """
        Récupérer tous les datasetId et leurs noms pour un workspace Power BI spécifique.
        """
        access_token = self._get_access_token()
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        response = requests.get(url, headers=headers)
        dataset_info = []

        if response.status_code == 200:
            datasets = response.json().get('value', [])
            for ds in datasets:
                dataset_id = ds.get("id")
                dataset_name = ds.get("name")
                if dataset_id and dataset_name:
                    dataset_info.append((dataset_id, dataset_name))
                    _logger.debug("✅ Dataset : %s (%s)", dataset_name, dataset_id)
        else:
            _logger.error("❌ Erreur lors de la récupération des datasets depuis Power BI : %s", response.text)

        return dataset_info

    def action_get_dataset_ids(self):

        if self.workspace_id:
            dataset_info = self.get_all_dataset_ids(self.workspace_id.workspace_id)
            if dataset_info:

                dataset_display = ', '.join([f"{name} ({dataset_id})" for dataset_id, name in dataset_info])
                self.dataset_id_display = dataset_display
                _logger.info("✅ DatasetIds et noms récupérés et affichés : %s", dataset_display)
            else:
                self.dataset_id_display = 'Aucun dataset trouvé.'
                _logger.info("❌ Aucun dataset trouvé pour le workspace.")
        else:
            self.dataset_id_display = 'Workspace non défini.'
            _logger.error("❌ Workspace non défini.")

    def get_reports_by_dataset(self, workspace_id):

        access_token = self._get_access_token()

        datasets = self.get_all_dataset_ids(workspace_id)
        dataset_ids = [ds_id for ds_id, _ in datasets]

        reports_by_dataset = {}

        url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            reports = response.json().get('value', [])

            for dataset_id in dataset_ids:
                reports_for_dataset = []
                for rep in reports:
                    if rep.get("datasetId") == dataset_id:
                        reports_for_dataset.append((rep["id"], rep["name"]))
                        _logger.debug("✅ Rapport trouvé : %s pour dataset %s", rep["name"], dataset_id)

                if reports_for_dataset:
                    reports_by_dataset[dataset_id] = reports_for_dataset

            _logger.info("✅ Rapports par dataset récupérés avec succès.")
        else:
            _logger.error("❌ Erreur lors de la récupération des rapports : %s", response.text)

        return reports_by_dataset

    def action_afficher_rapports_par_dataset(self):
        if self.workspace_id:
            rapports = self.get_reports_by_dataset(self.workspace_id.workspace_id)
            for dataset_id, reports in rapports.items():
                _logger.info("📊 Dataset ID: %s", dataset_id)
                for report_id, name in reports:
                    _logger.info("    🔸 Report: %s (%s)", name, report_id)
        else:
            _logger.warning("❗ Aucun workspace sélectionné.")

    @api.depends('selected_report_choice')
    def _compute_report_embed(self):
        for record in self:
            _logger.info("Embed URL récupéré pour record ID %s : %s", record.id, record.embed_url)
            if record.embed_url:
                iframe_html = f'''
                    <iframe title="Power BI Report" 
                            width="100%" 
                            height="600" 
                            src="{record.embed_url}" 
                            frameborder="0" 
                            allowFullScreen="true">
                    </iframe>
                '''
                record.report_embed = Markup(iframe_html)
            else:
                record.report_embed = False
