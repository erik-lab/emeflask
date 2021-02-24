from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello_world(fubar='No Input'):
    return 'Hello, kitten'

@app.route('/<fubar>')
def hello_wparm(fubar='No Input'):
    return 'Hello, ' + fubar

def main():
    app.run(debug = True)


if __name__ == '__main__':
    main()