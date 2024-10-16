from flask import Flask, request, jsonify
import dataset

app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def github_webhook():
    print('Webhook received:', request.json)
    data = request.json
    files = dataset.get_full_code(data)
    dataset.llm_code(files)

    # dataset.llm_code(content)
    return jsonify({'status': 'success'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
