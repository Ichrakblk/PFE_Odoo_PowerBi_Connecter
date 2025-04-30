from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)


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

    @api.onchange('workspace_id', 'dataset_id')
    def _onchange_workspace_id(self):
        """When changing workspace or dataset, reload only the reports associated with the selected dataset"""
        self.available_report_ids = [(5, 0, 0)]

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

            else:
                _logger.warning("⚠️ No reports found for the selected dataset.")
        else:
            _logger.warning("⚠️ The selected dataset was not found in Power BI.")

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
                dataset_info.append((ds.get("id"), ds.get("name")))
        else:
            _logger.error("Error fetching datasets: %s", response.text)

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

    def action_test_report_embed(self):
        self._compute_report_embed()
        _logger.info("✅ Report tested and embed generated.")
