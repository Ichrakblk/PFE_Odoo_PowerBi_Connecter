from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Paramètres de connexion à Odoo
odoo_url = "http://ichrak-virtual-machine:8069"
odoo_db = "my_newnew"
odoo_user = "admin"
odoo_password = "admin"

@app.route('/api/powerbi/sync', methods=['POST'])
def sync_data():
    try:
        # Obtenir les données envoyées dans la requête
        data = request.json
        model_name = data.get('model')
        model_data = data.get('data')

        if not model_name or not model_data:
            return jsonify({'error': 'Model or data missing'}), 400

        # Authentification via JSON-RPC
        auth_data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": odoo_db,
                "login": odoo_user,
                "password": odoo_password
            },
            "id": 1
        }

        # Effectuer la requête d'authentification
        auth_response = requests.post(f"{odoo_url}/web/session/authenticate", json=auth_data)

        if auth_response.status_code != 200:
            return jsonify({'error': 'Authentication failed'}), 500

        session_info = auth_response.json()
        if 'result' not in session_info or not session_info['result']:
            return jsonify({'error': 'Authentication failed'}), 500

        # Authentification réussie, effectuer la création des données
        create_data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model_name,
                "method": "create",
                "args": [model_data],
            },
            "id": 2
        }

        # Effectuer la requête pour créer un enregistrement
        create_response = requests.post(f"{odoo_url}/web/dataset/call_kw", json=create_data)

        if create_response.status_code == 200:
            return jsonify({'success': True, 'message': f"Data for {model_name} synchronized successfully."}), 200
        else:
            return jsonify({'error': 'Failed to synchronize data with Odoo'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
