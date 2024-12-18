from flask import Flask, request, jsonify
import requests
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration (replace with your credentials)
SHOPIFY_API_KEY = "your_shopify_api_key"
SHOPIFY_PASSWORD = "your_shopify_password"
SHOPIFY_STORE_URL = "your-shopify-store.myshopify.com"

SHIPPING_PARTNER_API_URL = "https://api.speedy.bg/v1"
SHIPPING_PARTNER_USERNAME = "your_speedy_username"
SHIPPING_PARTNER_PASSWORD = "your_speedy_password"

# Root endpoint for health check or status
@app.route('/')
def home():
    return "Shopify and Shipping Partner Integration is running!"

# Webhook endpoint to handle Shopify order creation
@app.route('/webhook/orders', methods=['POST'])
def handle_order_webhook():
    logging.info(f"Raw request data: {request.data}")
    data = request.get_json()
    logging.info(f"Parsed JSON data: {data}")
    return jsonify({"message": "Webhook received successfully"}), 200
    try:
        data = request.get_json()
        logging.info(f"Received Shopify order: {data}")

        # Extract relevant order details
        order_id = data['id']
        recipient_name = data['shipping_address']['first_name'] + ' ' + data['shipping_address']['last_name']
        address = data['shipping_address']['address1']
        city = data['shipping_address']['city']
        postal_code = data['shipping_address']['zip']
        weight = 2.5  # Example weight, replace with actual data if available

        # Create shipment with shipping partner API
        shipment_response = create_shipment(recipient_name, address, city, postal_code, weight)
        if 'id' in shipment_response:
            tracking_number = shipment_response['id']

            # Update Shopify order with tracking number
            update_shopify_order(order_id, tracking_number)
            return jsonify({"message": "Order processed successfully"}), 200
        else:
            logging.error("Failed to create shipment")
            return jsonify({"error": "Failed to create shipment"}), 500
    except Exception as e:
        logging.error(f"Error processing webhook: {e}")
        return jsonify({"error": str(e)}), 500

# Function to create a shipment
def create_shipment(name, address, city, postal_code, weight):
    payload = {
        "userName": SHIPPING_PARTNER_USERNAME,
        "password": SHIPPING_PARTNER_PASSWORD,
        "recipient": {
            "clientName": name,
            "address": {
                "streetName": address,
                "city": city,
                "zip": postal_code
            }
        },
        "content": {
            "parcelsCount": 1,
            "totalWeight": weight,
            "contents": "General Goods"
        }
    }

    headers = {'Content-Type': 'application/json'}
    response = requests.post(f"{SHIPPING_PARTNER_API_URL}/shipment", json=payload, headers=headers)

    if response.status_code == 200:
        logging.info(f"Shipment created: {response.json()}")
        return response.json()
    else:
        logging.error(f"Failed to create shipment: {response.text}")
        return {}

# Function to update Shopify order with tracking information
def update_shopify_order(order_id, tracking_number):
    url = f"https://{SHOPIFY_API_KEY}:{SHOPIFY_PASSWORD}@{SHOPIFY_STORE_URL}/admin/api/2023-01/orders/{order_id}/fulfillments.json"
    payload = {
        "fulfillment": {
            "tracking_number": tracking_number,
            "tracking_company": "Speedy",
            "notify_customer": True
        }
    }

    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 201:
        logging.info(f"Shopify order updated: {response.json()}")
    else:
        logging.error(f"Failed to update Shopify order: {response.text}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
