from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    #app.run(debug=True)
    #app.run(host='0.0.0.0', port=5000, debug=True)
    #app.run(host='127.0.0.1', port=5000, debug=True)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
