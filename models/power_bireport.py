from odoo import models, fields, api
import requests
import logging
import re
import requests
_logger = logging.getLogger(__name__)
import time
import base64
from odoo.exceptions import UserError
import fitz

from openai import OpenAI
import time
import openai
import openai



class PowerBIReport(models.Model):
    _name = 'power_bi.report'
    _description = 'Power BI Report'

    name = fields.Char(string="Name")
    workspace_id = fields.Many2one('power_bi.workspace', string="Workspace")
    dataset_id = fields.Many2one('power_bi.dataset', string="Power BI Dataset")

    report_id = fields.Char(string="Power BI Report ID")  # Real ID
    report_url = fields.Char(string="Report URL", compute="_compute_report_url")
    report_embed = fields.Html(string="Preview", compute="_compute_report_embed", sanitize=False)

    parent_id = fields.Many2one('power_bi.report', string="Parent Report")
    available_report_ids = fields.One2many('power_bi.report', 'parent_id', string="Available Reports")
    embed_url = fields.Char("Embed URL", readonly=True)
    dataset_id_display = fields.Char(string="Power BI Dataset ID", readonly=True)
    has_multiple_reports = fields.Boolean(string="Multiple Reports?", compute="_compute_multiple_reports",
                                          store=True)
    summary_text = fields.Text(string="Summary of the Report", store=True)

    @api.depends('available_report_ids')
    def _compute_multiple_reports(self):
        for rec in self:
            rec.has_multiple_reports = len(rec.available_report_ids) > 1

    @api.depends('report_id', 'workspace_id')
    def _compute_report_url(self):
        for rec in self:
            if rec.report_id and rec.workspace_id:
                rec.report_url = f"https://app.powerbi.com/groups/{rec.workspace_id.workspace_id}/reports/{rec.report_id}?experience=power-bi"
            else:
                rec.report_url = ''

    @api.depends('embed_url')
    def _compute_report_embed(self):
        for rec in self:
            if rec.embed_url:
                rec.report_embed = f'''
                    <iframe title="Power BI Report" 
                            width="100%" 
                            height="600" 
                            src="{rec.embed_url}" 
                            frameborder="0" 
                            allowFullScreen="true">
                    </iframe>
                '''
            else:
                rec.report_embed = False

    @api.onchange('workspace_id')
    def _onchange_workspace_id(self):
        self.dataset_id = False
        self.available_report_ids = [(5, 0, 0)]

        if not self.workspace_id:
            return {'domain': {'dataset_id': []}}

        # Récupère les IDs Power BI des datasets via l'API
        datasets = self.get_all_dataset_ids(self.workspace_id.workspace_id)
        dataset_powerbi_ids = [ds[0] for ds in datasets]  # Liste des IDs externes (GUID)

        # Applique un domaine sur le champ powerbi_id du modèle dataset
        domain = [('powerbi_id', 'in', dataset_powerbi_ids)]

        return {'domain': {'dataset_id': domain}}

    @api.onchange('available_report_ids')
    def _onchange_available_report_ids(self):
        """
        Dynamically update the embed_url if a report is deleted or modified
        """
        if self.available_report_ids:

            first_report = self.available_report_ids[0]
            ctid = "a079a463-30e0-4530-a231-576caa0508bc"
            embed_url = f"https://app.powerbi.com/reportEmbed?reportId={first_report.report_id}&autoAuth=true&ctid={ctid}"
            self.embed_url = embed_url
            self.report_embed = f'''
                            <iframe title="Power BI Report" 
                                    width="100%" 
                                    height="600" 
                                    src="{embed_url}" 
                                    frameborder="0" 
                                    allowFullScreen="true">
                            </iframe>
                        '''
        else:

            self.embed_url = False
            self.report_embed = False

    def action_create_report_lines(self):
        """
                Method to generate and save the report lines
                available based on the workspace_id and dataset_id.
                """
        if not self.workspace_id or not self.dataset_id:
            return

        selected_dataset_name = self.dataset_id.name
        _logger.info("🔎 Selected Dataset: %s", selected_dataset_name)

        dataset_info = self.get_all_dataset_ids(self.workspace_id.workspace_id)

        selected_dataset_id = None
        for ds_id, ds_name in dataset_info:
            if ds_name == selected_dataset_name:
                selected_dataset_id = ds_id
                break

        if selected_dataset_id:
            _logger.info("📊 Dataset found with ID: %s", selected_dataset_id)

            reports = self.get_reports_by_dataset(self.workspace_id.workspace_id)

            reports_for_selected_dataset = reports.get(selected_dataset_id, [])

            if reports_for_selected_dataset:
                _logger.info("📋 Reports associated with dataset %s:", selected_dataset_id)

                report_lines = []

                for report_id, report_name in reports_for_selected_dataset:
                    _logger.info("    🔸 Report: %s (ID: %s)", report_name, report_id)

                    ctid = "a079a463-30e0-4530-a231-576caa0508bc"
                    embed_url = f"https://app.powerbi.com/reportEmbed?reportId={report_id}&autoAuth=true&ctid={ctid}"
                    _logger.info("🔗 Power BI URL generated: %s", embed_url)
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
                _logger.info("✅ Report lines created and saved.")

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
            _logger.error("❌ Token not found: %s", response_data)
        return access_token

    def get_all_dataset_ids(self, workspace_id):
        access_token = self._get_access_token()
        if not access_token:
            _logger.error("❌ Impossible de récupérer le token d'accès.")
            return []

        url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.error("❌ Erreur lors de la requête GET datasets: %s", str(e))
            return []

        dataset_info = []
        response_data = response.json()

        datasets = response_data.get('value', [])
        if not datasets:
            _logger.warning("⚠️ Aucun dataset trouvé dans le workspace %s.", workspace_id)
            return []

        for ds in datasets:
            dataset_id = ds.get("id")
            dataset_name = ds.get("name")
            if dataset_id and dataset_name:
                dataset_info.append((dataset_id, dataset_name))
            else:
                _logger.warning("⚠️ Dataset incomplet détecté : %s", ds)

        _logger.info("✅ %d datasets récupérés avec succès depuis le workspace %s.", len(dataset_info), workspace_id)
        return dataset_info

    def get_reports_by_dataset(self, workspace_id):
        access_token = self._get_access_token()
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports"
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        response = requests.get(url, headers=headers)
        reports_by_dataset = {}

        if response.status_code == 200:
            for report in response.json().get('value', []):
                dataset_id = report.get('datasetId')
                report_id = report.get('id')
                report_name = report.get('name')
                if dataset_id and report_id and report_name:
                    reports_by_dataset.setdefault(dataset_id, []).append((report_id, report_name))
        else:
            _logger.error("Error fetching reports: %s", response.text)

        return reports_by_dataset

    def action_show_datasets(self):
        for record in self:
            datasets = record.get_all_dataset_ids(record.workspace_id.workspace_id)
            _logger.info("✅ Datasets récupérés pour workspace %s :", record.workspace_id.name)

            if not datasets:
                raise UserError("Aucun dataset trouvé pour ce workspace.")

            created_datasets = []

            for dataset_id, dataset_name in datasets:
                _logger.info("🔹 ID: %s | Nom: %s", dataset_id, dataset_name)

                # Vérifier si le dataset existe déjà
                dataset_rec = self.env['power_bi.dataset'].search([('powerbi_id', '=', dataset_id)], limit=1)

                if not dataset_rec:
                    # Créer le dataset s'il n'existe pas
                    dataset_rec = self.env['power_bi.dataset'].create({
                        'name': dataset_name,
                        'powerbi_id': dataset_id
                    })
                    _logger.info("✅ Dataset créé : %s", dataset_name)
                else:
                    _logger.info("ℹ️ Dataset déjà existant : %s", dataset_name)

                created_datasets.append(dataset_rec.id)

            # Optionnel : associer un des datasets créés (le premier par exemple) au champ `dataset_id`
            if created_datasets:
                record.dataset_id = created_datasets[0]

        return True

    def action_test_report_embed(self):
        self._compute_report_embed()
        _logger.info("✅ Report tested and embed generated.")

    def _get_page_titles(self, report_id):
        access_token = self._get_access_token()
        headers = {'Authorization': f'Bearer {access_token}'}

        pages_url = f"https://api.powerbi.com/v1.0/myorg/groups/5240a229-ed55-45a7-a593-b23a4bbea19a/reports/d02dbe0f-68ba-47f4-8350-db54b67b1123/pages"
        pages_response = requests.get(pages_url, headers=headers)

        if pages_response.status_code != 200:
            _logger.error(
                f"Erreur lors de la récupération des pages : {pages_response.status_code} - {pages_response.text}")
            return []

        try:
            pages = pages_response.json().get('value', [])
        except ValueError:
            _logger.error(f"Réponse JSON invalide : {pages_response.text}")
            return []

        titles = [page.get("displayName") for page in pages if page.get("displayName")]
        return titles

    def action_test_page_titles(self):
        report_id = self.report_id
        titles = self._get_page_titles(report_id)

        if not titles:
            _logger.info("❌ Aucune page trouvée.")
        else:
            _logger.info("✅ Pages du rapport récupérées :")
            for title in titles:
                _logger.info(f"👉 {title}")

    def action_export_pdf(self):
        self.ensure_one()

        if not self.workspace_id or not self.dataset_id:
            raise UserError("Le workspace ou le dataset est manquant.")

        access_token = self._get_access_token()
        if not access_token:
            raise UserError("Impossible d'obtenir le token d'accès.")

        # 1. Récupérer tous les rapports du dataset
        selected_dataset_name = self.dataset_id.name
        dataset_info = self.get_all_dataset_ids(self.workspace_id.workspace_id)

        selected_dataset_id = None
        for ds_id, ds_name in dataset_info:
            if ds_name == selected_dataset_name:
                selected_dataset_id = ds_id
                break

        if not selected_dataset_id:
            raise UserError("Aucun ID de dataset trouvé correspondant au nom sélectionné.")

        reports = self.get_reports_by_dataset(self.workspace_id.workspace_id)
        reports_for_selected_dataset = reports.get(selected_dataset_id, [])

        if not reports_for_selected_dataset:
            raise UserError("Aucun rapport trouvé pour le dataset sélectionné.")

        # 2. Prendre le premier rapport lié
        report_id = reports_for_selected_dataset[0][0]  # (report_id, report_name)
        _logger.info("🧾 Report sélectionné pour export : ID = %s", report_id)

        # 3. Construire l'URL d'export dynamique
        export_url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id.workspace_id}/reports/{report_id}/ExportTo"
        _logger.info("Export URL construit : %s", export_url)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        body = {
            "format": "PDF"
        }

        # Lancer la demande d'export
        response = requests.post(export_url, headers=headers, json=body)
        if response.status_code != 202:
            _logger.error("❌ Échec de l'export PDF : %s", response.text)
            raise UserError("Erreur lors de la génération du PDF depuis Power BI.")

        # Récupérer l'ID d'export
        export_id = response.json().get('id')
        if not export_id:
            raise UserError("ID d'export introuvable.")

        # URL de suivi de l'export
        status_url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id.workspace_id}/reports/{report_id}/exports/{export_id}"
        _logger.info("Export  : %s", status_url)

        # Polling pour vérifier l'état de l'export
        for _ in range(15):  # par ex. 15 essais * 8sec = 120sec max
            time.sleep(8)
            status_response = requests.get(status_url, headers=headers)
            if status_response.status_code != 200:
                _logger.warning(f"Réponse inattendue lors du polling: {status_response.status_code}")
                continue

            status_data = status_response.json()
            status = status_data.get("status")
            _logger.info(f"Statut export PDF : {status}")

            if status == "Succeeded":
                break
            elif status == "Failed":
                raise UserError("L'export PDF a échoué.")
        else:
            raise UserError("L'export du PDF a expiré.")

        # Télécharger le fichier PDF
        file_url = status_url + "/file"
        pdf_response = requests.get(file_url, headers=headers)
        if pdf_response.status_code != 200:
            raise UserError("Erreur lors du téléchargement du fichier PDF.")

        # Enregistrer le PDF en pièce jointe Odoo
        attachment = self.env['ir.attachment'].create({
            'name': f"{self.name}.pdf",
            'type': 'binary',
            'datas': base64.b64encode(pdf_response.content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        _logger.info("✅ PDF exporté et enregistré avec succès.")

        # --- Extraction du texte depuis le PDF ---
        extracted_text = self._extract_text_from_pdf(pdf_response.content)
        _logger.info("Texte extrait du PDF (premiers 200 caractères) : %s", extracted_text[:200])

        # --- Résumé du texte extrait ---
        summary = self._summarize_text(extracted_text)
        _logger.info("Résumé généré : %s", summary)

        # --- Mise à jour du champ summary_text ---
        self.summary_text = summary

        # Retourne une action pour ouvrir ou télécharger le PDF
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def _extract_text_from_pdf(self, pdf_content):
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        return full_text

    def _summarize_text(self, text):
        try:
            cleaned_text = text[:1000]
            prompt = (
                "Here is the content of a decision-making report (excerpt):\n"
                f"{cleaned_text}\n"
                "Can you generate a clear and useful summary for a decision-maker?"
            )

            _logger.info(f"Prompt sent to Ollama: {prompt}")

            response = requests.post(
                "http://localhost:11434/api/generate",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=400
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Summary not available.")
            else:
                _logger.error(f"Summarization erro via Ollama: {response.status_code} - {response.text}")
                return "Summary not available."
        except Exception as e:
            _logger.error(f"Exception during summarization via Ollama: {str(e)}")
            return "Summary not available."






