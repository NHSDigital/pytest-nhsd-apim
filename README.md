# pytest-nhsd-apim

A pytest extension for NHSDigital's API Mangement suite.

## Installation
In your project's virtual environment
```code()
poetry add pytest-nhsd-apim
```
or if using pip directly
```code()
python -m pip install pytest-nhsd-apim
```

## Usage
- create a python test file
- write a test using our custom authentication markers!
- enjoy!?
      


## Testing
- run `make test` to run test examples, located in this repo
- after creating your file you can use the plugin as:
```code()
python -m pytest -p pytest_nhsd_apim test_nhsd_apim.py -s --apigee-proxy-name=<your-proxy-name>
```

## Available tools
When installing this library in your project you can access some very handy tools, including our platform authenticators and our apigee api wrapper library.
### Autheticators
We present a variety of authenticators including AuthorizationCodeAuthenticator, ClientCredentialsAuthenticator and TokenExchangeAuthenticator. The way of using them is simple. First you create the configuration object which will validate that your coniguration is correct on creation using pydantic, then pass the config to the authenticator and call get_token() on it.
```python
    from pytest_nhsd_apim.identity_service import ClientCredentialsConfig, ClientCredentialsAuthenticator

    config = ClientCredentialsConfig(
        environment={APIGEE_ENVIRONMENT},
        identity_service_base_url={BASE_URL},
        client_id={CLIENT_ID},
        jwt_private_key={PRIVATE_KEY_PEM},
        jwt_kid={KEY_ID},
    )

    authenticator=ClientCredentialsAuthenticator(config=config)
    token=authenticator.get_token()
```
For a more detailed implementation on the rest of the authenticators please refer to the examples [here](/tests/test_examples.py#L308).
### Apigee APIs
We also present a variety off Apigee APIs with the benefit of a fully authenticated Apigee client ready to use. Just remember to export the following variables
```bash
# If you want the client to authenticate you...
export APIGEE_NHSD_NONPROD_USERNAME={my_username}
export APIGEE_NHSD_NONPROD_PASSWORD={my_password}
export APIGEE_NHSD_NONPROD_OTP_KEY={my_otp}
# Or alternatively, if you already have a token you can pass it and the client will use it.
export APIGEE_ACCESS_TOKEN={access_token}

#NOTE: in case both sets of credentials are defined, the username and password take presedence, this is so the Apigee client can keep itself authenticated all the time.
```
```python
from pytest_nhsd_apim.apigee_apis import ApigeeNonProdCredentials, DeveloperAppsAPI

config = ApigeeNonProdCredentials()
client =  ApigeeClient(config=config)
apps = DeveloperAppsAPI(client=client)

print(apps.list_aps('lucas.fantini@nhs.net'))
```
The APIs we offer at the moment are:
| API  | Methods | Documentation| 
| ------------- | ------------- |-------------|
| DeveloperAppsAPI  | [here](/src/pytest_nhsd_apim/apigee_apis.py#L292)  |[Overview](https://apidocs.apigee.com/docs/developer-apps/1/overview)|
| ApiProductsAPI  | [here](/src/pytest_nhsd_apim/apigee_apis.py#L575)  |[Overview](https://apidocs.apigee.com/docs/api-products/1/overview)|
| DebugSessionsAPI  | [here](/src/pytest_nhsd_apim/apigee_apis.py#L844)  |[Overview](https://apidocs.apigee.com/docs/debug-sessions/1/overview)|
| AccessTokensAPI  | [here](/src/pytest_nhsd_apim/apigee_apis.py#L983)  |[Overview](https://apidocs.apigee.com/docs/oauth-20-access-tokens/1/overview)|

For a more detailed implementation of the available APIs please refer to the tests [here](/tests/test_apigee_apis.py).
We will keep adding APIs with time, if you are looking for a particular APIs not listed above please feel free to open a pull request and send it to us.


