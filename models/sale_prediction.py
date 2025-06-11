from odoo import models, fields, api
import pandas as pd
from prophet import Prophet
import psycopg2
from io import BytesIO
import base64
import matplotlib.pyplot as plt


class SalePrediction(models.Model):
    _name = 'sale.prediction'
    _description = 'Prévision des ventes par produit'

    product_name = fields.Char(string='Product name')
    prediction_result = fields.Text(string='Result of the prediction', readonly=False)
    prediction_graph = fields.Binary(string=".", readonly=True)
    def get_prediction(self):
        conn = psycopg2.connect(
            host="192.168.233.128",
            port="5432",
            database="connecterbase",
            user="admin",
            password="admin"
        )
        query = """SELECT
    sol.product_id,
    pt.name AS product_name,
    so.date_order,
    sol.product_uom_qty,
    sol.price_total
FROM
    sale_order_line sol
JOIN
    sale_order so ON sol.order_id = so.id
JOIN
    product_product pp ON sol.product_id = pp.id
JOIN
    product_template pt ON pp.product_tmpl_id = pt.id
WHERE
    so.state IN ('sale', 'done')"""
        df = pd.read_sql(query, conn)
        df['product_name'] = df['product_name'].apply(
            lambda x: x['en_US'] if isinstance(x, dict) and 'en_US' in x else str(x))
        df['date_order'] = pd.to_datetime(df['date_order'])

        df_monthly = df.groupby([pd.Grouper(key='date_order', freq='ME'), 'product_name'])[
            'product_uom_qty'].sum().reset_index()
        image = None
        result = ""
        for product in df_monthly['product_name'].unique():
            if self.product_name.lower() not in product.lower():
                continue

            df_product = df_monthly[df_monthly['product_name'] == product][['date_order', 'product_uom_qty']].copy()
            df_product.rename(columns={'date_order': 'ds', 'product_uom_qty': 'y'}, inplace=True)

            if df_product['y'].notnull().sum() >= 2:
                model = Prophet()
                model.fit(df_product)
                future = model.make_future_dataframe(periods=3, freq='ME')
                forecast = model.predict(future)

                forecast_filtered = forecast[['ds', 'yhat']].tail(3)
                for index, row in forecast_filtered.iterrows():
                    result += f"{row['ds'].date()} : {row['yhat']:.2f} unités\n"
                    # 💡 Générer le graphe
                    plt.figure(figsize=(18, 9))
                    plt.plot(df_product['ds'], df_product['y'], label='Historique', marker='o')
                    plt.plot(forecast['ds'], forecast['yhat'], label='Prévision', linestyle='--')
                    plt.legend()
                    plt.title(f"Prévision de ventes : {product}")
                    plt.xlabel('Date')
                    plt.ylabel('Quantité vendue')

                    buf = BytesIO()
                    plt.savefig(buf, format='png')
                    buf.seek(0)
                    image = base64.b64encode(buf.read())
                    buf.close()
                    break
                else:
                    result = f"Pas assez de données pour {self.product_name}"

                self.prediction_result = result
                self.prediction_graph = image

                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'sale.prediction',
                    'res_id': self.id,
                    'view_mode': 'form',
                    'target': 'new',
                }

