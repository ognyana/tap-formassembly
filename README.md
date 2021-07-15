# tap-formassembly

A singer.io tap for extracting data from the Formassembly API, written in python 3.

Author: Ognyana Ivanova

## Quick start

1. Install

    Clone this repository, and then install using setup.py. We recommend using a virtualenv:

    ```bash
    > virtualenv -p python3 venv
    > source venv/bin/activate
    > python setup.py install
    ```

2. Create your tap's config file which should look like the following:

    ```json
    { 
       "baseUrl": "FORM_ASSEMBLY_BASE_URL",
       "accessToken": "FORM_ASSEMBLY_ACCESS_TOKEN",
       "dateRange": "FORM_ASSEMBLY_DATE_RANGE"
    }
    ```

43. Run the application

    `tap-formassembly` can be run with:

    ```bash
    tap-formassembly --config config.json
    ```

---

Copyright &copy; 2021
