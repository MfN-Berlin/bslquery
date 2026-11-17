# bslquery

[![tests](https://github.com/MfN-Berlin/bslquery/actions/workflows/tests.yml/badge.svg)](https://github.com/MfN-Berlin/bslquery/actions/workflows/tests.yml)

Python package for querying the biosoundslab database.

## Installation
```
conda create -n biosoundslab python=3.12
conda activate biosoundslab
python -m pip install -r requirements.txt
```

Copy the `.env.examples ` file to `.env`. 
Open `.env` and set the required variables (this file will not be committed).

## Running the tests
```
conda activate biosoundslab
pip install -e .
python -m pytest
```

## Running the examples
Start the Jupyter notebooks server

```
conda activate biosoundslab
pip install -e .
jupyter lab
```

Open the `examples/00_Setup_DB_Connection` notebook and follow the instructions in the notebook to finish the setup.

See the notebooks in the `examples` directory for more examples.
