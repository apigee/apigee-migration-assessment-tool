# Apigee Migration Assessment Tool

# Depedencies  

* Install Graphviz following https://graphviz.org/download/

* Install Python venv

```
python3 -m pip install virtualenv==20.24.4
```

* Install Python dependencies inside virtual env

```
python3 -m venv dev
source dev/bin/activate
pip install -r requirements.txt
```

# Specify Inputs

Create an `input.properties` file with the following data-

```
[inputs]      
SOURCE_URL=https://xxx/v1                # Apigee OPDK/Edge Management URL 
SOURCE_ORG=xxx                           # Apigee OPDK/Edge Organization
SOURCE_AUTH_TYPE=basic | oauth           # Apigee OPDK/Edge auth type , basic or ouath
SOURCE_UI_URL=https://xxx                # Apigee OPDK/Edge UI URL
SOURCE_APIGEE_VERSION=xxxx               # APIGEE Flavor OPDK/SAAS/X/HYBRID
GCP_PROJECT_ID=xx-xx-xx                  # Apigee X/Hybrd Organiziation ID
API_URL=https://xxx/docs                 # Apigee API url
GCP_ENV_TYPE=BASE | INTERMEDIATE | COMPREHENSIVE    # Apigee X/Hybrid desired environment type - [See docs](https://cloud.google.com/apigee/docs/api-platform/fundamentals/environments-overview#environment-types)
TARGET_DIR=target


[export]
EXPORT_DIR=export
EXPORT_FILE=export_data.json

[topology]
TOPOLOGY_DIR=topology
NW_TOPOLOGY_MAPPING=pod_component_mapping.json
DATA_CENTER_MAPPING=data_center_mapping.json

[report]
QUALIFICATION_REPORT=qualification_report.xlsx

[visualize]
VISUALIZATION_GRAPH_FILE=visualization.html

[validate]
CSV_REPORT=report.csv
```

# Usage 

To generate the Migration assessment report for all Apigee Objects run the command

```
python3 main.py --resources all
```


To selectively assess only certain Apigee Objects. The utility also supports the below arguments. 

* `--resources RESOURCES` resources can be one of or comma seperated list of
```                   
* targetservers
* keyvaluemaps
* references
* resourcefiles
* keystores
* flowhooks
* developers
* apiproducts
* apis
* apps
```
                                                
> For Apigee Environment level objects choose
>    `targetservers,keyvaluemaps,references,resourcefiles,keystores,flowhooks`

> For Apigee Organization level objects choose
>    `keyvaluemaps,developers,apiproducts,apis,apps`

> Example1: `--resources targetservers,keyvaluemaps`
> Example2: `--resources keystores,apps`
                                                

Command to run the tool
```
python3 main.py --resources targetservers

```


# Accessing the report

Once the tool is run, it will create a file called `qualification_report.xlsx`

You can import it to Google Sheets or any other application which can read `.xlsx` format


# Accessing the visualisation

Once the tool is run, it will create a file called `visualization.html`

You can access it by opening it in any browser

### Sample visualisation
![alt text](assets/visualization.png)