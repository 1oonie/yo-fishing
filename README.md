# yo-fishing

Twaddle would not make Yo! Fishing so I did.

## Running

Create a [virtual environment](https://docs.python.org/3/library/venv.html) and activate it
```sh
python3 -m venv venv && source ./venv/bin/activate
```

Install the necessary requirements
```sh
pip install -r requirements.txt
```

Make the database file (if you have't already)
```sh
touch data.sqlite
```

Run the setup file
```sh
python setup.py
```