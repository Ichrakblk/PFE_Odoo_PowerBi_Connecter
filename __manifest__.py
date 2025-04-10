{
    'name': 'Power BI Connector',
    'version': '1.0',
    'depends': ['base','mail'],
    'data': [
        'views/powerbi_connector_views.xml',
        'data/cron_jobs.xml',
        'views/power_bi_connection_views.xml',

        'views/power_bi_workspace_views.xml',
        'views/power_bi_workspacetemp.xml',
        'views/power_bi_dataset_views.xml',
        'views/power_bi_table_views.xml',
        'views/dashboard.xml',
        'views/job_tree_view.xml',
        'views/log_message_views.xml',
        'views/log_message.xml',
        'views/power_bi_menus.xml',
        'security/ir.model.access.csv',
    ],



    'installable': True,
    'application': True,
}
