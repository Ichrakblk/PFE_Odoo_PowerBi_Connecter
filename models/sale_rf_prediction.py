from odoo import models, fields, api
import psycopg2
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor


class SaleRFPrediction(models.TransientModel):
    _name = 'sale.rf.prediction'
    _description = 'Prédiction du montant total avec RandomForest'

    partner_ref = fields.Char(string='Référence Client', required=True)
    product_ref = fields.Char(string='Référence Produit', required=True)
    product_uom_qty = fields.Float(string='Quantité', required=True)
    price_unit = fields.Float(string='Prix Unitaire', required=True)

    prediction_result = fields.Text(string='Résultat de la prédiction', readonly=True)

    def _get_data_and_train_model(self):
        # Connexion à la base PostgreSQL
        conn = psycopg2.connect(
            host="192.168.233.128",
            port="5432",
            database="connecterbase",
            user="admin",
            password="admin"
        )
        query = """
        SELECT
            so.id AS order_id,
            so.partner_id,
            sol.product_id,
            sol.product_uom_qty,
            sol.price_unit,
            so.amount_total
        FROM
            sale_order_line sol
        JOIN
            sale_order so ON sol.order_id = so.id
        WHERE
            sol.price_total IS NOT NULL
        """
        df = pd.read_sql(query, conn)
        conn.close()

        df['partner_id'] = df['partner_id'].astype(str)
        df['product_id'] = df['product_id'].astype(str)

        X = df[['partner_id', 'product_id', 'product_uom_qty', 'price_unit']]
        y = df['amount_total']

        from sklearn.preprocessing import LabelEncoder
        le_partner = LabelEncoder()
        le_product = LabelEncoder()

        X['partner_id_enc'] = le_partner.fit_transform(X['partner_id'])
        X['product_id_enc'] = le_product.fit_transform(X['product_id'])

        X_final = X[['partner_id_enc', 'product_id_enc', 'product_uom_qty', 'price_unit']]

        X_train, X_test, y_train, y_test = train_test_split(X_final, y, test_size=0.2, random_state=42)

        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)


        return model, le_partner, le_product

    @api.model
    def predict_amount_total(self, partner_ref, product_ref, qty, price_unit):
        model, le_partner, le_product = self._get_data_and_train_model()

        partner_enc = le_partner.transform([partner_ref])[0]
        product_enc = le_product.transform([product_ref])[0]

        input_data = np.array([[partner_enc, product_enc, qty, price_unit]])

        prediction = model.predict(input_data)[0]

        return prediction

    def action_predict(self):
        if not self.partner_ref or not self.product_ref:
            self.prediction_result = "Erreur : veuillez saisir la référence client et produit."
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
            }
        try:
            prediction = self.predict_amount_total(
                self.partner_ref,
                self.product_ref,
                self.product_uom_qty,
                self.price_unit
            )
            self.write({'prediction_result': f"Montant total prédit : {prediction:.2f}"})
        except Exception as e:
            self.write({'prediction_result': f"Erreur lors de la prédiction : {str(e)}"})

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

